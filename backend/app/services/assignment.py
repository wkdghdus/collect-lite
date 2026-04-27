import uuid
from sqlalchemy.orm import Session

from app.models.task import Assignment, Task


def get_next_task_for_annotator(db: Session, annotator_id: uuid.UUID) -> Task | None:
    """Find highest-priority unassigned task. Returns None if queue is empty."""
    return None


def create_assignment(db: Session, task_id: uuid.UUID, annotator_id: uuid.UUID) -> Assignment:
    """Lock a task to an annotator. Raises if already assigned."""
    raise NotImplementedError
