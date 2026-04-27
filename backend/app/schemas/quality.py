import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.schemas.task import TaskDetailResponse

ReviewLabel = Literal["relevant", "partially_relevant", "not_relevant"]


class ReviewDecisionCreate(BaseModel):
    final_label: ReviewLabel
    reason: str | None = None
    reviewer_id: uuid.UUID | None = None


class ReviewDecisionResponse(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    reviewer_id: uuid.UUID
    final_label: dict
    reason: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


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


class ReviewSubmitResponse(BaseModel):
    review: ReviewDecisionResponse
    task_status: str


class ReviewQueueItem(TaskDetailResponse):
    consensus: ConsensusResultResponse | None = None
