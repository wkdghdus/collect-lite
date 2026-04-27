import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db

router = APIRouter(tags=["suggestions"])


@router.post("/tasks/{task_id}/suggestions", status_code=202)
def request_suggestions(task_id: uuid.UUID, db: Session = Depends(get_db)):
    raise NotImplementedError


@router.get("/tasks/{task_id}/suggestions")
def list_suggestions(task_id: uuid.UUID, db: Session = Depends(get_db)):
    raise NotImplementedError
