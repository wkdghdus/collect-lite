import uuid
from datetime import datetime

from pydantic import BaseModel


class ReviewDecisionCreate(BaseModel):
    final_label: dict
    reason: str | None = None


class ConsensusResultResponse(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    final_label: dict
    agreement_score: float
    method: str
    num_annotations: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
