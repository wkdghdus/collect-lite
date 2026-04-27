import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import (
    Annotation,
    Assignment,
    Dataset,
    Project,
    SourceExample,
    Task,
    TaskTemplate,
    User,
)


def _seed_task(
    db: Session,
    *,
    required_annotations: int = 2,
    task_status: str = "assigned",
    assignment_status: str = "assigned",
):
    user = User(email=f"u-{uuid.uuid4()}@example.com", name="A", role="annotator")
    project = Project(name="P", task_type="rag_relevance")
    db.add_all([user, project])
    db.flush()
    dataset = Dataset(project_id=project.id, filename="d.jsonl", row_count=1)
    db.add(dataset)
    db.flush()
    example = SourceExample(
        dataset_id=dataset.id,
        project_id=project.id,
        source_hash=f"h-{uuid.uuid4()}",
        payload={"q": "?", "doc": "."},
    )
    template = TaskTemplate(
        project_id=project.id,
        name="t",
        instructions="x",
        label_schema={"type": "object"},
    )
    db.add_all([example, template])
    db.flush()
    task = Task(
        project_id=project.id,
        example_id=example.id,
        template_id=template.id,
        status=task_status,
        required_annotations=required_annotations,
    )
    db.add(task)
    db.flush()
    assignment = Assignment(
        task_id=task.id,
        annotator_id=user.id,
        status=assignment_status,
    )
    db.add(assignment)
    db.commit()
    return {"task": task, "assignment": assignment, "user": user}


def _valid_body(assignment_id: uuid.UUID, **overrides) -> dict:
    body = {
        "assignment_id": str(assignment_id),
        "label": {"relevance": "relevant"},
        "confidence": 4,
    }
    body.update(overrides)
    return body


def test_submit_annotation_success(client: TestClient, db_session: Session) -> None:
    seeded = _seed_task(db_session, required_annotations=2)
    task = seeded["task"]
    assignment = seeded["assignment"]

    response = client.post(
        f"/api/tasks/{task.id}/annotations",
        json=_valid_body(assignment.id),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["task_status"] == "assigned"
    annotation = body["annotation"]
    assert "id" in annotation
    assert annotation["task_id"] == str(task.id)
    assert annotation["assignment_id"] == str(assignment.id)
    assert annotation["annotator_id"] == str(seeded["user"].id)

    db_session.expire_all()
    refreshed_assignment = db_session.get(Assignment, assignment.id)
    assert refreshed_assignment.status == "submitted"
    assert refreshed_assignment.submitted_at is not None
    assert db_session.query(Annotation).filter(Annotation.task_id == task.id).count() == 1


def test_annotator_id_derived_from_assignment(client: TestClient, db_session: Session) -> None:
    seeded = _seed_task(db_session, required_annotations=2)
    task = seeded["task"]
    assignment = seeded["assignment"]

    response = client.post(
        f"/api/tasks/{task.id}/annotations",
        json=_valid_body(assignment.id),
    )

    assert response.status_code == 201
    annotator_id = response.json()["annotation"]["annotator_id"]
    assert annotator_id == str(seeded["user"].id)
    assert annotator_id == str(assignment.annotator_id)


def test_assignment_task_mismatch_returns_400(client: TestClient, db_session: Session) -> None:
    task_a = _seed_task(db_session)["task"]
    seeded_b = _seed_task(db_session)
    other_assignment = seeded_b["assignment"]

    response = client.post(
        f"/api/tasks/{task_a.id}/annotations",
        json=_valid_body(other_assignment.id),
    )

    assert response.status_code == 400
    assert "does not belong" in response.json()["detail"]


def test_missing_task_returns_404(client: TestClient) -> None:
    response = client.post(
        f"/api/tasks/{uuid.uuid4()}/annotations",
        json=_valid_body(uuid.uuid4()),
    )
    assert response.status_code == 404


def test_missing_assignment_returns_404(client: TestClient, db_session: Session) -> None:
    task = _seed_task(db_session)["task"]
    response = client.post(
        f"/api/tasks/{task.id}/annotations",
        json=_valid_body(uuid.uuid4()),
    )
    assert response.status_code == 404


@pytest.mark.parametrize("terminal_status", ["resolved", "exported"])
def test_terminal_task_returns_409(
    client: TestClient, db_session: Session, terminal_status: str
) -> None:
    seeded = _seed_task(db_session, task_status=terminal_status)
    response = client.post(
        f"/api/tasks/{seeded['task'].id}/annotations",
        json=_valid_body(seeded["assignment"].id),
    )
    assert response.status_code == 409


def test_invalid_relevance_returns_422(client: TestClient, db_session: Session) -> None:
    seeded = _seed_task(db_session)
    response = client.post(
        f"/api/tasks/{seeded['task'].id}/annotations",
        json={
            "assignment_id": str(seeded["assignment"].id),
            "label": {"relevance": "maybe"},
            "confidence": 4,
        },
    )
    assert response.status_code == 422


def test_confidence_out_of_range_returns_422(client: TestClient, db_session: Session) -> None:
    seeded = _seed_task(db_session)
    response = client.post(
        f"/api/tasks/{seeded['task'].id}/annotations",
        json=_valid_body(seeded["assignment"].id, confidence=7),
    )
    assert response.status_code == 422


def test_first_annotation_keeps_assigned(client: TestClient, db_session: Session) -> None:
    seeded = _seed_task(db_session, required_annotations=2)
    response = client.post(
        f"/api/tasks/{seeded['task'].id}/annotations",
        json=_valid_body(seeded["assignment"].id),
    )

    assert response.status_code == 201
    assert response.json()["task_status"] == "assigned"
    db_session.expire_all()
    assert db_session.get(Task, seeded["task"].id).status == "assigned"


def test_threshold_annotation_marks_submitted(client: TestClient, db_session: Session) -> None:
    seeded = _seed_task(db_session, required_annotations=1)
    response = client.post(
        f"/api/tasks/{seeded['task'].id}/annotations",
        json=_valid_body(seeded["assignment"].id),
    )

    assert response.status_code == 201
    assert response.json()["task_status"] == "submitted"
    db_session.expire_all()
    assert db_session.get(Task, seeded["task"].id).status == "submitted"


def test_assignment_already_submitted_returns_409(client: TestClient, db_session: Session) -> None:
    seeded = _seed_task(db_session, assignment_status="submitted")
    response = client.post(
        f"/api/tasks/{seeded['task'].id}/annotations",
        json=_valid_body(seeded["assignment"].id),
    )
    assert response.status_code == 409


def test_consensus_scheduled_not_blocking(client: TestClient, db_session: Session) -> None:
    seeded = _seed_task(db_session, required_annotations=1)
    task_id = seeded["task"].id
    mock = MagicMock()

    with patch("app.routers.annotations.jobs.compute_consensus", mock):
        response = client.post(
            f"/api/tasks/{task_id}/annotations",
            json=_valid_body(seeded["assignment"].id),
        )

    assert response.status_code == 201
    mock.assert_called_once_with(task_id)
