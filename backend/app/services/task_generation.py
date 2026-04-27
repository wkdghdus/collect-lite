import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.dataset import SourceExample
from app.models.task import Task


def generate_tasks_for_project(
    db: Session,
    project_id: uuid.UUID,
    template_id: uuid.UUID,
    required_annotations: int = 2,
) -> int:
    existing_example_ids = select(Task.example_id).where(
        Task.project_id == project_id,
        Task.template_id == template_id,
    )
    examples_to_seed = (
        db.query(SourceExample.id)
        .filter(
            SourceExample.project_id == project_id,
            SourceExample.id.notin_(existing_example_ids),
        )
        .all()
    )
    if not examples_to_seed:
        return 0

    db.add_all(
        Task(
            project_id=project_id,
            example_id=row.id,
            template_id=template_id,
            status="created",
            priority=0,
            required_annotations=required_annotations,
        )
        for row in examples_to_seed
    )
    db.commit()
    return len(examples_to_seed)
