"""Behavioral tests for backend/scripts/seed.py.

Covers:
- Fresh-DB run produces a fully demo-ready project (users, project, dataset,
  examples, template, tasks, suggestions, annotations, consensus, review).
- Re-running on an already-seeded DB adds zero rows (idempotency).
- Disabling optional flags leaves tasks at status='created' with no model
  suggestions, annotations, or consensus.
"""

from pathlib import Path

from app.models import (
    Annotation,
    Assignment,
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
from scripts.seed import (
    DEMO_USERS,
    LABEL_OPTIONS,
    PROJECT_NAME,
    PROJECT_TASK_TYPE,
    TEMPLATE_NAME,
    seed,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_PATH = REPO_ROOT / "data" / "sample_relevance_tasks.jsonl"


def _row_counts(db) -> dict[str, int]:
    return {
        "users": db.query(User).count(),
        "projects": db.query(Project).count(),
        "datasets": db.query(Dataset).count(),
        "source_examples": db.query(SourceExample).count(),
        "task_templates": db.query(TaskTemplate).count(),
        "tasks": db.query(Task).count(),
        "assignments": db.query(Assignment).count(),
        "annotations": db.query(Annotation).count(),
        "model_suggestions": db.query(ModelSuggestion).count(),
        "consensus_results": db.query(ConsensusResult).count(),
        "review_decisions": db.query(ReviewDecision).count(),
    }


def test_seed_creates_demo_project_fresh_db(db_session) -> None:
    report = seed(sample_path=SAMPLE_PATH, session=db_session)
    db_session.expire_all()

    projects = db_session.query(Project).all()
    assert len(projects) == 1
    project = projects[0]
    assert project.name == PROJECT_NAME
    assert project.task_type == PROJECT_TASK_TYPE
    assert project.status == "active"

    users = {u.email: u for u in db_session.query(User).all()}
    for spec in DEMO_USERS:
        assert spec["email"] in users, f"missing seeded user {spec['email']}"
        assert users[spec["email"]].role == spec["role"]

    assert project.owner_id == users["owner@collectlite.local"].id

    examples = db_session.query(SourceExample).filter(SourceExample.project_id == project.id).all()
    # Pairwise sample (5 rows × 2 candidates) expands to 10 source examples.
    assert len(examples) == 10
    assert all(ex.payload["query"] for ex in examples)
    assert all(ex.payload["candidate_document"] for ex in examples)

    tasks = db_session.query(Task).filter(Task.project_id == project.id).all()
    assert len(tasks) == len(examples)

    suggestions = db_session.query(ModelSuggestion).all()
    assert len(suggestions) == len(tasks)
    for s in suggestions:
        assert s.suggestion["relevance"] in LABEL_OPTIONS

    consensus = (
        db_session.query(ConsensusResult)
        .join(Task, Task.id == ConsensusResult.task_id)
        .filter(Task.project_id == project.id)
        .all()
    )
    assert len(consensus) >= 6
    resolved_count = sum(1 for t in tasks if t.status == "resolved")
    needs_review_count = sum(1 for t in tasks if t.status == "needs_review")
    assert resolved_count >= 4, f"expected >=4 resolved, got {resolved_count}"
    assert needs_review_count >= 2, (
        f"expected >=2 still in needs_review after the seed reviewer override "
        f"(3 disagreement-tasks minus 1 reviewer override), got {needs_review_count}"
    )

    review_decisions = db_session.query(ReviewDecision).all()
    assert len(review_decisions) == 1
    decision = review_decisions[0]
    reviewer = users["carol@collectlite.local"]
    assert decision.reviewer_id == reviewer.id
    assert decision.final_label["relevance"] in LABEL_OPTIONS

    template = db_session.query(TaskTemplate).filter(TaskTemplate.project_id == project.id).one()
    assert template.name == TEMPLATE_NAME
    assert template.label_schema["field"] == "relevance"
    assert template.label_schema["options"] == LABEL_OPTIONS

    assert report.total_created > 0


def test_seed_is_idempotent(db_session) -> None:
    seed(sample_path=SAMPLE_PATH, session=db_session)
    db_session.expire_all()
    first = _row_counts(db_session)

    second_report = seed(sample_path=SAMPLE_PATH, session=db_session)
    db_session.expire_all()
    second = _row_counts(db_session)

    assert second == first, f"row counts changed on re-run: before={first}, after={second}"
    assert second_report.total_created == 0


def test_seed_no_optional_extras(db_session) -> None:
    seed(
        sample_path=SAMPLE_PATH,
        with_suggestions=False,
        with_annotations=False,
        session=db_session,
    )
    db_session.expire_all()

    project = db_session.query(Project).one()
    tasks = db_session.query(Task).filter(Task.project_id == project.id).all()
    assert len(tasks) > 0
    assert all(t.status == "created" for t in tasks)

    assert db_session.query(ModelSuggestion).count() == 0
    assert db_session.query(Annotation).count() == 0
    assert db_session.query(Assignment).count() == 0
    assert db_session.query(ConsensusResult).count() == 0
    assert db_session.query(ReviewDecision).count() == 0


def test_seed_sample_file_exists() -> None:
    """Guard against the fixture path drifting; the seed depends on this file."""
    assert SAMPLE_PATH.exists(), f"missing sample dataset: {SAMPLE_PATH}"
