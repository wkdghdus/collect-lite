import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db

router = APIRouter(tags=["metrics"])


@router.get("/projects/{project_id}/metrics")
def get_project_metrics(project_id: uuid.UUID, db: Session = Depends(get_db)):
    raise NotImplementedError
