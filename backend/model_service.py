from pathlib import Path
import json
import joblib

ROOT = Path(__file__).resolve().parent
MODEL_PATH = ROOT / "models" / "review_pipeline.joblib"
METRICS_PATH = ROOT / "models" / "metrics.json"

class ModelUnavailable(RuntimeError):
    pass

class ReviewModel:
    def __init__(self):
        self.pipeline = None
        self.metrics = {}
        self.version = None
        self.reload()

    def reload(self):
        self.pipeline = None
        self.metrics = {}
        self.version = None
        if MODEL_PATH.exists():
            self.pipeline = joblib.load(MODEL_PATH)
            if (not hasattr(self.pipeline, "predict") or not hasattr(self.pipeline, "predict_proba")
                    or set(getattr(self.pipeline, "classes_", [])) != {"CG", "OR"}):
                self.pipeline = None
                raise ValueError("Model artifact must support probabilities for exactly CG and OR")
        if METRICS_PATH.exists():
            self.metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
            self.version = self.metrics.get("model_version")

    @property
    def loaded(self) -> bool:
        return self.pipeline is not None

    def predict(self, text: str) -> tuple[str, float, float]:
        if not self.pipeline:
            raise ModelUnavailable("No trained model artifact is available. Train one with backend/train.py.")
        label = str(self.pipeline.predict([text])[0])
        probabilities = self.pipeline.predict_proba([text])[0]
        classes = list(self.pipeline.classes_)
        probability = float(probabilities[classes.index("CG")])
        confidence = max(probability, 1.0 - probability)
        if label not in {"CG", "OR"}:
            raise ValueError("Model returned an unsupported label")
        return label, probability, confidence

    def model_info(self) -> dict:
        return {
            "loaded": self.loaded,
            "model_version": self.version,
            "metrics": self.metrics,
            "architecture": "TF-IDF features with calibrated linear SVM" if self.loaded else None,
            "limitations": [
                "Labels describe computer-generated versus original text, not verified fraud.",
                "Text alone omits reviewer, product, transaction, and provenance context.",
                "Performance on new products, languages, and modern generators is unknown.",
                "Review-level splits can contain duplicates or related text unless group-aware evaluation is used.",
            ],
        }
