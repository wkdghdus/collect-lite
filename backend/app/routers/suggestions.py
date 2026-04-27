import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.annotation import ModelSuggestion
from app.models.task import Task
from app.schemas.task import ModelSuggestionResponse

router = APIRouter(tags=["suggestions"])


@router.post("/tasks/{task_id}/suggestions", status_code=202)
def request_suggestions(task_id: uuid.UUID, db: Session = Depends(get_db)):
    raise NotImplementedError


@router.get(
    "/tasks/{task_id}/suggestions",
    response_model=list[ModelSuggestionResponse],
)
def list_suggestions(task_id: uuid.UUID, db: Session = Depends(get_db)):
    if db.query(Task).filter(Task.id == task_id).first() is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return (
        db.query(ModelSuggestion)
        .filter(ModelSuggestion.task_id == task_id)
        .order_by(ModelSuggestion.created_at.desc())
        .all()
    )
