import uuid

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.task import TaskGenerateRequest, TaskResponse

router = APIRouter(tags=["tasks"])


@router.post("/projects/{project_id}/tasks/generate", status_code=202)
def generate_tasks(project_id: uuid.UUID, body: TaskGenerateRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    raise NotImplementedError


@router.post("/projects/{project_id}/tasks/suggest", status_code=202)
def run_model_suggestions(project_id: uuid.UUID, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    raise NotImplementedError


@router.get("/tasks/next", response_model=TaskResponse | None)
def get_next_task(db: Session = Depends(get_db)):
    raise NotImplementedError


@router.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(task_id: uuid.UUID, db: Session = Depends(get_db)):
    raise NotImplementedError
