import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class RelevanceLabel(BaseModel):
    relevance: Literal["relevant", "partially_relevant", "not_relevant"]


class AnnotationCreate(BaseModel):
    assignment_id: uuid.UUID
    label: RelevanceLabel
    confidence: int | None = Field(default=None, ge=1, le=5)
    notes: str | None = None


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


class AnnotationSubmissionResponse(BaseModel):
    annotation: AnnotationResponse
    task_status: str
