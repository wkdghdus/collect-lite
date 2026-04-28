import uuid

import pytest

from app.models import (
    Annotation,
    Assignment,
    Dataset,
    ModelSuggestion,
    Project,
    SourceExample,
    Task,
    TaskTemplate,
    User,
)
from app.services.consensus import compute_consensus


def _seed_project(db_session, *, name: str = "P") -> Project:
    project = Project(name=name, task_type="rag_relevance")
    db_session.add(project)
    db_session.flush()
    dataset = Dataset(project_id=project.id, filename="d.jsonl", row_count=1)
    template = TaskTemplate(
        project_id=project.id,
        name="T",
        instructions="Label",
        label_schema={"type": "string"},
    )
    db_session.add_all([dataset, template])
    db_session.flush()
    project._dataset_id = dataset.id
    project._template_id = template.id
    db_session.commit()
    return project


def _add_task(db_session, project: Project, *, status: str) -> Task:
    example = SourceExample(
        dataset_id=project._dataset_id,
        project_id=project.id,
        source_hash=f"h-{uuid.uuid4()}",
        payload={"text": "x"},
    )
    db_session.add(example)
    db_session.flush()
    task = Task(
        project_id=project.id,
        example_id=example.id,
        template_id=project._template_id,
        status=status,
    )
    db_session.add(task)
    db_session.commit()
    return task


def _attach_annotations(db_session, task: Task, label_values: list[str]) -> None:
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


def _attach_suggestion(db_session, task: Task, suggestion: dict) -> None:
    db_session.add(
        ModelSuggestion(
            task_id=task.id,
            provider="cohere",
            model_name="rerank-english-v3.0",
            suggestion=suggestion,
        )
    )
    db_session.commit()


def _resolve_with_humans(db_session, project: Project, label_values: list[str]) -> Task:
    task = _add_task(db_session, project, status="submitted")
    _attach_annotations(db_session, task, label_values)
    compute_consensus(db_session, task.id)
    db_session.expire_all()
    return db_session.get(Task, task.id)


def test_metrics_unknown_project_returns_404(client) -> None:
    response = client.get(f"/api/projects/{uuid.uuid4()}/metrics")
    assert response.status_code == 404
    assert response.json() == {"detail": "Project not found"}


def test_metrics_empty_project_returns_zeros(client, db_session) -> None:
    project = _seed_project(db_session)

    response = client.get(f"/api/projects/{project.id}/metrics")
    assert response.status_code == 200
    body = response.json()
    assert body == {
        "total_tasks": 0,
        "created_count": 0,
        "suggested_count": 0,
        "assigned_count": 0,
        "submitted_count": 0,
        "needs_review_count": 0,
        "resolved_count": 0,
        "exported_count": 0,
        "avg_human_agreement": None,
        "model_human_agreement_rate": None,
        "final_label_distribution": {},
        "exportable_task_count": 0,
    }


def test_metrics_status_counts_sum_to_total(client, db_session) -> None:
    project = _seed_project(db_session)
    plan = {
        "created": 2,
        "suggested": 1,
        "assigned": 3,
        "submitted": 1,
        "needs_review": 2,
        "resolved": 4,
        "exported": 1,
    }
    for status, n in plan.items():
        for _ in range(n):
            _add_task(db_session, project, status=status)

    response = client.get(f"/api/projects/{project.id}/metrics")
    assert response.status_code == 200
    body = response.json()
    assert body["created_count"] == 2
    assert body["suggested_count"] == 1
    assert body["assigned_count"] == 3
    assert body["submitted_count"] == 1
    assert body["needs_review_count"] == 2
    assert body["resolved_count"] == 4
    assert body["exported_count"] == 1
    assert body["total_tasks"] == sum(plan.values())
    assert body["total_tasks"] == (
        body["created_count"]
        + body["suggested_count"]
        + body["assigned_count"]
        + body["submitted_count"]
        + body["needs_review_count"]
        + body["resolved_count"]
        + body["exported_count"]
    )
    assert body["exportable_task_count"] == plan["resolved"]


def test_metrics_label_distribution(client, db_session) -> None:
    project = _seed_project(db_session)
    _resolve_with_humans(db_session, project, ["relevant", "relevant"])
    _resolve_with_humans(db_session, project, ["relevant", "relevant"])
    _resolve_with_humans(db_session, project, ["not_relevant", "not_relevant"])

    response = client.get(f"/api/projects/{project.id}/metrics")
    assert response.status_code == 200
    body = response.json()
    assert body["final_label_distribution"] == {"relevant": 2, "not_relevant": 1}


def test_metrics_avg_human_agreement(client, db_session) -> None:
    project = _seed_project(db_session)
    _resolve_with_humans(db_session, project, ["relevant", "relevant"])
    _resolve_with_humans(db_session, project, ["relevant", "relevant", "not_relevant"])

    response = client.get(f"/api/projects/{project.id}/metrics")
    assert response.status_code == 200
    body = response.json()
    assert body["avg_human_agreement"] == pytest.approx((1.0 + 2 / 3) / 2)


def test_metrics_model_agreement_rate(client, db_session) -> None:
    project = _seed_project(db_session)

    matching = _resolve_with_humans(db_session, project, ["relevant", "relevant"])
    _attach_suggestion(db_session, matching, {"relevance": "relevant"})

    disagreeing = _resolve_with_humans(db_session, project, ["relevant", "relevant"])
    _attach_suggestion(db_session, disagreeing, {"relevance": "not_relevant"})

    _resolve_with_humans(db_session, project, ["relevant", "relevant"])

    response = client.get(f"/api/projects/{project.id}/metrics")
    assert response.status_code == 200
    body = response.json()
    assert body["model_human_agreement_rate"] == pytest.approx(0.5)


def test_metrics_isolation_across_projects(client, db_session) -> None:
    project_a = _seed_project(db_session, name="A")
    project_b = _seed_project(db_session, name="B")

    for _ in range(3):
        _add_task(db_session, project_a, status="created")
    _resolve_with_humans(db_session, project_a, ["relevant", "relevant"])

    for _ in range(5):
        _add_task(db_session, project_b, status="resolved")
    _resolve_with_humans(db_session, project_b, ["not_relevant", "not_relevant"])

    response_a = client.get(f"/api/projects/{project_a.id}/metrics")
    response_b = client.get(f"/api/projects/{project_b.id}/metrics")
    assert response_a.status_code == 200
    assert response_b.status_code == 200
    body_a = response_a.json()
    body_b = response_b.json()

    assert body_a["created_count"] == 3
    assert body_a["resolved_count"] == 1
    assert body_a["total_tasks"] == 4
    assert body_a["final_label_distribution"] == {"relevant": 1}
    assert body_a["exportable_task_count"] == 1

    assert body_b["resolved_count"] == 6
    assert body_b["total_tasks"] == 6
    assert body_b["final_label_distribution"] == {"not_relevant": 1}
    assert body_b["exportable_task_count"] == 6
