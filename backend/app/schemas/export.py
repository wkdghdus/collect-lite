import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ExportCreate(BaseModel):
    format: Literal["jsonl", "csv"] = "jsonl"


class ExportResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    format: str
    status: str
    file_path: str | None
    row_count: int
    schema_version: str
    created_at: datetime

    model_config = {"from_attributes": True}
