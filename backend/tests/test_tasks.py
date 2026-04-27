import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.dataset import Dataset, SourceExample
from app.models.project import Project
from app.models.task import Task, TaskTemplate


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
    dataset = Dataset(project_id=project_id, filename="seed.jsonl", row_count=count)
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
    return examples


def test_get_next_task_route_exists(client: TestClient) -> None:
    response = client.get("/api/tasks/next")
    assert response.status_code in (200, 500)


def test_generate_tasks_route_exists(client: TestClient) -> None:
    project_id = uuid.uuid4()
    template_id = uuid.uuid4()
    response = client.post(
        f"/api/projects/{project_id}/tasks/generate",
        json={"template_id": str(template_id), "required_annotations": 2},
    )
    assert response.status_code in (202, 404, 500)


def test_generate_tasks_creates_one_task_per_example(
    client: TestClient, db_session: Session
) -> None:
    project = _seed_project(db_session)
    template = _seed_template(db_session, project.id)
    examples = _seed_examples(db_session, project.id, count=3)
    seeded_example_ids = {ex.id for ex in examples}

    response = client.post(
        f"/api/projects/{project.id}/tasks/generate",
        json={"template_id": str(template.id), "required_annotations": 2},
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
    _seed_examples(db_session, project.id, count=4)

    payload = {"template_id": str(template.id), "required_annotations": 2}
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
    _seed_examples(db_session, project.id, count=3, hash_prefix="batch1")

    payload = {"template_id": str(template.id), "required_annotations": 2}
    client.post(f"/api/projects/{project.id}/tasks/generate", json=payload)
    new_examples = _seed_examples(db_session, project.id, count=2, hash_prefix="batch2")
    client.post(f"/api/projects/{project.id}/tasks/generate", json=payload)

    tasks = db_session.query(Task).filter(Task.project_id == project.id).all()
    assert len(tasks) == 5
    new_example_ids = {ex.id for ex in new_examples}
    new_task_example_ids = {t.example_id for t in tasks if t.example_id in new_example_ids}
    assert new_task_example_ids == new_example_ids


def test_generate_tasks_404_for_unknown_project(client: TestClient) -> None:
    response = client.post(
        f"/api/projects/{uuid.uuid4()}/tasks/generate",
        json={"template_id": str(uuid.uuid4()), "required_annotations": 2},
    )
    assert response.status_code == 404


def test_generate_tasks_400_for_wrong_task_type(client: TestClient, db_session: Session) -> None:
    project = _seed_project(db_session, task_type="other")
    template = _seed_template(db_session, project.id)

    response = client.post(
        f"/api/projects/{project.id}/tasks/generate",
        json={"template_id": str(template.id), "required_annotations": 2},
    )

    assert response.status_code == 400
