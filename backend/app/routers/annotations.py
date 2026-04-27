import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import func as sql_func
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.annotation import Annotation
from app.models.task import Assignment, Task
from app.schemas.annotation import (
    AnnotationCreate,
    AnnotationResponse,
    AnnotationSubmissionResponse,
)
from app.workers import jobs

router = APIRouter(tags=["annotations"])

TERMINAL_TASK_STATUSES = {"resolved", "exported"}


@router.post(
    "/tasks/{task_id}/annotations",
    response_model=AnnotationSubmissionResponse,
    status_code=201,
)
def submit_annotation(
    task_id: uuid.UUID,
    body: AnnotationCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status in TERMINAL_TASK_STATUSES:
        raise HTTPException(
            status_code=409,
            detail=f"Task is {task.status}; cannot annotate",
        )

    assignment = db.query(Assignment).filter(Assignment.id == body.assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    if assignment.task_id != task_id:
        raise HTTPException(
            status_code=400,
            detail="Assignment does not belong to this task",
        )
    if assignment.status != "assigned":
        raise HTTPException(
            status_code=409,
            detail=f"Assignment is {assignment.status}; cannot submit annotation",
        )

    annotation = Annotation(
        task_id=task_id,
        assignment_id=assignment.id,
        annotator_id=assignment.annotator_id,
        label=body.label.model_dump(),
        confidence=body.confidence,
        notes=body.notes,
    )
    db.add(annotation)

    assignment.status = "submitted"
    assignment.submitted_at = sql_func.now()

    db.flush()

    new_count = (
        db.query(sql_func.count(Annotation.id)).filter(Annotation.task_id == task_id).scalar()
    )
    new_status = "submitted" if new_count >= task.required_annotations else "assigned"
    if task.status != new_status:
        task.status = new_status

    db.commit()
    db.refresh(annotation)
    db.refresh(task)

    background_tasks.add_task(jobs.compute_consensus, task_id)

    return AnnotationSubmissionResponse(
        annotation=AnnotationResponse.model_validate(annotation),
        task_status=task.status,
    )


@router.post("/tasks/{task_id}/skip", status_code=204)
def skip_task(task_id: uuid.UUID, db: Session = Depends(get_db)):
    raise NotImplementedError
