import uuid
from sqlalchemy.orm import Session


def submit_review_decision(db: Session, task_id: uuid.UUID, reviewer_id: uuid.UUID, final_label: dict, reason: str | None) -> None:
    """Persist a ReviewDecision and mark the task as resolved."""
    pass
