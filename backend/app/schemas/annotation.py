import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class RelevanceLabel(BaseModel):
    relevance: Literal["relevant", "partially_relevant", "not_relevant"]


class AnnotationCreate(BaseModel):
    assignment_id: uuid.UUID | None = None
    annotator_id: uuid.UUID | None = None
    label: RelevanceLabel
    confidence: int | None = Field(default=None, ge=1, le=5)
    notes: str | None = None
    model_suggestion_visible: bool = False

    @model_validator(mode="after")
    def _require_assignment_or_annotator(self) -> "AnnotationCreate":
        if self.assignment_id is None and self.annotator_id is None:
            raise ValueError("Either assignment_id or annotator_id must be provided")
        return self


class AnnotationUpdate(BaseModel):
    annotator_id: uuid.UUID
    label: RelevanceLabel | None = None
    confidence: int | None = Field(default=None, ge=1, le=5)
    notes: str | None = None
    model_suggestion_visible: bool | None = None


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
    updated_at: datetime

    model_config = {"from_attributes": True}


class AnnotationSubmissionResponse(BaseModel):
    annotation: AnnotationResponse
    task_status: str
