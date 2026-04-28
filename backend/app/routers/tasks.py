import json
import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.models.dataset import Dataset
from app.models.project import Project
from app.models.task import Task, TaskTemplate
from app.schemas.task import (
    AnnotationSummary,
    ModelSuggestionPayload,
    ModelSuggestionResponse,
    TaskDetailResponse,
    TaskGenerateRequest,
    TaskResponse,
    TaskTemplateResponse,
)
from app.services.model_suggestions import (
    PayloadInvalidError,
    TaskNotFoundError,
    TaskTerminalError,
    generate_suggestion_for_task,
)
from app.workers import jobs


def _as_dict(value: Any) -> dict:
    """Coerce a JSONB column into a dict.

    SQLite (test infra) compiles JSONB to TEXT, so values may round-trip as
    JSON-encoded strings instead of dicts. Returns ``{}`` on anything that
    cannot be parsed into a dict.
    """
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except (TypeError, ValueError):
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


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


@router.get(
    "/projects/{project_id}/templates",
    response_model=list[TaskTemplateResponse],
)
def list_project_templates(project_id: uuid.UUID, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    templates = (
        db.query(TaskTemplate)
        .filter(TaskTemplate.project_id == project_id)
        .order_by(TaskTemplate.created_at.desc())
        .all()
    )
    return [
        TaskTemplateResponse(
            id=t.id,
            project_id=t.project_id,
            name=t.name,
            instructions=t.instructions,
            label_schema=_as_dict(t.label_schema),
            version=t.version,
            created_at=t.created_at,
        )
        for t in templates
    ]


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

    dataset = db.query(Dataset).filter(Dataset.id == body.dataset_id).first()
    if not dataset or dataset.project_id != project_id:
        raise HTTPException(status_code=400, detail="Dataset does not belong to this project")

    background_tasks.add_task(
        jobs.generate_tasks,
        project_id,
        body.template_id,
        body.required_annotations,
        body.dataset_id,
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


@router.get("/tasks/{task_id}", response_model=TaskDetailResponse)
def get_task(task_id: uuid.UUID, db: Session = Depends(get_db)):
    task = (
        db.query(Task)
        .options(
            selectinload(Task.example),
            selectinload(Task.model_suggestions),
            selectinload(Task.annotations),
        )
        .filter(Task.id == task_id)
        .first()
    )
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    payload = _as_dict(task.example.payload if task.example else {})

    latest = max(task.model_suggestions, key=lambda s: s.created_at, default=None)
    suggestion_payload: ModelSuggestionPayload | None = None
    if latest is not None:
        s_dict = _as_dict(latest.suggestion)
        suggestion_payload = ModelSuggestionPayload(
            provider=latest.provider,
            model_name=latest.model_name,
            score=float(latest.confidence) if latest.confidence is not None else None,
            suggested_label=s_dict.get("relevance") or s_dict.get("label"),
            created_at=latest.created_at,
        )

    annotations_summary = sorted(
        (AnnotationSummary.model_validate(a) for a in task.annotations),
        key=lambda a: a.created_at,
    )

    return TaskDetailResponse(
        **TaskResponse.model_validate(task).model_dump(),
        source_example_id=task.example_id,
        dataset_id=task.example.dataset_id if task.example else None,
        query=str(payload.get("query", "")),
        candidate_document=str(payload.get("candidate_document", "")),
        document_id=payload.get("document_id"),
        example_metadata=payload.get("metadata") or {},
        model_suggestion=suggestion_payload,
        annotations=annotations_summary,
    )


@router.post(
    "/tasks/{task_id}/suggestion",
    response_model=ModelSuggestionResponse,
    status_code=201,
)
def create_task_suggestion(task_id: uuid.UUID, db: Session = Depends(get_db)):
    try:
        return generate_suggestion_for_task(db, task_id)
    except TaskNotFoundError:
        raise HTTPException(status_code=404, detail="Task not found")
    except TaskTerminalError as e:
        raise HTTPException(
            status_code=409,
            detail=f"Task is {e.status}; cannot generate a new suggestion",
        )
    except PayloadInvalidError as e:
        raise HTTPException(
            status_code=422,
            detail=f"Source example is missing required fields: {', '.join(e.missing)}",
        )
