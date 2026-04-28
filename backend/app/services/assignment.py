import uuid
from sqlalchemy.orm import Session

from app.models.task import Assignment, Task


def get_next_task_for_annotator(db: Session, annotator_id: uuid.UUID) -> Task | None:
    return None


def ensure_assignment(
    db: Session, task_id: uuid.UUID, annotator_id: uuid.UUID
) -> Assignment:
    # Look up regardless of status so a second submission surfaces the existing
    # 'submitted' row — caller's status guard then produces the duplicate 409.
    existing = (
        db.query(Assignment)
        .filter(
            Assignment.task_id == task_id,
            Assignment.annotator_id == annotator_id,
        )
        .first()
    )
    if existing is not None:
        return existing

    assignment = Assignment(
        task_id=task_id,
        annotator_id=annotator_id,
        status="assigned",
    )
    db.add(assignment)
    db.flush()
    return assignment
