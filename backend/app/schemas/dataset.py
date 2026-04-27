import uuid
from datetime import datetime

from pydantic import BaseModel


class DatasetResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    filename: str
    schema_version: str
    row_count: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SourceExampleResponse(BaseModel):
    id: uuid.UUID
    dataset_id: uuid.UUID
    project_id: uuid.UUID
    external_id: str | None
    source_hash: str
    payload: dict
    created_at: datetime

    model_config = {"from_attributes": True}
