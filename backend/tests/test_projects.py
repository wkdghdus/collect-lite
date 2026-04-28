import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.task import TaskTemplate
from app.services.task_templates import DEFAULT_TEMPLATES, ensure_default_template


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_projects_empty(client: TestClient) -> None:
    response = client.get("/api/projects")
    assert response.status_code == 200
    assert response.json() == []


def test_create_project(client: TestClient) -> None:
    response = client.post(
        "/api/projects",
        json={"name": "Test Project", "task_type": "classification"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Project"
    assert data["task_type"] == "classification"
    assert data["status"] == "draft"
    assert "id" in data


def test_list_projects_after_create(client: TestClient) -> None:
    client.post("/api/projects", json={"name": "P1", "task_type": "classification"})
    client.post("/api/projects", json={"name": "P2", "task_type": "relevance_rating"})
    response = client.get("/api/projects")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_project_not_found(client: TestClient) -> None:
    response = client.get(f"/api/projects/{uuid.uuid4()}")
    assert response.status_code == 404


def test_create_rag_relevance_project_seeds_default_template(
    client: TestClient, db_session: Session
) -> None:
    response = client.post(
        "/api/projects",
        json={"name": "Seeded", "task_type": "rag_relevance"},
    )
    assert response.status_code == 201
    project_id = uuid.UUID(response.json()["id"])

    templates = db_session.query(TaskTemplate).filter(TaskTemplate.project_id == project_id).all()
    assert len(templates) == 1
    template = templates[0]
    defaults = DEFAULT_TEMPLATES["rag_relevance"]
    assert template.name == defaults["name"]
    assert template.instructions == defaults["instructions"]
    assert template.label_schema == defaults["label_schema"]
    assert template.version == 1


def test_create_unknown_task_type_skips_template(client: TestClient, db_session: Session) -> None:
    response = client.post(
        "/api/projects",
        json={"name": "Other", "task_type": "classification"},
    )
    assert response.status_code == 201
    project_id = uuid.UUID(response.json()["id"])
    templates = db_session.query(TaskTemplate).filter(TaskTemplate.project_id == project_id).all()
    assert templates == []


def test_ensure_default_template_is_idempotent(db_session: Session) -> None:
    project = Project(name="Idem", task_type="rag_relevance", status="draft")
    db_session.add(project)
    db_session.flush()

    first = ensure_default_template(db_session, project)
    second = ensure_default_template(db_session, project)
    db_session.commit()

    assert first is not None
    assert second is not None
    assert first.id == second.id
    count = db_session.query(TaskTemplate).filter(TaskTemplate.project_id == project.id).count()
    assert count == 1


def test_ensure_default_template_returns_none_for_unknown(db_session: Session) -> None:
    project = Project(name="Unk", task_type="classification", status="draft")
    db_session.add(project)
    db_session.flush()

    result = ensure_default_template(db_session, project)
    assert result is None
    db_session.commit()
    count = db_session.query(TaskTemplate).filter(TaskTemplate.project_id == project.id).count()
    assert count == 0
