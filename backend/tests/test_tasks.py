import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.annotation import Annotation
from app.models.dataset import Dataset, SourceExample
from app.models.project import Project
from app.models.task import Assignment, Task, TaskTemplate
from app.models.user import User


def _seed_project(db: Session, task_type: str = "rag_relevance") -> Project:
    project = Project(name="P", task_type=task_type, status="draft")
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def _seed_template(db: Session, project_id: uuid.UUID) -> TaskTemplate:
    template = TaskTemplate(
        project_id=project_id,
        name="rag-rel",
        instructions="Rate relevance",
        label_schema={"type": "categorical", "options": ["relevant", "not"]},
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


def _seed_examples(db: Session, project_id: uuid.UUID, count: int, hash_prefix: str = "h"):
    dataset = Dataset(project_id=project_id, filename=f"{hash_prefix}.jsonl", row_count=count)
    db.add(dataset)
    db.flush()
    examples = [
        SourceExample(
            dataset_id=dataset.id,
            project_id=project_id,
            external_id=f"row_{i}",
            source_hash=f"{hash_prefix}_{i}",
            payload={"query": f"q{i}", "candidate_document": f"d{i}", "document_id": f"row_{i}"},
        )
        for i in range(count)
    ]
    db.add_all(examples)
    db.commit()
    db.refresh(dataset)
    return dataset, examples


def test_get_next_task_route_exists(client: TestClient) -> None:
    response = client.get("/api/tasks/next")
    assert response.status_code in (200, 500)


def test_generate_tasks_route_exists(client: TestClient) -> None:
    project_id = uuid.uuid4()
    template_id = uuid.uuid4()
    response = client.post(
        f"/api/projects/{project_id}/tasks/generate",
        json={
            "template_id": str(template_id),
            "dataset_id": str(uuid.uuid4()),
            "required_annotations": 2,
        },
    )
    assert response.status_code in (202, 404, 400, 500)


def test_generate_tasks_creates_one_task_per_example(
    client: TestClient, db_session: Session
) -> None:
    project = _seed_project(db_session)
    template = _seed_template(db_session, project.id)
    dataset, examples = _seed_examples(db_session, project.id, count=3)
    seeded_example_ids = {ex.id for ex in examples}

    response = client.post(
        f"/api/projects/{project.id}/tasks/generate",
        json={
            "template_id": str(template.id),
            "dataset_id": str(dataset.id),
            "required_annotations": 2,
        },
    )

    assert response.status_code == 202
    assert response.json() == {"status": "queued", "project_id": str(project.id)}

    tasks = db_session.query(Task).filter(Task.project_id == project.id).all()
    assert len(tasks) == 3
    assert {t.example_id for t in tasks} == seeded_example_ids
    for task in tasks:
        assert task.template_id == template.id
        assert task.status == "created"
        assert task.priority == 0
        assert task.required_annotations == 2


def test_generate_tasks_is_idempotent(client: TestClient, db_session: Session) -> None:
    project = _seed_project(db_session)
    template = _seed_template(db_session, project.id)
    dataset, _ = _seed_examples(db_session, project.id, count=4)

    payload = {
        "template_id": str(template.id),
        "dataset_id": str(dataset.id),
        "required_annotations": 2,
    }
    first = client.post(f"/api/projects/{project.id}/tasks/generate", json=payload)
    second = client.post(f"/api/projects/{project.id}/tasks/generate", json=payload)

    assert first.status_code == 202
    assert second.status_code == 202
    assert db_session.query(Task).filter(Task.project_id == project.id).count() == 4


def test_generate_tasks_inserts_only_new_examples_on_rerun(
    client: TestClient, db_session: Session
) -> None:
    project = _seed_project(db_session)
    template = _seed_template(db_session, project.id)
    dataset_a, _ = _seed_examples(db_session, project.id, count=3, hash_prefix="batch1")

    payload_a = {
        "template_id": str(template.id),
        "dataset_id": str(dataset_a.id),
        "required_annotations": 2,
    }
    client.post(f"/api/projects/{project.id}/tasks/generate", json=payload_a)
    dataset_b, new_examples = _seed_examples(db_session, project.id, count=2, hash_prefix="batch2")
    payload_b = {
        "template_id": str(template.id),
        "dataset_id": str(dataset_b.id),
        "required_annotations": 2,
    }
    client.post(f"/api/projects/{project.id}/tasks/generate", json=payload_b)

    tasks = db_session.query(Task).filter(Task.project_id == project.id).all()
    assert len(tasks) == 5
    new_example_ids = {ex.id for ex in new_examples}
    new_task_example_ids = {t.example_id for t in tasks if t.example_id in new_example_ids}
    assert new_task_example_ids == new_example_ids


def test_generate_tasks_404_for_unknown_project(client: TestClient) -> None:
    response = client.post(
        f"/api/projects/{uuid.uuid4()}/tasks/generate",
        json={
            "template_id": str(uuid.uuid4()),
            "dataset_id": str(uuid.uuid4()),
            "required_annotations": 2,
        },
    )
    assert response.status_code == 404


def test_generate_tasks_400_for_wrong_task_type(client: TestClient, db_session: Session) -> None:
    project = _seed_project(db_session, task_type="other")
    template = _seed_template(db_session, project.id)

    response = client.post(
        f"/api/projects/{project.id}/tasks/generate",
        json={
            "template_id": str(template.id),
            "dataset_id": str(uuid.uuid4()),
            "required_annotations": 2,
        },
    )

    assert response.status_code == 400


def test_list_project_tasks_empty(client: TestClient, db_session: Session) -> None:
    project = _seed_project(db_session)
    response = client.get(f"/api/projects/{project.id}/tasks")
    assert response.status_code == 200
    assert response.json() == []


def test_list_project_tasks_returns_seeded_tasks(client: TestClient, db_session: Session) -> None:
    project = _seed_project(db_session)
    template = _seed_template(db_session, project.id)
    dataset, _ = _seed_examples(db_session, project.id, count=3)

    other_project = _seed_project(db_session)
    other_template = _seed_template(db_session, other_project.id)
    other_dataset, _ = _seed_examples(db_session, other_project.id, count=1, hash_prefix="other")

    client.post(
        f"/api/projects/{project.id}/tasks/generate",
        json={
            "template_id": str(template.id),
            "dataset_id": str(dataset.id),
            "required_annotations": 2,
        },
    )
    client.post(
        f"/api/projects/{other_project.id}/tasks/generate",
        json={
            "template_id": str(other_template.id),
            "dataset_id": str(other_dataset.id),
            "required_annotations": 2,
        },
    )

    response = client.get(f"/api/projects/{project.id}/tasks")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 3
    assert {t["project_id"] for t in body} == {str(project.id)}
    timestamps = [t["created_at"] for t in body]
    assert timestamps == sorted(timestamps, reverse=True)


def test_list_project_tasks_includes_annotation_count(
    client: TestClient, db_session: Session
) -> None:
    project = _seed_project(db_session)
    template = _seed_template(db_session, project.id)
    dataset, examples = _seed_examples(db_session, project.id, count=3)

    client.post(
        f"/api/projects/{project.id}/tasks/generate",
        json={
            "template_id": str(template.id),
            "dataset_id": str(dataset.id),
            "required_annotations": 2,
        },
    )

    tasks = db_session.query(Task).filter(Task.project_id == project.id).all()
    assert len(tasks) == 3
    by_example = {t.example_id: t for t in tasks}

    user = User(email=f"a-{uuid.uuid4()}@x.com", name="A", role="annotator")
    db_session.add(user)
    db_session.flush()

    def _annotate(task_id: uuid.UUID, label: str) -> None:
        assignment = Assignment(task_id=task_id, annotator_id=user.id, status="submitted")
        db_session.add(assignment)
        db_session.flush()
        db_session.add(
            Annotation(
                task_id=task_id,
                assignment_id=assignment.id,
                annotator_id=user.id,
                label={"relevance": label},
            )
        )

    _annotate(by_example[examples[0].id].id, "relevant")
    _annotate(by_example[examples[1].id].id, "relevant")
    _annotate(by_example[examples[1].id].id, "not_relevant")
    db_session.commit()

    response = client.get(f"/api/projects/{project.id}/tasks")
    assert response.status_code == 200
    body = response.json()
    counts_by_task = {row["id"]: row["annotation_count"] for row in body}
    assert counts_by_task[str(by_example[examples[0].id].id)] == 1
    assert counts_by_task[str(by_example[examples[1].id].id)] == 2
    assert counts_by_task[str(by_example[examples[2].id].id)] == 0


def test_list_project_templates_returns_seeded(client: TestClient, db_session: Session) -> None:
    from datetime import datetime, timedelta, timezone

    project = _seed_project(db_session)
    older = _seed_template(db_session, project.id)
    older.name = "older"
    older.created_at = datetime.now(timezone.utc) - timedelta(seconds=10)
    db_session.commit()
    newer = TaskTemplate(
        project_id=project.id,
        name="newer",
        instructions="x",
        label_schema={"type": "categorical", "options": ["a"]},
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(newer)
    db_session.commit()
    db_session.refresh(newer)

    response = client.get(f"/api/projects/{project.id}/templates")
    assert response.status_code == 200
    body = response.json()
    assert [t["name"] for t in body] == ["newer", "older"]
    assert body[0]["id"] == str(newer.id)
    assert body[0]["project_id"] == str(project.id)
    assert body[0]["label_schema"] == {"type": "categorical", "options": ["a"]}
    assert body[1]["id"] == str(older.id)


def test_list_project_templates_empty(client: TestClient, db_session: Session) -> None:
    project = _seed_project(db_session)
    response = client.get(f"/api/projects/{project.id}/templates")
    assert response.status_code == 200
    assert response.json() == []


def test_list_project_templates_404_for_unknown_project(client: TestClient) -> None:
    response = client.get(f"/api/projects/{uuid.uuid4()}/templates")
    assert response.status_code == 404


def test_list_project_templates_does_not_leak_other_projects(
    client: TestClient, db_session: Session
) -> None:
    project = _seed_project(db_session)
    other = _seed_project(db_session)
    _seed_template(db_session, project.id)
    _seed_template(db_session, other.id)

    response = client.get(f"/api/projects/{project.id}/templates")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["project_id"] == str(project.id)


def test_generate_tasks_filters_by_dataset(client: TestClient, db_session: Session) -> None:
    project = _seed_project(db_session)
    template = _seed_template(db_session, project.id)
    dataset_a, examples_a = _seed_examples(db_session, project.id, count=3, hash_prefix="A")
    dataset_b, examples_b = _seed_examples(db_session, project.id, count=2, hash_prefix="B")

    response = client.post(
        f"/api/projects/{project.id}/tasks/generate",
        json={
            "template_id": str(template.id),
            "dataset_id": str(dataset_a.id),
            "required_annotations": 2,
        },
    )
    assert response.status_code == 202

    tasks = db_session.query(Task).filter(Task.project_id == project.id).all()
    assert len(tasks) == 3
    assert {t.example_id for t in tasks} == {ex.id for ex in examples_a}

    response = client.post(
        f"/api/projects/{project.id}/tasks/generate",
        json={
            "template_id": str(template.id),
            "dataset_id": str(dataset_b.id),
            "required_annotations": 2,
        },
    )
    assert response.status_code == 202

    tasks_after = db_session.query(Task).filter(Task.project_id == project.id).all()
    assert len(tasks_after) == 5
    assert {t.example_id for t in tasks_after} == {ex.id for ex in (*examples_a, *examples_b)}


def test_generate_tasks_rejects_foreign_dataset(client: TestClient, db_session: Session) -> None:
    project = _seed_project(db_session)
    template = _seed_template(db_session, project.id)
    _seed_examples(db_session, project.id, count=2)

    other = _seed_project(db_session)
    foreign_dataset, _ = _seed_examples(db_session, other.id, count=1, hash_prefix="foreign")

    response = client.post(
        f"/api/projects/{project.id}/tasks/generate",
        json={
            "template_id": str(template.id),
            "dataset_id": str(foreign_dataset.id),
            "required_annotations": 2,
        },
    )
    assert response.status_code == 400
    assert db_session.query(Task).filter(Task.project_id == project.id).count() == 0


def test_generate_tasks_rejects_unknown_dataset(client: TestClient, db_session: Session) -> None:
    project = _seed_project(db_session)
    template = _seed_template(db_session, project.id)
    _seed_examples(db_session, project.id, count=2)

    response = client.post(
        f"/api/projects/{project.id}/tasks/generate",
        json={
            "template_id": str(template.id),
            "dataset_id": str(uuid.uuid4()),
            "required_annotations": 2,
        },
    )
    assert response.status_code == 400


def test_list_project_tasks_status_filter(client: TestClient, db_session: Session) -> None:
    project = _seed_project(db_session)
    template = _seed_template(db_session, project.id)
    dataset, examples = _seed_examples(db_session, project.id, count=3)

    client.post(
        f"/api/projects/{project.id}/tasks/generate",
        json={
            "template_id": str(template.id),
            "dataset_id": str(dataset.id),
            "required_annotations": 2,
        },
    )

    one = db_session.query(Task).filter(Task.example_id == examples[0].id).one()
    one.status = "assigned"
    db_session.commit()

    created = client.get(f"/api/projects/{project.id}/tasks?status=created")
    assert created.status_code == 200
    assert len(created.json()) == 2
    assert all(t["status"] == "created" for t in created.json())

    assigned = client.get(f"/api/projects/{project.id}/tasks?status=assigned")
    assert assigned.status_code == 200
    assert len(assigned.json()) == 1
    assert assigned.json()[0]["status"] == "assigned"
