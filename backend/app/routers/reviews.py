import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.project import Project
from app.models.task import Task
from app.schemas.quality import (
    ConsensusResultResponse,
    ReviewDecisionCreate,
    ReviewDecisionResponse,
    ReviewQueueItem,
    ReviewSubmitResponse,
)
from app.schemas.task import (
    AnnotationSummary,
    ModelSuggestionPayload,
    TaskResponse,
)
from app.services.review import (
    ReviewerNotFoundError,
    TaskNotFoundError,
    TaskNotInReviewError,
    list_review_queue,
    submit_review_decision,
)

router = APIRouter(tags=["reviews"])


def _as_dict(value: Any) -> dict:
    """JSONB compiles to TEXT under SQLite tests, so values may round-trip as JSON strings."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except (TypeError, ValueError):
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _build_review_queue_item(task: Task) -> ReviewQueueItem:
    payload = _as_dict(task.example.payload if task.example else {})

    latest_suggestion = max(task.model_suggestions, key=lambda s: s.created_at, default=None)
    suggestion_payload: ModelSuggestionPayload | None = None
    if latest_suggestion is not None:
        s_dict = _as_dict(latest_suggestion.suggestion)
        suggestion_payload = ModelSuggestionPayload(
            provider=latest_suggestion.provider,
            model_name=latest_suggestion.model_name,
            score=(
                float(latest_suggestion.confidence)
                if latest_suggestion.confidence is not None
                else None
            ),
            suggested_label=s_dict.get("relevance") or s_dict.get("label"),
            created_at=latest_suggestion.created_at,
        )

    annotations_summary = sorted(
        (AnnotationSummary.model_validate(a) for a in task.annotations),
        key=lambda a: a.created_at,
    )

    consensus_payload: ConsensusResultResponse | None = None
    latest_consensus = max(task.consensus_results, key=lambda c: c.created_at, default=None)
    if latest_consensus is not None:
        consensus_payload = ConsensusResultResponse(
            id=latest_consensus.id,
            task_id=latest_consensus.task_id,
            final_label=_as_dict(latest_consensus.final_label),
            agreement_score=float(latest_consensus.agreement_score),
            method=latest_consensus.method,
            num_annotations=latest_consensus.num_annotations,
            status=latest_consensus.status,
            created_at=latest_consensus.created_at,
        )

    return ReviewQueueItem(
        **TaskResponse.model_validate(task).model_dump(),
        source_example_id=task.example_id,
        dataset_id=task.example.dataset_id if task.example else None,
        query=str(payload.get("query", "")),
        candidate_document=str(payload.get("candidate_document", "")),
        document_id=payload.get("document_id"),
        example_metadata=payload.get("metadata") or {},
        model_suggestion=suggestion_payload,
        annotations=annotations_summary,
        consensus=consensus_payload,
    )


@router.get(
    "/projects/{project_id}/review/tasks",
    response_model=list[ReviewQueueItem],
)
def list_review_tasks(project_id: uuid.UUID, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    tasks = list_review_queue(db, project_id)
    return [_build_review_queue_item(t) for t in tasks]


@router.post(
    "/tasks/{task_id}/review",
    response_model=ReviewSubmitResponse,
    status_code=200,
)
def submit_review(
    task_id: uuid.UUID,
    body: ReviewDecisionCreate,
    db: Session = Depends(get_db),
):
    try:
        decision = submit_review_decision(
            db,
            task_id=task_id,
            final_label=body.final_label,
            reason=body.reason,
            reviewer_id=body.reviewer_id,
        )
    except TaskNotFoundError:
        raise HTTPException(status_code=404, detail="Task not found")
    except ReviewerNotFoundError:
        raise HTTPException(status_code=404, detail="Reviewer not found")
    except TaskNotInReviewError as e:
        raise HTTPException(
            status_code=409,
            detail=f"Task is {e.status}; cannot submit review",
        )

    return ReviewSubmitResponse(
        review=ReviewDecisionResponse.model_validate(decision),
        task_status="resolved",
    )
