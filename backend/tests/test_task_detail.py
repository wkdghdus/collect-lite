"""Tests for GET /api/tasks/{task_id} (task detail endpoint)."""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import (
    Annotation,
    Dataset,
    ModelSuggestion,
    Project,
    SourceExample,
    Task,
    TaskTemplate,
    User,
)
from app.models.task import Assignment


def _seed_task(
    db: Session,
    *,
    payload: dict | None = None,
    task_status: str = "created",
):
    payload = (
        payload
        if payload is not None
        else {
            "query": "neural networks",
            "candidate_document": "neural networks are great",
            "document_id": "row_0",
        }
    )
    project = Project(name="P", task_type="rag_relevance")
    db.add(project)
    db.flush()
    dataset = Dataset(project_id=project.id, filename="d.jsonl", row_count=1)
    db.add(dataset)
    db.flush()
    example = SourceExample(
        dataset_id=dataset.id,
        project_id=project.id,
        source_hash=f"h-{uuid.uuid4()}",
        payload=payload,
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
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    db.refresh(example)
    return {"task": task, "example": example, "project": project, "dataset": dataset}


def _seed_annotator(db: Session, email: str) -> User:
    user = User(email=email, name="Annotator", role="annotator")
    db.add(user)
    db.flush()
    return user


def _seed_assignment(db: Session, task_id: uuid.UUID, annotator_id: uuid.UUID) -> Assignment:
    assignment = Assignment(task_id=task_id, annotator_id=annotator_id, status="assigned")
    db.add(assignment)
    db.flush()
    return assignment


# T1 — query and candidate_document round-trip
def test_get_task_returns_query_and_candidate_document(
    client: TestClient, db_session: Session
) -> None:
    seeded = _seed_task(
        db_session,
        payload={
            "query": "neural networks",
            "candidate_document": "neural networks are great",
            "document_id": "row_0",
        },
    )
    task = seeded["task"]
    response = client.get(f"/api/tasks/{task.id}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(task.id)
    assert body["project_id"] == str(task.project_id)
    assert body["template_id"] == str(task.template_id)
    assert body["example_id"] == str(task.example_id)
    assert body["source_example_id"] == str(task.example_id)
    assert body["dataset_id"] == str(seeded["dataset"].id)
    assert body["status"] == "created"
    assert body["query"] == "neural networks"
    assert body["candidate_document"] == "neural networks are great"


# T2 — document_id and metadata round-trip; absence of metadata yields {}
def test_get_task_returns_document_id_and_metadata(client: TestClient, db_session: Session) -> None:
    seeded_with_meta = _seed_task(
        db_session,
        payload={
            "query": "q",
            "candidate_document": "d",
            "document_id": "doc-42",
            "metadata": {"source": "trec", "year": 2026},
        },
    )
    response = client.get(f"/api/tasks/{seeded_with_meta['task'].id}")
    assert response.status_code == 200
    body = response.json()
    assert body["document_id"] == "doc-42"
    assert body["example_metadata"] == {"source": "trec", "year": 2026}

    seeded_without_meta = _seed_task(
        db_session,
        payload={"query": "q2", "candidate_document": "d2"},
    )
    response = client.get(f"/api/tasks/{seeded_without_meta['task'].id}")
    assert response.status_code == 200
    body = response.json()
    assert body["document_id"] is None
    assert body["example_metadata"] == {}


# T3 — latest model suggestion is selected, with relevance/label fallback
def test_get_task_returns_latest_model_suggestion(client: TestClient, db_session: Session) -> None:
    seeded = _seed_task(db_session)
    task_id = seeded["task"].id
    older_at = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    newer_at = older_at + timedelta(seconds=5)

    older = ModelSuggestion(
        task_id=task_id,
        provider="local",
        model_name="lexical_overlap",
        suggestion={"relevance": "not_relevant"},
        confidence=0.10,
        created_at=older_at,
    )
    newer = ModelSuggestion(
        task_id=task_id,
        provider="cohere",
        model_name="rerank-english-v3.0",
        suggestion={"label": "relevant"},
        confidence=0.91,
        created_at=newer_at,
    )
    db_session.add_all([older, newer])
    db_session.commit()

    response = client.get(f"/api/tasks/{task_id}")
    assert response.status_code == 200
    body = response.json()
    suggestion = body["model_suggestion"]
    assert suggestion is not None
    assert suggestion["provider"] == "cohere"
    assert suggestion["model_name"] == "rerank-english-v3.0"
    assert suggestion["suggested_label"] == "relevant"
    assert suggestion["score"] == 0.91
    assert suggestion["created_at"].startswith("2026-01-01T12:00:05")


# T4 — no suggestion / no annotations returns null and []
def test_get_task_returns_null_model_suggestion_when_absent(
    client: TestClient, db_session: Session
) -> None:
    seeded = _seed_task(db_session)
    response = client.get(f"/api/tasks/{seeded['task'].id}")
    assert response.status_code == 200
    body = response.json()
    assert body["model_suggestion"] is None
    assert body["annotations"] == []


# T5 — annotations included, sorted, narrow shape (no annotator_id / assignment_id)
def test_get_task_returns_annotations(client: TestClient, db_session: Session) -> None:
    seeded = _seed_task(db_session)
    task_id = seeded["task"].id
    annotator = _seed_annotator(db_session, email=f"a-{uuid.uuid4()}@example.com")
    assignment = _seed_assignment(db_session, task_id, annotator.id)
    db_session.commit()

    older_at = datetime(2026, 2, 1, 9, 0, 0, tzinfo=timezone.utc)
    newer_at = older_at + timedelta(seconds=10)

    older = Annotation(
        task_id=task_id,
        assignment_id=assignment.id,
        annotator_id=annotator.id,
        label={"relevance": "relevant"},
        confidence=4,
        notes="first",
        created_at=older_at,
    )
    newer = Annotation(
        task_id=task_id,
        assignment_id=assignment.id,
        annotator_id=annotator.id,
        label={"relevance": "partially_relevant"},
        notes=None,
        created_at=newer_at,
    )
    db_session.add_all([older, newer])
    db_session.commit()

    response = client.get(f"/api/tasks/{task_id}")
    assert response.status_code == 200
    body = response.json()
    annotations = body["annotations"]
    assert len(annotations) == 2
    assert annotations[0]["created_at"] <= annotations[1]["created_at"]
    assert annotations[0]["label"] == {"relevance": "relevant"}
    assert annotations[0]["confidence"] == 4
    assert annotations[0]["notes"] == "first"
    assert annotations[1]["label"] == {"relevance": "partially_relevant"}
    assert annotations[1]["confidence"] is None
    assert annotations[1]["notes"] is None
    for entry in annotations:
        assert set(entry.keys()) == {
            "id",
            "annotator_id",
            "label",
            "confidence",
            "notes",
            "created_at",
            "updated_at",
        }
        assert entry["annotator_id"] == str(annotator.id)
        assert "assignment_id" not in entry


# T6 — unknown task returns 404
def test_get_task_returns_404_for_unknown_task(client: TestClient) -> None:
    response = client.get(f"/api/tasks/{uuid.uuid4()}")
    assert response.status_code == 404
    assert response.json() == {"detail": "Task not found"}
