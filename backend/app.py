from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from db import initialize, insert_analysis, insert_many, list_analyses, analytics
from model_service import ReviewModel, ModelUnavailable
from link_assessment import assess_listing
from schemas import AmazonAssessmentInput, BatchInput, BatchResponse, BatchSummary, HealthResponse, HistoryResponse, Prediction, ReviewInput

model = ReviewModel()

@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize()
    yield

app = FastAPI(title="FAKE DECT Review Analysis API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_methods=["*"], allow_headers=["*"])

WARNING = "Estimate of text patterns associated with computer-generated or original reviews; not proof of fraud or authenticity."

def prediction(row: dict) -> Prediction:
    label = row["label"]
    return Prediction(
        id=row["id"], created_at=row["created_at"], label=label,
        display_label="Computer-generated pattern" if label == "CG" else "Original-writing pattern",
        probability=round(row["probability"], 6), confidence=round(row["confidence"], 6),
        text_length=len(row["text"]), source=row.get("source"), warning=WARNING,
    )

def run_prediction(review: ReviewInput) -> Prediction:
    try:
        label, probability, confidence = model.predict(review.text)
    except ModelUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    row = insert_analysis(review.text, label, probability, confidence, review.source, model.version or "local")
    return prediction(row)

@app.get("/api/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok", model_loaded=model.loaded, model_version=model.version)

@app.post("/api/assess-amazon")
def assess_amazon(payload: AmazonAssessmentInput):
    try:
        return assess_listing(payload, model)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.post("/api/predict", response_model=Prediction)
def predict(review: ReviewInput):
    return run_prediction(review)

@app.post("/api/predict/batch", response_model=BatchResponse)
def predict_batch(payload: BatchInput):
    try:
        values = [(review, model.predict(review.text)) for review in payload.reviews]
    except ModelUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    rows = insert_many([
        (review.text, label, probability, confidence, review.source, model.version or "local")
        for review, (label, probability, confidence) in values
    ])
    items = [prediction(row) for row in rows]
    generated = sum(item.label == "CG" for item in items)
    return BatchResponse(items=items, summary=BatchSummary(total=len(items), generated_count=generated, original_count=len(items)-generated))

@app.get("/api/history", response_model=HistoryResponse)
def history(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), label: str | None = Query(None)):
    rows, total = list_analyses(limit, offset, label)
    return HistoryResponse(items=[prediction(row) for row in rows], total=total, limit=limit, offset=offset)

@app.get("/api/analytics")
def get_analytics():
    return analytics()

@app.get("/api/model")
def model_info():
    return model.model_info()

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
if (FRONTEND / "index.html").is_file():
    app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")
