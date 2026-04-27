import uuid
from datetime import datetime

from pydantic import BaseModel


class ExportCreate(BaseModel):
    format: str = "jsonl"


class ExportResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    format: str
    status: str
    file_path: str | None
    schema_version: str
    created_at: datetime

    model_config = {"from_attributes": True}
