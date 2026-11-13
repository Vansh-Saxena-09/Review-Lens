from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator

MAX_TEXT_LENGTH = 10_000
MAX_BATCH_ITEMS = 500

class ReviewInput(BaseModel):
    text: str = Field(..., min_length=1, max_length=MAX_TEXT_LENGTH)
    source: Optional[str] = Field(default=None, max_length=120)

    @field_validator("text")
    @classmethod
    def non_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Review text cannot be blank")
        return value

class AmazonAssessmentInput(BaseModel):
    url: str = Field(..., min_length=1, max_length=2048)
    title: Optional[str] = Field(default=None, max_length=500)
    brand: Optional[str] = Field(default=None, max_length=120)
    seller: Optional[str] = Field(default=None, max_length=120)
    price: Optional[str] = Field(default=None, max_length=80)
    seller_authorized: Literal["yes", "no", "unknown"] = "unknown"
    review_text: Optional[str] = Field(default=None, max_length=MAX_TEXT_LENGTH)

class BatchInput(BaseModel):
    reviews: list[ReviewInput] = Field(..., min_length=1, max_length=MAX_BATCH_ITEMS)

class Prediction(BaseModel):
    id: int
    created_at: datetime
    label: str
    display_label: str
    probability: float
    confidence: float
    text_length: int
    source: Optional[str] = None
    warning: str

class BatchSummary(BaseModel):
    total: int
    generated_count: int
    original_count: int

class BatchResponse(BaseModel):
    items: list[Prediction]
    summary: BatchSummary

class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    model_version: Optional[str] = None

class HistoryResponse(BaseModel):
    items: list[Prediction]
    total: int
    limit: int
    offset: int
