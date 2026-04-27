import uuid
from datetime import datetime

from pydantic import BaseModel


class TaskTemplateCreate(BaseModel):
    name: str
    instructions: str
    label_schema: dict


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
    required_annotations: int = 2
