import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.models import (
    Annotation,
    Assignment,
    ConsensusResult,
    Dataset,
    ModelSuggestion,
    Project,
    SourceExample,
    Task,
    TaskTemplate,
    User,
)
from app.services import consensus as consensus_module
from app.services.consensus import (
    compute_agreement_score,
    compute_consensus,
    compute_majority_vote,
    resolve_task_consensus,
)


def test_majority_vote_single_label() -> None:
    labels = [{"value": "relevant"}, {"value": "relevant"}, {"value": "irrelevant"}]
    result = compute_majority_vote(labels, "value")
    assert result is not None
    assert result["value"] == "relevant"
    assert result["_count"] == 2


def test_majority_vote_empty() -> None:
    result = compute_majority_vote([], "value")
    assert result is None


def test_agreement_score_full_agreement() -> None:
    labels = [{"value": "relevant"}, {"value": "relevant"}]
    score = compute_agreement_score(labels, "value")
    assert score == 1.0


def test_agreement_score_no_agreement() -> None:
    labels = [{"value": "relevant"}, {"value": "irrelevant"}]
    score = compute_agreement_score(labels, "value")
    assert score == 0.5


def _seed_task(db_session, *, label_values: list[str], initial_status: str = "submitted") -> Task:
    project = Project(name="P", task_type="rag_relevance")
    db_session.add(project)
    db_session.flush()

    dataset = Dataset(project_id=project.id, filename="d.jsonl", row_count=1)
    db_session.add(dataset)
    db_session.flush()

    example = SourceExample(
        dataset_id=dataset.id,
        project_id=project.id,
        source_hash=f"h-{uuid.uuid4()}",
        payload={"text": "x"},
    )
    template = TaskTemplate(
        project_id=project.id,
        name="T",
        instructions="Label",
        label_schema={"type": "string"},
    )
    db_session.add_all([example, template])
    db_session.flush()

    task = Task(
        project_id=project.id,
        example_id=example.id,
        template_id=template.id,
        status=initial_status,
    )
    db_session.add(task)
    db_session.flush()

    for value in label_values:
        user = User(email=f"u-{uuid.uuid4()}@example.com", name="A", role="annotator")
        db_session.add(user)
        db_session.flush()
        assignment = Assignment(task_id=task.id, annotator_id=user.id, status="submitted")
        db_session.add(assignment)
        db_session.flush()
        annotation = Annotation(
            task_id=task.id,
            assignment_id=assignment.id,
            annotator_id=user.id,
            label={"relevance": value},
        )
        db_session.add(annotation)

    db_session.commit()
    return task


def _add_annotation(db_session, task: Task, value: str) -> Annotation:
    user = User(email=f"u-{uuid.uuid4()}@example.com", name="A", role="annotator")
    db_session.add(user)
    db_session.flush()
    assignment = Assignment(task_id=task.id, annotator_id=user.id, status="submitted")
    db_session.add(assignment)
    db_session.flush()
    annotation = Annotation(
        task_id=task.id,
        assignment_id=assignment.id,
        annotator_id=user.id,
        label={"relevance": value},
    )
    db_session.add(annotation)
    db_session.commit()
    return annotation


def _add_suggestion(
    db_session,
    task_id: uuid.UUID,
    *,
    suggestion: dict,
    created_at: datetime | None = None,
) -> ModelSuggestion:
    row = ModelSuggestion(
        task_id=task_id,
        provider="cohere",
        model_name="rerank-english-v3.0",
        suggestion=suggestion,
    )
    if created_at is not None:
        row.created_at = created_at
    db_session.add(row)
    db_session.commit()
    return row


def _consensus_for(db_session, task_id: uuid.UUID) -> ConsensusResult | None:
    return (
        db_session.query(ConsensusResult).filter(ConsensusResult.task_id == task_id).one_or_none()
    )


# T1
def test_compute_consensus_full_agreement_no_model_resolves(db_session) -> None:
    task = _seed_task(db_session, label_values=["relevant", "relevant"])

    compute_consensus(db_session, task.id)

    db_session.expire_all()
    refreshed = db_session.get(Task, task.id)
    assert refreshed.status == "resolved"

    result = _consensus_for(db_session, task.id)
    assert result is not None
    assert result.status == "auto_resolved"
    assert float(result.agreement_score) == 1.0
    assert result.num_annotations == 2
    assert result.method == "majority_vote"
    assert result.final_label == {"relevance": "relevant"}


# T2
def test_compute_consensus_model_disagreement_forces_review(db_session) -> None:
    task = _seed_task(db_session, label_values=["relevant", "relevant"])
    _add_suggestion(db_session, task.id, suggestion={"relevance": "not_relevant"})

    compute_consensus(db_session, task.id)

    db_session.expire_all()
    assert db_session.get(Task, task.id).status == "needs_review"
    result = _consensus_for(db_session, task.id)
    assert result is not None
    assert result.status == "needs_review"


# T3
def test_compute_consensus_low_human_agreement_forces_review(db_session) -> None:
    task = _seed_task(db_session, label_values=["relevant", "relevant", "not_relevant"])

    compute_consensus(db_session, task.id)

    db_session.expire_all()
    assert db_session.get(Task, task.id).status == "needs_review"
    result = _consensus_for(db_session, task.id)
    assert result is not None
    assert float(result.agreement_score) == pytest.approx(2 / 3)


# T4
def test_compute_consensus_uses_latest_model_suggestion(db_session) -> None:
    task = _seed_task(db_session, label_values=["relevant", "relevant"])

    older = datetime.now(timezone.utc) - timedelta(hours=2)
    newer = datetime.now(timezone.utc)
    # Older suggestion disagrees; newer suggestion agrees. If "latest" is honored,
    # task resolves; if older were used, task would need review.
    _add_suggestion(db_session, task.id, suggestion={"relevance": "not_relevant"}, created_at=older)
    _add_suggestion(db_session, task.id, suggestion={"relevance": "relevant"}, created_at=newer)

    compute_consensus(db_session, task.id)

    db_session.expire_all()
    assert db_session.get(Task, task.id).status == "resolved"


# T5
def test_compute_consensus_no_suggestion_resolves_from_humans(db_session) -> None:
    task = _seed_task(db_session, label_values=["relevant", "relevant", "relevant"])

    compute_consensus(db_session, task.id)

    db_session.expire_all()
    assert db_session.get(Task, task.id).status == "resolved"
    result = _consensus_for(db_session, task.id)
    assert result is not None
    assert result.status == "auto_resolved"


# T6
def test_compute_consensus_no_annotations_is_noop(db_session) -> None:
    task = _seed_task(db_session, label_values=[], initial_status="submitted")

    compute_consensus(db_session, task.id)

    db_session.expire_all()
    assert db_session.get(Task, task.id).status == "submitted"
    assert _consensus_for(db_session, task.id) is None


# T7
def test_compute_consensus_updates_existing_consensus_result(db_session) -> None:
    task = _seed_task(db_session, label_values=["relevant", "relevant"])
    compute_consensus(db_session, task.id)

    first = _consensus_for(db_session, task.id)
    assert first is not None
    first_id = first.id

    _add_annotation(db_session, task, "not_relevant")
    compute_consensus(db_session, task.id)

    db_session.expire_all()
    rows = db_session.query(ConsensusResult).filter(ConsensusResult.task_id == task.id).all()
    assert len(rows) == 1
    updated = rows[0]
    assert updated.id == first_id
    assert updated.num_annotations == 3
    assert float(updated.agreement_score) == pytest.approx(2 / 3)
    assert updated.status == "needs_review"
    assert db_session.get(Task, task.id).status == "needs_review"


# T8
def test_resolve_task_consensus_delegates_to_compute_consensus(monkeypatch) -> None:
    calls: list[tuple] = []

    def fake_compute(db, task_id):
        calls.append((db, task_id))

    monkeypatch.setattr(consensus_module, "compute_consensus", fake_compute)

    sentinel_db = object()
    sentinel_id = uuid.uuid4()
    resolve_task_consensus(sentinel_db, sentinel_id)

    assert calls == [(sentinel_db, sentinel_id)]


# T9
def test_compute_consensus_uses_label_fallback_key(db_session) -> None:
    task = _seed_task(db_session, label_values=["relevant", "relevant"])
    _add_suggestion(db_session, task.id, suggestion={"label": "relevant"})

    compute_consensus(db_session, task.id)

    db_session.expire_all()
    assert db_session.get(Task, task.id).status == "resolved"


# T10
def test_compute_consensus_malformed_model_suggestion_forces_review(db_session) -> None:
    task = _seed_task(db_session, label_values=["relevant", "relevant"])
    _add_suggestion(db_session, task.id, suggestion={"unexpected_key": "x"})

    compute_consensus(db_session, task.id)

    db_session.expire_all()
    assert db_session.get(Task, task.id).status == "needs_review"
    result = _consensus_for(db_session, task.id)
    assert result is not None
    assert result.status == "needs_review"


# T10b
def test_compute_consensus_empty_model_suggestion_forces_review(db_session) -> None:
    task = _seed_task(db_session, label_values=["relevant", "relevant"])
    _add_suggestion(db_session, task.id, suggestion={})

    compute_consensus(db_session, task.id)

    db_session.expire_all()
    assert db_session.get(Task, task.id).status == "needs_review"
    result = _consensus_for(db_session, task.id)
    assert result is not None
    assert result.status == "needs_review"
