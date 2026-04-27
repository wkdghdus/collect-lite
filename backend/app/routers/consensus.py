import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db

router = APIRouter(tags=["consensus"])


@router.post("/tasks/{task_id}/consensus", status_code=202)
def compute_consensus(task_id: uuid.UUID, db: Session = Depends(get_db)):
    raise NotImplementedError


@router.get("/tasks/{task_id}/consensus")
def get_consensus(task_id: uuid.UUID, db: Session = Depends(get_db)):
    raise NotImplementedError
