import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import func as sql_func
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.annotation import Annotation
from app.models.task import Assignment, Task
from app.models.user import User
from app.schemas.annotation import (
    AnnotationCreate,
    AnnotationResponse,
    AnnotationSubmissionResponse,
    AnnotationUpdate,
)
from app.services.assignment import ensure_assignment
from app.workers import jobs

router = APIRouter(tags=["annotations"])

TERMINAL_TASK_STATUSES = {"resolved", "exported"}
LOCKED_TASK_STATUSES = {"needs_review", "resolved", "exported"}


def _duplicate_submission_response(
    db: Session, task_id: uuid.UUID, annotator_id: uuid.UUID, assignment_status: str
) -> JSONResponse:
    existing = (
        db.query(Annotation)
        .filter(Annotation.task_id == task_id, Annotation.annotator_id == annotator_id)
        .first()
    )
    if existing is not None:
        return JSONResponse(
            status_code=409,
            content={
                "detail": (
                    f"Annotation already submitted; PATCH "
                    f"/api/tasks/{task_id}/annotations/{existing.id} to edit"
                ),
                "annotation_id": str(existing.id),
            },
        )
    return JSONResponse(
        status_code=409,
        content={
            "detail": f"Assignment is {assignment_status}; cannot submit annotation",
        },
    )


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

    if body.assignment_id is not None:
        assignment = (
            db.query(Assignment).filter(Assignment.id == body.assignment_id).first()
        )
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")
        if assignment.task_id != task_id:
            raise HTTPException(
                status_code=400,
                detail="Assignment does not belong to this task",
            )
        if assignment.status != "assigned":
            return _duplicate_submission_response(
                db, task_id, assignment.annotator_id, assignment.status
            )
    else:
        annotator = db.query(User).filter(User.id == body.annotator_id).first()
        if annotator is None:
            raise HTTPException(status_code=404, detail="Annotator not found")
        assignment = ensure_assignment(db, task_id, body.annotator_id)
        if assignment.status != "assigned":
            return _duplicate_submission_response(
                db, task_id, assignment.annotator_id, assignment.status
            )

    annotation = Annotation(
        task_id=task_id,
        assignment_id=assignment.id,
        annotator_id=assignment.annotator_id,
        label=body.label.model_dump(),
        confidence=body.confidence,
        notes=body.notes,
        model_suggestion_visible=body.model_suggestion_visible,
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

    background_tasks.add_task(jobs.compute_consensus, task_id)

    return AnnotationSubmissionResponse(
        annotation=AnnotationResponse.model_validate(annotation),
        task_status=new_status,
    )


@router.patch(
    "/tasks/{task_id}/annotations/{annotation_id}",
    response_model=AnnotationResponse,
)
def update_annotation(
    task_id: uuid.UUID,
    annotation_id: uuid.UUID,
    body: AnnotationUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    annotation = db.query(Annotation).filter(Annotation.id == annotation_id).first()
    if annotation is None:
        raise HTTPException(status_code=404, detail="Annotation not found")
    if (
        annotation.task_id != task_id
        or annotation.annotator_id != body.annotator_id
    ):
        raise HTTPException(
            status_code=403,
            detail="Annotator does not own this annotation",
        )

    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status in LOCKED_TASK_STATUSES:
        raise HTTPException(
            status_code=409,
            detail=f"Task is {task.status}; annotation locked",
        )

    if body.label is not None:
        annotation.label = body.label.model_dump()
    if body.confidence is not None:
        annotation.confidence = body.confidence
    if body.notes is not None:
        annotation.notes = body.notes
    if body.model_suggestion_visible is not None:
        annotation.model_suggestion_visible = body.model_suggestion_visible

    db.commit()
    db.refresh(annotation)

    if task.status == "submitted":
        background_tasks.add_task(jobs.compute_consensus, task_id)

    return AnnotationResponse.model_validate(annotation)


@router.post("/tasks/{task_id}/skip", status_code=204)
def skip_task(task_id: uuid.UUID, db: Session = Depends(get_db)):
    raise NotImplementedError
