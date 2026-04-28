import uuid
from datetime import datetime

from pydantic import BaseModel


class TaskTemplateCreate(BaseModel):
    name: str
    instructions: str
    label_schema: dict


class TaskTemplateResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    instructions: str
    label_schema: dict
    version: int
    created_at: datetime

    model_config = {"from_attributes": True}


class TaskResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    example_id: uuid.UUID
    template_id: uuid.UUID
    status: str
    priority: int
    required_annotations: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskGenerateRequest(BaseModel):
    template_id: uuid.UUID
    dataset_id: uuid.UUID
    required_annotations: int = 2


class ModelSuggestionResponse(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    provider: str
    model_name: str
    suggestion: dict
    confidence: float | None
    raw_response: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ModelSuggestionPayload(BaseModel):
    provider: str
    model_name: str
    score: float | None = None
    suggested_label: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AnnotationSummary(BaseModel):
    id: uuid.UUID
    label: dict
    confidence: int | None = None
    notes: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TaskDetailResponse(TaskResponse):
    source_example_id: uuid.UUID
    dataset_id: uuid.UUID | None = None
    query: str = ""
    candidate_document: str = ""
    document_id: str | None = None
    example_metadata: dict = {}
    model_suggestion: ModelSuggestionPayload | None = None
    annotations: list[AnnotationSummary] = []
