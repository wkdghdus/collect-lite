"""Default-template provisioning for projects.

Centralises the template-content for each supported `task_type` so the
projects router and the seed script stay in sync.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.task import TaskTemplate

RAG_RELEVANCE = "rag_relevance"

RAG_RELEVANCE_LABEL_OPTIONS = ["relevant", "partially_relevant", "not_relevant"]

DEFAULT_TEMPLATE_NAME = {
    RAG_RELEVANCE: "RAG Relevance v1",
}

DEFAULT_TEMPLATE_INSTRUCTIONS = {
    RAG_RELEVANCE: (
        "Read the query and the candidate document. Mark the document "
        "'relevant' if it directly answers the query, 'partially_relevant' "
        "if it touches the same topic but does not answer the question, or "
        "'not_relevant' if it is off-topic."
    ),
}

DEFAULT_TEMPLATE_LABEL_SCHEMA = {
    RAG_RELEVANCE: {
        "type": "single_choice",
        "field": "relevance",
        "options": RAG_RELEVANCE_LABEL_OPTIONS,
    },
}


def ensure_default_template(db: Session, project: Project) -> TaskTemplate | None:
    """Return the existing default template for the project, or create it.

    Looks up by `(project_id, name)` so a second invocation is a no-op.
    Returns ``None`` for task types without a known default (the project is
    still created; callers can manage templates manually).
    """
    if project.task_type not in DEFAULT_TEMPLATE_NAME:
        return None

    name = DEFAULT_TEMPLATE_NAME[project.task_type]
    existing = (
        db.query(TaskTemplate)
        .filter(TaskTemplate.project_id == project.id, TaskTemplate.name == name)
        .first()
    )
    if existing is not None:
        return existing

    template = TaskTemplate(
        project_id=project.id,
        name=name,
        instructions=DEFAULT_TEMPLATE_INSTRUCTIONS[project.task_type],
        label_schema=DEFAULT_TEMPLATE_LABEL_SCHEMA[project.task_type],
        version=1,
    )
    db.add(template)
    db.flush()
    return template
