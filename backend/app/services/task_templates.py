"""Default-template provisioning for projects.

Centralises the template content for each supported ``task_type`` so the
projects router and the seed script stay in sync.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.task import TaskTemplate

DEFAULT_TEMPLATES: dict[str, dict] = {
    "rag_relevance": {
        "name": "RAG Relevance v1",
        "instructions": (
            "Read the query and the candidate document. Mark the document "
            "'relevant' if it directly answers the query, 'partially_relevant' "
            "if it touches the same topic but does not answer the question, or "
            "'not_relevant' if it is off-topic."
        ),
        "label_schema": {
            "type": "single_choice",
            "field": "relevance",
            "options": ["relevant", "partially_relevant", "not_relevant"],
        },
    },
}


def ensure_default_template(db: Session, project: Project) -> TaskTemplate | None:
    """Return the existing default template for the project, or create it.

    Looks up by ``(project_id, name)`` so a second invocation is a no-op.
    Returns ``None`` for task types without a known default (the project is
    still created; callers can manage templates manually).
    """
    defaults = DEFAULT_TEMPLATES.get(project.task_type)
    if defaults is None:
        return None

    existing = (
        db.query(TaskTemplate)
        .filter(
            TaskTemplate.project_id == project.id,
            TaskTemplate.name == defaults["name"],
        )
        .first()
    )
    if existing is not None:
        return existing

    template = TaskTemplate(
        project_id=project.id,
        name=defaults["name"],
        instructions=defaults["instructions"],
        label_schema=defaults["label_schema"],
        version=1,
    )
    db.add(template)
    db.flush()
    return template
