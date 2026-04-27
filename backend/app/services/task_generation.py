import uuid
from sqlalchemy.orm import Session

from app.models.task import Task


def generate_tasks_for_project(db: Session, project_id: uuid.UUID, template_id: uuid.UUID, required_annotations: int = 2) -> int:
    # Idempotent by (project_id, example_id, template_id)
    return 0
