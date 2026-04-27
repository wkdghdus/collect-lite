import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.annotation import AnnotationCreate, AnnotationResponse

router = APIRouter(tags=["annotations"])


@router.post("/tasks/{task_id}/annotations", response_model=AnnotationResponse, status_code=201)
def submit_annotation(task_id: uuid.UUID, body: AnnotationCreate, db: Session = Depends(get_db)):
    raise NotImplementedError


@router.post("/tasks/{task_id}/skip", status_code=204)
def skip_task(task_id: uuid.UUID, db: Session = Depends(get_db)):
    raise NotImplementedError
