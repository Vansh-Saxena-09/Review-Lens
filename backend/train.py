"""Train a leakage-safe TF-IDF + calibrated linear SVM from a CSV.
Expected columns: text_ (or text) and label, where labels are CG and OR.
"""
import argparse
import hashlib
import json
import platform
from pathlib import Path

import pandas as pd
from joblib import dump
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", type=Path)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--overwrite", action="store_true", help="Replace existing model and metrics after backing them up")
    args = parser.parse_args()
    out = ROOT / "models"
    if not args.overwrite and any((out / name).exists() for name in ("review_pipeline.joblib", "metrics.json")):
        raise SystemExit("Model or metrics already exist. Back them up and pass --overwrite to replace them.")
    data_path = args.csv.resolve()
    raw = pd.read_csv(data_path)
    text_col = "text_" if "text_" in raw.columns else "text"
    if text_col not in raw.columns or "label" not in raw.columns:
        raise SystemExit("CSV must contain text_ (or text) and label columns")
    data = raw[[text_col, "label"]].dropna()
    data[text_col] = data[text_col].astype(str).str.strip()
    data = data[data[text_col] != ""]
    data = data[data["label"].isin(["CG", "OR"])]
    counts = data["label"].value_counts()
    if len(data) < 20 or set(counts.index) != {"CG", "OR"} or counts.min() < 4:
        raise SystemExit("Need at least 20 non-empty rows, including at least 4 rows for each of CG and OR")
    x_train, x_test, y_train, y_test = train_test_split(data[text_col], data["label"], test_size=0.2, random_state=args.seed, stratify=data["label"])
    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(lowercase=True, strip_accents="unicode", ngram_range=(1, 2), min_df=2, max_df=0.98, sublinear_tf=True, max_features=100_000)),
        ("classifier", CalibratedClassifierCV(SGDClassifier(loss="hinge", alpha=1e-5, max_iter=2000, random_state=args.seed), cv=3, method="sigmoid")),
    ])
    pipeline.fit(x_train, y_train)
    probabilities = pipeline.predict_proba(x_test)[:, list(pipeline.classes_).index("CG")]
    predicted = pipeline.predict(x_test)
    report = classification_report(y_test, predicted, labels=["CG", "OR"], output_dict=True, zero_division=0)
    metrics = {
        "model_version": "tfidf-calibrated-linear-svm-v1",
        "trained_rows": int(len(x_train)), "test_rows": int(len(x_test)),
        "seed": args.seed, "positive_class": "CG",
        "accuracy": float(accuracy_score(y_test, predicted)),
        "roc_auc": float(roc_auc_score((y_test == "CG").astype(int), probabilities)),
        "classification_report": report,
        "confusion_matrix": confusion_matrix(y_test, predicted, labels=["CG", "OR"]).tolist(),
        "dataset_sha256": hashlib.sha256(data_path.read_bytes()).hexdigest(),
        "dataset_path_name": data_path.name,
        "python": platform.python_version(),
        "sklearn": __import__("sklearn").__version__,
        "preprocessing": "TF-IDF fit on training partition only; stratified 80/20 split",
    }
    out = ROOT / "models"
    out.mkdir(exist_ok=True)
    dump(pipeline, out / "review_pipeline.joblib")
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))

if __name__ == "__main__":
    main()
