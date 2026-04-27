"""Tests for POST /api/tasks/{task_id}/suggestion and the underlying service."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    Dataset,
    ModelSuggestion,
    Project,
    SourceExample,
    Task,
    TaskTemplate,
)
from app.services import cohere_service


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
    return {"task": task, "example": example, "project": project}


# T1
def test_suggestion_route_returns_201(client: TestClient, db_session: Session) -> None:
    seeded = _seed_task(db_session)
    response = client.post(f"/api/tasks/{seeded['task'].id}/suggestion")
    assert response.status_code == 201
    body = response.json()
    assert body["task_id"] == str(seeded["task"].id)
    assert "provider" in body
    assert "model_name" in body
    assert "suggestion" in body
    assert "relevance" in body["suggestion"]
    assert "confidence" in body


# T2
def test_local_fallback_when_cohere_missing(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:

    monkeypatch.setattr(settings, "cohere_api_key", "")
    seeded = _seed_task(
        db_session,
        payload={
            "query": "neural networks ranking",
            "candidate_document": "neural networks ranking great",
            "document_id": "row_0",
        },
    )
    response = client.post(f"/api/tasks/{seeded['task'].id}/suggestion")
    assert response.status_code == 201
    body = response.json()
    assert body["provider"] == "local"
    assert body["model_name"] == "lexical_overlap"
    assert body["raw_response"]["method"] == "jaccard"
    assert body["suggestion"]["relevance"] == "relevant"


# T3
def test_cohere_path_when_api_key_present(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:

    monkeypatch.setattr(settings, "cohere_api_key", "fake-key")

    class _FakeResult:
        relevance_score = 0.55

    class _FakeResponse:
        results = [_FakeResult()]

        def model_dump(self, mode: str = "json") -> dict:
            return {"results": [{"relevance_score": 0.55}]}

    class _FakeClient:
        def __init__(self, *args, **kwargs) -> None: ...
        def rerank(self, **kwargs) -> _FakeResponse:
            return _FakeResponse()

    monkeypatch.setattr(cohere_service, "cohere", type("M", (), {"Client": _FakeClient}))

    seeded = _seed_task(db_session)
    response = client.post(f"/api/tasks/{seeded['task'].id}/suggestion")
    assert response.status_code == 201
    body = response.json()
    assert body["provider"] == "cohere"
    assert body["model_name"] == "rerank-english-v3.0"
    assert body["suggestion"]["relevance"] == "partially_relevant"
    assert body["raw_response"] == {"results": [{"relevance_score": 0.55}]}


# T4 — threshold mapping via the local path
@pytest.mark.parametrize(
    ("query", "document", "expected_label"),
    [
        ("alpha beta gamma", "alpha beta gamma", "relevant"),
        ("alpha beta", "alpha beta gamma", "partially_relevant"),
        ("alpha", "zulu yankee xray", "not_relevant"),
    ],
)
def test_threshold_mapping_via_local_fallback(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    query: str,
    document: str,
    expected_label: str,
) -> None:

    monkeypatch.setattr(settings, "cohere_api_key", "")
    seeded = _seed_task(
        db_session,
        payload={"query": query, "candidate_document": document, "document_id": "row_0"},
    )
    response = client.post(f"/api/tasks/{seeded['task'].id}/suggestion")
    assert response.status_code == 201
    assert response.json()["suggestion"]["relevance"] == expected_label


# T5a
def test_status_transitions_created_to_suggested(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:

    monkeypatch.setattr(settings, "cohere_api_key", "")
    seeded = _seed_task(db_session, task_status="created")
    response = client.post(f"/api/tasks/{seeded['task'].id}/suggestion")
    assert response.status_code == 201
    db_session.expire_all()
    assert db_session.get(Task, seeded["task"].id).status == "suggested"


# T5b
@pytest.mark.parametrize("task_status", ["suggested", "assigned", "submitted", "needs_review"])
def test_status_unchanged_when_not_created(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    task_status: str,
) -> None:

    monkeypatch.setattr(settings, "cohere_api_key", "")
    seeded = _seed_task(db_session, task_status=task_status)
    response = client.post(f"/api/tasks/{seeded['task'].id}/suggestion")
    assert response.status_code == 201
    db_session.expire_all()
    assert db_session.get(Task, seeded["task"].id).status == task_status


# T6
@pytest.mark.parametrize("terminal_status", ["resolved", "exported"])
def test_terminal_task_returns_409(
    client: TestClient,
    db_session: Session,
    terminal_status: str,
) -> None:

    seeded = _seed_task(db_session, task_status=terminal_status)
    response = client.post(f"/api/tasks/{seeded['task'].id}/suggestion")
    assert response.status_code == 409
    assert terminal_status in response.json()["detail"]
    assert (
        db_session.query(ModelSuggestion)
        .filter(ModelSuggestion.task_id == seeded["task"].id)
        .count()
        == 0
    )


# T7
def test_unknown_task_returns_404(client: TestClient) -> None:
    response = client.post(f"/api/tasks/{uuid.uuid4()}/suggestion")
    assert response.status_code == 404


# T8
@pytest.mark.parametrize(
    ("payload", "missing"),
    [
        ({"candidate_document": "x"}, ["query"]),
        ({"query": "x"}, ["candidate_document"]),
        ({}, ["query", "candidate_document"]),
    ],
)
def test_missing_payload_fields_return_422(
    client: TestClient,
    db_session: Session,
    payload: dict,
    missing: list[str],
) -> None:

    seeded = _seed_task(db_session, payload=payload)
    response = client.post(f"/api/tasks/{seeded['task'].id}/suggestion")
    assert response.status_code == 422
    detail = response.json()["detail"]
    for field in missing:
        assert field in detail
    assert (
        db_session.query(ModelSuggestion)
        .filter(ModelSuggestion.task_id == seeded["task"].id)
        .count()
        == 0
    )


# T9 — pure-function unit test
def test_lexical_overlap_score_pure_function() -> None:
    from app.services.model_suggestions import lexical_overlap_score

    assert lexical_overlap_score("alpha beta", "alpha beta") == 1.0
    assert lexical_overlap_score("alpha", "zulu") == 0.0
    assert lexical_overlap_score("Alpha BETA", "alpha gamma") == pytest.approx(1 / 3)
    assert lexical_overlap_score("alpha, beta!", "alpha beta") == 1.0
    assert lexical_overlap_score("", "anything") == 0.0
    assert lexical_overlap_score("anything", "") == 0.0


# T10 — determinism
def test_local_suggestion_deterministic() -> None:
    from app.services.model_suggestions import _local_suggestion

    a = _local_suggestion("alpha beta", "alpha gamma")
    b = _local_suggestion("alpha beta", "alpha gamma")
    assert a == b
