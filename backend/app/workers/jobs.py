import uuid
from sqlalchemy.orm import Session

from app.db import SessionLocal


def _get_db() -> Session:
    return SessionLocal()


def generate_tasks(project_id: uuid.UUID, template_id: uuid.UUID, required_annotations: int = 2) -> None:
    from app.services.task_generation import generate_tasks_for_project
    db = _get_db()
    try:
        generate_tasks_for_project(db, project_id, template_id, required_annotations)
    finally:
        db.close()


def run_model_suggestions(project_id: uuid.UUID) -> None:
    from app.services.model_suggestions import generate_suggestion_for_task  # noqa: F401
    db = _get_db()
    try:
        pass
    finally:
        db.close()


def compute_consensus(task_id: uuid.UUID) -> None:
    from app.services.consensus import resolve_task_consensus
    db = _get_db()
    try:
        resolve_task_consensus(db, task_id)
    finally:
        db.close()


def create_export(export_id: uuid.UUID) -> None:
    from app.services.export import run_export_job
    db = _get_db()
    try:
        run_export_job(db, export_id)
    finally:
        db.close()


def refresh_metrics(project_id: uuid.UUID) -> None:
    db = _get_db()
    try:
        pass
    finally:
        db.close()
