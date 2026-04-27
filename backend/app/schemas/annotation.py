import uuid
from datetime import datetime

from pydantic import BaseModel


class AnnotationCreate(BaseModel):
    label: dict
    confidence: int | None = None
    notes: str | None = None
    model_suggestion_visible: bool = True
    latency_ms: int | None = None


class AnnotationResponse(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    assignment_id: uuid.UUID
    annotator_id: uuid.UUID
    label: dict
    confidence: int | None
    notes: str | None
    model_suggestion_visible: bool
    latency_ms: int | None
    created_at: datetime

    model_config = {"from_attributes": True}
