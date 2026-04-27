import uuid

from sqlalchemy.orm import Session, selectinload

from app.models.quality import ConsensusResult, ReviewDecision
from app.models.task import Task
from app.models.user import User
from app.services.audit import log_event

SYSTEM_REVIEWER_EMAIL = "system-reviewer@collectlite.local"


class TaskNotFoundError(Exception):
    pass


class TaskNotInReviewError(Exception):
    def __init__(self, status: str) -> None:
        self.status = status


class ReviewerNotFoundError(Exception):
    pass


def _get_or_create_system_reviewer(db: Session) -> User:
    reviewer = db.query(User).filter(User.email == SYSTEM_REVIEWER_EMAIL).first()
    if reviewer is not None:
        return reviewer
    reviewer = User(
        email=SYSTEM_REVIEWER_EMAIL,
        name="System Reviewer",
        role="reviewer",
    )
    db.add(reviewer)
    db.flush()
    return reviewer


def submit_review_decision(
    db: Session,
    task_id: uuid.UUID,
    final_label: str,
    reason: str | None,
    reviewer_id: uuid.UUID | None,
) -> ReviewDecision:
    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        raise TaskNotFoundError()
    if task.status != "needs_review":
        raise TaskNotInReviewError(task.status)

    if reviewer_id is not None:
        reviewer = db.query(User).filter(User.id == reviewer_id).first()
        if reviewer is None:
            raise ReviewerNotFoundError()
    else:
        reviewer = _get_or_create_system_reviewer(db)

    label_dict = {"relevance": final_label}

    decision = ReviewDecision(
        task_id=task.id,
        reviewer_id=reviewer.id,
        final_label=label_dict,
        reason=reason,
    )
    db.add(decision)

    consensus = (
        db.query(ConsensusResult)
        .filter(ConsensusResult.task_id == task.id)
        .order_by(ConsensusResult.created_at.desc())
        .first()
    )
    if consensus is not None:
        consensus.final_label = label_dict
        consensus.status = "review_resolved"

    task.status = "resolved"

    db.flush()

    log_event(
        db,
        event_type="task.review_submitted",
        entity_type="task",
        entity_id=task.id,
        actor_id=reviewer.id,
        payload={"final_label": final_label, "reason": reason},
    )

    db.refresh(decision)
    return decision


def list_review_queue(db: Session, project_id: uuid.UUID) -> list[Task]:
    return (
        db.query(Task)
        .options(
            selectinload(Task.example),
            selectinload(Task.annotations),
            selectinload(Task.model_suggestions),
            selectinload(Task.consensus_results),
        )
        .filter(Task.project_id == project_id, Task.status == "needs_review")
        .order_by(Task.created_at.desc())
        .all()
    )
