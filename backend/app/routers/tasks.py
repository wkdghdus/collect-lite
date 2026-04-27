import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.project import Project
from app.models.task import Task, TaskTemplate
from app.schemas.task import TaskGenerateRequest, TaskResponse
from app.workers import jobs

router = APIRouter(tags=["tasks"])


@router.get("/projects/{project_id}/tasks", response_model=list[TaskResponse])
def list_project_tasks(
    project_id: uuid.UUID,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Task).filter(Task.project_id == project_id)
    if status is not None:
        query = query.filter(Task.status == status)
    return query.order_by(Task.created_at.desc()).all()


@router.post("/projects/{project_id}/tasks/generate", status_code=202)
def generate_tasks(
    project_id: uuid.UUID,
    body: TaskGenerateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.task_type != "rag_relevance":
        raise HTTPException(
            status_code=400,
            detail=(
                "Task generation is only supported for rag_relevance projects "
                f"(got {project.task_type!r})"
            ),
        )

    template = db.query(TaskTemplate).filter(TaskTemplate.id == body.template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Task template not found")
    if template.project_id != project_id:
        raise HTTPException(status_code=400, detail="Template does not belong to this project")

    background_tasks.add_task(
        jobs.generate_tasks, project_id, body.template_id, body.required_annotations
    )
    return {"status": "queued", "project_id": project_id}


@router.post("/projects/{project_id}/tasks/suggest", status_code=202)
def run_model_suggestions(
    project_id: uuid.UUID, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    raise NotImplementedError


@router.get("/tasks/next", response_model=TaskResponse | None)
def get_next_task(db: Session = Depends(get_db)):
    raise NotImplementedError


@router.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(task_id: uuid.UUID, db: Session = Depends(get_db)):
    raise NotImplementedError
