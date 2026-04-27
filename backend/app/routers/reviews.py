import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.quality import ReviewDecisionCreate

router = APIRouter(tags=["reviews"])


@router.get("/projects/{project_id}/review-queue")
def get_review_queue(project_id: uuid.UUID, db: Session = Depends(get_db)):
    raise NotImplementedError


@router.post("/reviews/{task_id}/resolve", status_code=200)
def resolve_review(task_id: uuid.UUID, body: ReviewDecisionCreate, db: Session = Depends(get_db)):
    raise NotImplementedError
