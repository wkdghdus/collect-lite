"""Tests for the review queue (GET) and review submit (POST) endpoints."""

import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import (
    Annotation,
    AuditEvent,
    ConsensusResult,
    Dataset,
    ModelSuggestion,
    Project,
    ReviewDecision,
    SourceExample,
    Task,
    TaskTemplate,
    User,
)
from app.models.task import Assignment
from app.services.review import SYSTEM_REVIEWER_EMAIL


def _project(db: Session, name: str = "P") -> Project:
    project = Project(name=name, task_type="rag_relevance")
    db.add(project)
    db.flush()
    return project


def _seed_task(
    db: Session,
    *,
    project: Project | None = None,
    payload: dict | None = None,
    status: str = "needs_review",
    with_consensus: bool = True,
    consensus_status: str = "needs_review",
) -> Task:
    project = project or _project(db)
    payload = (
        payload
        if payload is not None
        else {
            "query": "neural networks",
            "candidate_document": "neural networks are great",
            "document_id": "row_0",
        }
    )
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
        status=status,
    )
    db.add(task)
    db.flush()
    if with_consensus:
        consensus = ConsensusResult(
            task_id=task.id,
            final_label={"relevance": "relevant"},
            agreement_score=0.5,
            method="majority_vote",
            num_annotations=2,
            status=consensus_status,
        )
        db.add(consensus)
    db.commit()
    db.refresh(task)
    return task


def _seed_annotation(db: Session, task: Task, value: str = "relevant") -> Annotation:
    user = User(email=f"u-{uuid.uuid4()}@example.com", name="A", role="annotator")
    db.add(user)
    db.flush()
    assignment = Assignment(task_id=task.id, annotator_id=user.id, status="submitted")
    db.add(assignment)
    db.flush()
    annotation = Annotation(
        task_id=task.id,
        assignment_id=assignment.id,
        annotator_id=user.id,
        label={"relevance": value},
    )
    db.add(annotation)
    db.commit()
    return annotation


def _seed_suggestion(
    db: Session,
    task: Task,
    *,
    suggested_label: str = "relevant",
    score: float = 0.91,
) -> ModelSuggestion:
    suggestion = ModelSuggestion(
        task_id=task.id,
        provider="cohere",
        model_name="rerank-english-v3.0",
        suggestion={"relevance": suggested_label},
        confidence=score,
    )
    db.add(suggestion)
    db.commit()
    return suggestion


def _label_dict(value) -> dict:
    """JSONB columns round-trip through SQLite-as-TEXT in tests; decode consistently."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            return {}
    return {}


def test_list_review_tasks_returns_only_needs_review_in_project(
    client: TestClient, db_session: Session
) -> None:
    project_a = _project(db_session, name="A")
    project_b = _project(db_session, name="B")

    target = _seed_task(db_session, project=project_a, status="needs_review")
    _seed_task(db_session, project=project_a, status="resolved", with_consensus=False)
    _seed_task(db_session, project=project_a, status="submitted", with_consensus=False)
    _seed_task(db_session, project=project_b, status="needs_review")

    _seed_annotation(db_session, target, "relevant")
    _seed_suggestion(db_session, target, suggested_label="not_relevant")

    response = client.get(f"/api/projects/{project_a.id}/review/tasks")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) == 1

    item = body[0]
    assert item["id"] == str(target.id)
    assert item["status"] == "needs_review"
    assert item["query"] == "neural networks"
    assert item["candidate_document"] == "neural networks are great"
    assert item["document_id"] == "row_0"
    assert item["example_metadata"] == {}
    assert item["model_suggestion"] is not None
    assert item["model_suggestion"]["suggested_label"] == "not_relevant"
    assert len(item["annotations"]) == 1
    assert item["annotations"][0]["label"] == {"relevance": "relevant"}
    assert item["consensus"] is not None
    assert item["consensus"]["status"] == "needs_review"


def test_list_review_tasks_unknown_project_returns_404(client: TestClient) -> None:
    response = client.get(f"/api/projects/{uuid.uuid4()}/review/tasks")
    assert response.status_code == 404
    assert response.json() == {"detail": "Project not found"}


def test_list_review_tasks_includes_consensus_block(
    client: TestClient, db_session: Session
) -> None:
    project = _project(db_session)
    task = _seed_task(db_session, project=project, with_consensus=False)
    consensus = ConsensusResult(
        task_id=task.id,
        final_label={"relevance": "partially_relevant"},
        agreement_score=0.5,
        method="majority_vote",
        num_annotations=2,
        status="needs_review",
    )
    db_session.add(consensus)
    db_session.commit()

    response = client.get(f"/api/projects/{project.id}/review/tasks")
    assert response.status_code == 200
    [item] = response.json()
    assert item["consensus"]["status"] == "needs_review"
    assert item["consensus"]["agreement_score"] == 0.5
    assert item["consensus"]["num_annotations"] == 2
    assert item["consensus"]["method"] == "majority_vote"
    assert item["consensus"]["final_label"] == {"relevance": "partially_relevant"}


def test_list_review_tasks_orders_newest_first(client: TestClient, db_session: Session) -> None:
    project = _project(db_session)
    older = _seed_task(db_session, project=project)
    newer = _seed_task(db_session, project=project)
    older.created_at = datetime.now(timezone.utc) - timedelta(hours=2)
    newer.created_at = datetime.now(timezone.utc)
    db_session.commit()

    response = client.get(f"/api/projects/{project.id}/review/tasks")
    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body] == [str(newer.id), str(older.id)]


def test_submit_review_creates_decision_and_resolves_task(
    client: TestClient, db_session: Session
) -> None:
    task = _seed_task(db_session)
    response = client.post(
        f"/api/tasks/{task.id}/review",
        json={"final_label": "relevant", "reason": "doc directly answers the query"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["task_status"] == "resolved"
    assert body["review"]["task_id"] == str(task.id)
    assert body["review"]["final_label"] == {"relevance": "relevant"}
    assert body["review"]["reason"] == "doc directly answers the query"

    db_session.expire_all()
    decisions = db_session.query(ReviewDecision).filter(ReviewDecision.task_id == task.id).all()
    assert len(decisions) == 1
    decision = decisions[0]
    assert _label_dict(decision.final_label) == {"relevance": "relevant"}
    assert decision.reason == "doc directly answers the query"
    assert decision.reviewer_id is not None

    refreshed_task = db_session.get(Task, task.id)
    assert refreshed_task.status == "resolved"

    consensus = db_session.query(ConsensusResult).filter(ConsensusResult.task_id == task.id).one()
    assert _label_dict(consensus.final_label) == {"relevance": "relevant"}
    assert consensus.status == "review_resolved"

    audits = (
        db_session.query(AuditEvent)
        .filter(
            AuditEvent.entity_id == task.id,
            AuditEvent.event_type == "task.review_submitted",
        )
        .all()
    )
    assert len(audits) == 1
    audit = audits[0]
    assert audit.entity_type == "task"
    assert audit.actor_id == decision.reviewer_id
    payload = _label_dict(audit.payload)
    assert payload["final_label"] == "relevant"
    assert payload["reason"] == "doc directly answers the query"


def test_submit_review_uses_system_reviewer_when_omitted(
    client: TestClient, db_session: Session
) -> None:
    task1 = _seed_task(db_session)
    task2 = _seed_task(db_session)
    for task in (task1, task2):
        response = client.post(
            f"/api/tasks/{task.id}/review",
            json={"final_label": "relevant"},
        )
        assert response.status_code == 200

    db_session.expire_all()
    system_reviewers = db_session.query(User).filter(User.email == SYSTEM_REVIEWER_EMAIL).all()
    assert len(system_reviewers) == 1
    assert system_reviewers[0].role == "reviewer"

    decisions = db_session.query(ReviewDecision).all()
    assert len(decisions) == 2
    assert {d.reviewer_id for d in decisions} == {system_reviewers[0].id}


def test_submit_review_with_explicit_reviewer_id(client: TestClient, db_session: Session) -> None:
    reviewer = User(email=f"reviewer-{uuid.uuid4()}@example.com", name="R", role="reviewer")
    db_session.add(reviewer)
    db_session.commit()
    db_session.refresh(reviewer)

    task = _seed_task(db_session)
    response = client.post(
        f"/api/tasks/{task.id}/review",
        json={"final_label": "not_relevant", "reviewer_id": str(reviewer.id)},
    )
    assert response.status_code == 200

    db_session.expire_all()
    decision = db_session.query(ReviewDecision).filter(ReviewDecision.task_id == task.id).one()
    assert decision.reviewer_id == reviewer.id

    system_reviewers = db_session.query(User).filter(User.email == SYSTEM_REVIEWER_EMAIL).all()
    assert system_reviewers == []


def test_submit_review_unknown_reviewer_returns_404(
    client: TestClient, db_session: Session
) -> None:
    task = _seed_task(db_session)
    response = client.post(
        f"/api/tasks/{task.id}/review",
        json={"final_label": "relevant", "reviewer_id": str(uuid.uuid4())},
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Reviewer not found"}

    db_session.expire_all()
    assert db_session.query(ReviewDecision).count() == 0
    assert db_session.get(Task, task.id).status == "needs_review"


@pytest.mark.parametrize(
    "label",
    ["relevant", "partially_relevant", "not_relevant"],
)
def test_submit_review_accepts_each_valid_label(
    client: TestClient, db_session: Session, label: str
) -> None:
    task = _seed_task(db_session)
    response = client.post(
        f"/api/tasks/{task.id}/review",
        json={"final_label": label},
    )
    assert response.status_code == 200

    db_session.expire_all()
    decision = db_session.query(ReviewDecision).filter(ReviewDecision.task_id == task.id).one()
    assert _label_dict(decision.final_label) == {"relevance": label}
    assert db_session.get(Task, task.id).status == "resolved"
    consensus = db_session.query(ConsensusResult).filter(ConsensusResult.task_id == task.id).one()
    assert consensus.status == "review_resolved"
    assert _label_dict(consensus.final_label) == {"relevance": label}


@pytest.mark.parametrize(
    "body",
    [
        {"final_label": "kinda_relevant"},
        {"final_label": ""},
        {"final_label": "RELEVANT"},
        {"reason": "missing label"},
    ],
)
def test_submit_review_invalid_label_returns_422(
    client: TestClient, db_session: Session, body: dict
) -> None:
    task = _seed_task(db_session)
    response = client.post(f"/api/tasks/{task.id}/review", json=body)
    assert response.status_code == 422

    db_session.expire_all()
    assert db_session.query(ReviewDecision).count() == 0
    assert db_session.query(AuditEvent).count() == 0
    assert db_session.get(Task, task.id).status == "needs_review"


def test_submit_review_409_on_resolved_task(client: TestClient, db_session: Session) -> None:
    task = _seed_task(db_session, status="resolved", with_consensus=False)
    response = client.post(
        f"/api/tasks/{task.id}/review",
        json={"final_label": "relevant"},
    )
    assert response.status_code == 409
    assert "resolved" in response.json()["detail"]

    db_session.expire_all()
    assert db_session.query(ReviewDecision).count() == 0
    assert db_session.query(AuditEvent).count() == 0


def test_submit_review_409_on_exported_task(client: TestClient, db_session: Session) -> None:
    task = _seed_task(db_session, status="exported", with_consensus=False)
    response = client.post(
        f"/api/tasks/{task.id}/review",
        json={"final_label": "relevant"},
    )
    assert response.status_code == 409
    assert "exported" in response.json()["detail"]

    db_session.expire_all()
    assert db_session.query(ReviewDecision).count() == 0


@pytest.mark.parametrize("status", ["created", "suggested", "assigned", "submitted"])
def test_submit_review_409_on_pre_review_states(
    client: TestClient, db_session: Session, status: str
) -> None:
    task = _seed_task(db_session, status=status, with_consensus=False)
    response = client.post(
        f"/api/tasks/{task.id}/review",
        json={"final_label": "relevant"},
    )
    assert response.status_code == 409
    assert status in response.json()["detail"]

    db_session.expire_all()
    assert db_session.query(ReviewDecision).count() == 0


def test_submit_review_unknown_task_returns_404(client: TestClient, db_session: Session) -> None:
    response = client.post(
        f"/api/tasks/{uuid.uuid4()}/review",
        json={"final_label": "relevant"},
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Task not found"}
