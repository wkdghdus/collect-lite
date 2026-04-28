"""Tests for the export pipeline (POST + list + status + download)."""

import csv
import io
import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    Annotation,
    ConsensusResult,
    Dataset,
    Export,
    ModelSuggestion,
    Project,
    ReviewDecision,
    SourceExample,
    Task,
    TaskTemplate,
    User,
)
from app.models.task import Assignment


def _project(db: Session, name: str = "P") -> Project:
    project = Project(name=name, task_type="rag_relevance")
    db.add(project)
    db.flush()
    return project


def _seed_resolved_task(
    db: Session,
    *,
    project: Project,
    payload: dict | None = None,
    consensus_status: str = "auto_resolved",
    final_label: str = "relevant",
    suggestion_label: str | None = "relevant",
    suggestion_score: float | None = 0.91,
    agreement_score: float = 1.0,
    with_review: bool = False,
    task_status: str = "resolved",
) -> Task:
    payload = (
        payload
        if payload is not None
        else {
            "query": "neural networks",
            "candidate_document": "neural networks are great",
            "document_id": "row_0",
            "extra": "kept-in-metadata",
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
        status=task_status,
    )
    db.add(task)
    db.flush()
    consensus = ConsensusResult(
        task_id=task.id,
        final_label={"relevance": final_label},
        agreement_score=agreement_score,
        method="majority_vote",
        num_annotations=2,
        status=consensus_status,
    )
    db.add(consensus)
    if suggestion_label is not None:
        suggestion = ModelSuggestion(
            task_id=task.id,
            provider="cohere",
            model_name="rerank-english-v3.0",
            suggestion={"relevance": suggestion_label},
            confidence=suggestion_score,
        )
        db.add(suggestion)
    if with_review:
        reviewer = User(
            email=f"reviewer-{uuid.uuid4()}@example.com",
            name="R",
            role="reviewer",
        )
        db.add(reviewer)
        db.flush()
        decision = ReviewDecision(
            task_id=task.id,
            reviewer_id=reviewer.id,
            final_label={"relevance": final_label},
        )
        db.add(decision)
    db.commit()
    db.refresh(task)
    return task


def _seed_pre_review_task(
    db: Session,
    *,
    project: Project,
    status: str,
) -> Task:
    dataset = Dataset(project_id=project.id, filename="d.jsonl", row_count=1)
    db.add(dataset)
    db.flush()
    example = SourceExample(
        dataset_id=dataset.id,
        project_id=project.id,
        source_hash=f"h-{uuid.uuid4()}",
        payload={"query": "q", "candidate_document": "d", "document_id": "x"},
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
    if status in ("submitted", "needs_review"):
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
            label={"relevance": "relevant"},
        )
        db.add(annotation)
    db.commit()
    db.refresh(task)
    return task


@pytest.fixture
def isolated_exports_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "exports_dir", str(tmp_path))
    return tmp_path


def test_create_export_route_exists(client: TestClient) -> None:
    project_id = uuid.uuid4()
    response = client.post(
        f"/api/projects/{project_id}/exports",
        json={"format": "jsonl"},
    )
    assert response.status_code in (202, 404, 500)


def test_get_export_route_exists(client: TestClient) -> None:
    export_id = uuid.uuid4()
    response = client.get(f"/api/exports/{export_id}")
    assert response.status_code in (200, 404, 500)


def test_post_jsonl_creates_file_and_marks_tasks_exported(
    client: TestClient,
    db_session: Session,
    isolated_exports_dir,
) -> None:
    project = _project(db_session)
    task1 = _seed_resolved_task(db_session, project=project)
    task2 = _seed_resolved_task(
        db_session,
        project=project,
        payload={
            "query": "deep learning",
            "candidate_document": "transformers",
            "document_id": "row_1",
            "split": "train",
        },
        final_label="not_relevant",
        suggestion_label="not_relevant",
        suggestion_score=0.42,
        agreement_score=0.5,
    )
    skipped = _seed_pre_review_task(db_session, project=project, status="needs_review")

    response = client.post(
        f"/api/projects/{project.id}/exports",
        json={"format": "jsonl"},
    )
    assert response.status_code == 202
    body = response.json()
    export_id = uuid.UUID(body["id"])

    db_session.expire_all()
    export = db_session.get(Export, export_id)
    assert export.status == "completed"
    assert export.format == "jsonl"
    assert export.row_count == 2

    file_path = isolated_exports_dir / f"{export_id}.jsonl"
    assert file_path.exists()
    assert export.file_path == str(file_path.resolve())

    lines = [line for line in file_path.read_text().splitlines() if line]
    assert len(lines) == 2
    rows = [json.loads(line) for line in lines]
    expected_keys = {
        "query",
        "candidate_document",
        "document_id",
        "final_label",
        "label_source",
        "model_suggestion",
        "model_score",
        "human_agreement",
        "metadata",
    }
    for row in rows:
        assert set(row.keys()) == expected_keys
        assert row["label_source"] == "consensus"
    by_id = {r["document_id"]: r for r in rows}
    assert by_id["row_0"]["final_label"] == "relevant"
    assert by_id["row_0"]["metadata"] == {"extra": "kept-in-metadata"}
    assert by_id["row_1"]["final_label"] == "not_relevant"
    assert by_id["row_1"]["metadata"] == {"split": "train"}
    assert by_id["row_1"]["model_score"] == pytest.approx(0.42)
    assert by_id["row_1"]["human_agreement"] == pytest.approx(0.5)

    assert db_session.get(Task, task1.id).status == "exported"
    assert db_session.get(Task, task2.id).status == "exported"
    assert db_session.get(Task, skipped.id).status == "needs_review"


def test_post_csv_creates_file_with_header_and_rows(
    client: TestClient,
    db_session: Session,
    isolated_exports_dir,
) -> None:
    project = _project(db_session)
    _seed_resolved_task(db_session, project=project)
    _seed_resolved_task(
        db_session,
        project=project,
        payload={
            "query": "deep learning",
            "candidate_document": "transformers",
            "document_id": "row_1",
            "split": "train",
        },
    )

    response = client.post(
        f"/api/projects/{project.id}/exports",
        json={"format": "csv"},
    )
    assert response.status_code == 202
    export_id = uuid.UUID(response.json()["id"])

    db_session.expire_all()
    export = db_session.get(Export, export_id)
    assert export.status == "completed"
    assert export.format == "csv"
    assert export.row_count == 2

    file_path = isolated_exports_dir / f"{export_id}.csv"
    assert file_path.exists()

    content = file_path.read_text()
    reader = csv.reader(io.StringIO(content))
    header = next(reader)
    assert header == [
        "query",
        "candidate_document",
        "document_id",
        "final_label",
        "label_source",
        "model_suggestion",
        "model_score",
        "human_agreement",
        "metadata",
    ]
    data_rows = list(reader)
    assert len(data_rows) == 2
    metadata_index = header.index("metadata")
    decoded = [json.loads(row[metadata_index]) for row in data_rows]
    assert {"extra": "kept-in-metadata"} in decoded
    assert {"split": "train"} in decoded


def test_post_export_with_no_eligible_tasks_succeeds_empty(
    client: TestClient,
    db_session: Session,
    isolated_exports_dir,
) -> None:
    project = _project(db_session)
    statuses = ["created", "suggested", "assigned", "submitted", "needs_review"]
    pre_tasks = [_seed_pre_review_task(db_session, project=project, status=s) for s in statuses]

    response = client.post(
        f"/api/projects/{project.id}/exports",
        json={"format": "jsonl"},
    )
    assert response.status_code == 202
    export_id = uuid.UUID(response.json()["id"])

    db_session.expire_all()
    export = db_session.get(Export, export_id)
    assert export.status == "completed"
    assert export.row_count == 0

    file_path = isolated_exports_dir / f"{export_id}.jsonl"
    assert file_path.exists()
    assert file_path.stat().st_size == 0

    for task, status in zip(pre_tasks, statuses):
        assert db_session.get(Task, task.id).status == status


def test_already_exported_tasks_are_not_re_exported(
    client: TestClient,
    db_session: Session,
    isolated_exports_dir,
) -> None:
    project = _project(db_session)
    _seed_resolved_task(db_session, project=project)
    _seed_resolved_task(
        db_session,
        project=project,
        payload={
            "query": "q2",
            "candidate_document": "d2",
            "document_id": "row_1",
        },
    )

    first = client.post(
        f"/api/projects/{project.id}/exports",
        json={"format": "jsonl"},
    )
    assert first.status_code == 202
    db_session.expire_all()
    first_export = db_session.get(Export, uuid.UUID(first.json()["id"]))
    assert first_export.row_count == 2

    second = client.post(
        f"/api/projects/{project.id}/exports",
        json={"format": "jsonl"},
    )
    assert second.status_code == 202
    db_session.expire_all()
    second_export = db_session.get(Export, uuid.UUID(second.json()["id"]))
    assert second_export.row_count == 0

    exported_count = (
        db_session.query(Task)
        .filter(Task.project_id == project.id, Task.status == "exported")
        .count()
    )
    assert exported_count == 2


def test_download_returns_file_contents_with_correct_content_type(
    client: TestClient,
    db_session: Session,
    isolated_exports_dir,
) -> None:
    project = _project(db_session)
    _seed_resolved_task(db_session, project=project)

    create = client.post(
        f"/api/projects/{project.id}/exports",
        json={"format": "jsonl"},
    )
    export_id = uuid.UUID(create.json()["id"])

    db_session.expire_all()
    file_path = isolated_exports_dir / f"{export_id}.jsonl"
    expected_body = file_path.read_text()

    response = client.get(f"/api/exports/{export_id}/download")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/x-ndjson")
    assert response.text == expected_body


def test_download_404_unknown_id(client: TestClient) -> None:
    response = client.get(f"/api/exports/{uuid.uuid4()}/download")
    assert response.status_code == 404
    assert response.json() == {"detail": "Export not found"}


def test_download_409_when_not_completed(client: TestClient, db_session: Session) -> None:
    project = _project(db_session)
    export = Export(project_id=project.id, format="jsonl", status="queued")
    db_session.add(export)
    db_session.commit()
    db_session.refresh(export)

    response = client.get(f"/api/exports/{export.id}/download")
    assert response.status_code == 409
    assert response.json() == {"detail": "Export not completed"}


def test_list_exports_newest_first(client: TestClient, db_session: Session) -> None:
    project = _project(db_session)
    older = Export(
        project_id=project.id,
        format="jsonl",
        status="completed",
        row_count=0,
    )
    newer = Export(
        project_id=project.id,
        format="csv",
        status="completed",
        row_count=0,
    )
    db_session.add_all([older, newer])
    db_session.commit()
    older.created_at = datetime.now(timezone.utc) - timedelta(hours=2)
    newer.created_at = datetime.now(timezone.utc)
    db_session.commit()

    response = client.get(f"/api/projects/{project.id}/exports")
    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body] == [str(newer.id), str(older.id)]
    assert all("row_count" in item for item in body)


def test_list_exports_unknown_project_404(client: TestClient) -> None:
    response = client.get(f"/api/projects/{uuid.uuid4()}/exports")
    assert response.status_code == 404
    assert response.json() == {"detail": "Project not found"}


def test_label_source_reflects_review_decision(
    client: TestClient,
    db_session: Session,
    isolated_exports_dir,
) -> None:
    project = _project(db_session)
    _seed_resolved_task(
        db_session,
        project=project,
        payload={
            "query": "q-review",
            "candidate_document": "d-review",
            "document_id": "row_review",
        },
        consensus_status="review_resolved",
        with_review=True,
    )
    _seed_resolved_task(
        db_session,
        project=project,
        payload={
            "query": "q-auto",
            "candidate_document": "d-auto",
            "document_id": "row_auto",
        },
        consensus_status="auto_resolved",
        with_review=False,
    )

    response = client.post(
        f"/api/projects/{project.id}/exports",
        json={"format": "jsonl"},
    )
    export_id = uuid.UUID(response.json()["id"])
    db_session.expire_all()

    file_path = isolated_exports_dir / f"{export_id}.jsonl"
    rows = [json.loads(line) for line in file_path.read_text().splitlines() if line]
    sources = {row["document_id"]: row["label_source"] for row in rows}
    assert sources["row_review"] == "review"
    assert sources["row_auto"] == "consensus"


def test_post_unknown_project_404(client: TestClient) -> None:
    response = client.post(
        f"/api/projects/{uuid.uuid4()}/exports",
        json={"format": "jsonl"},
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Project not found"}


def test_post_invalid_format_422(client: TestClient, db_session: Session) -> None:
    project = _project(db_session)
    response = client.post(
        f"/api/projects/{project.id}/exports",
        json={"format": "parquet"},
    )
    assert response.status_code == 422
    assert db_session.query(Export).count() == 0
