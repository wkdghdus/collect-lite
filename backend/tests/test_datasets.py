import io
import json
import uuid

import pytest
from fastapi.testclient import TestClient

from app.models.dataset import SourceExample


def _jsonl(rows: list[dict]) -> bytes:
    return ("\n".join(json.dumps(row) for row in rows) + "\n").encode()


def _upload(client: TestClient, project_id: str, filename: str, content: bytes):
    return client.post(
        f"/api/projects/{project_id}/datasets",
        files={"file": (filename, io.BytesIO(content), "application/octet-stream")},
    )


@pytest.fixture
def project_id(client: TestClient) -> str:
    response = client.post(
        "/api/projects",
        json={"name": "DS Test", "task_type": "relevance_rating"},
    )
    return response.json()["id"]


def test_upload_jsonl_pointwise(client: TestClient, project_id: str) -> None:
    rows = [
        {"query": "q1", "candidate_document": "c1", "document_id": "d1"},
        {"query": "q2", "candidate_document": "c2"},
    ]
    response = _upload(client, project_id, "test.jsonl", _jsonl(rows))
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["row_count"] == 2
    assert data["status"] == "uploaded"
    assert data["inserted_count"] == 2
    assert data["skipped_duplicate_count"] == 0
    assert data["existing_duplicate_count"] == 0
    assert data["total_input_rows"] == 2
    assert data["total_normalized_examples"] == 2
    assert data["filename"] == "test.jsonl"


def test_upload_csv_pointwise(client: TestClient, project_id: str) -> None:
    csv = b"query,candidate_document,document_id\nq1,c1,d1\nq2,c2,d2\n"
    response = _upload(client, project_id, "test.csv", csv)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["row_count"] == 2
    assert data["inserted_count"] == 2


def test_upload_creates_source_examples(client: TestClient, project_id: str, db_session) -> None:
    rows = [{"query": "q", "candidate_document": "c", "document_id": "d-99"}]
    response = _upload(client, project_id, "test.jsonl", _jsonl(rows))
    assert response.status_code == 201
    dataset_id = uuid.UUID(response.json()["id"])
    examples = db_session.query(SourceExample).filter(SourceExample.dataset_id == dataset_id).all()
    assert len(examples) == 1
    example = examples[0]
    assert example.external_id == "d-99"
    assert example.payload["query"] == "q"
    assert example.payload["candidate_document"] == "c"
    assert example.payload["document_id"] == "d-99"


def test_upload_pointwise_generates_document_id_when_absent(
    client: TestClient, project_id: str, db_session
) -> None:
    rows = [{"query": "q", "candidate_document": "c"}]
    response = _upload(client, project_id, "test.jsonl", _jsonl(rows))
    assert response.status_code == 201
    dataset_id = uuid.UUID(response.json()["id"])
    example = db_session.query(SourceExample).filter(SourceExample.dataset_id == dataset_id).one()
    assert example.external_id == "row_0"
    assert example.payload["document_id"] == "row_0"


def test_upload_pairwise_expands_to_two_pointwise(
    client: TestClient, project_id: str, db_session
) -> None:
    rows = [
        {
            "query": "q",
            "candidate_a": "A",
            "candidate_b": "B",
            "metadata": {"id": "p1"},
        }
    ]
    response = _upload(client, project_id, "pair.jsonl", _jsonl(rows))
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["total_input_rows"] == 1
    assert data["total_normalized_examples"] == 2
    assert data["inserted_count"] == 2
    assert data["row_count"] == 2
    dataset_id = uuid.UUID(data["id"])
    examples = (
        db_session.query(SourceExample)
        .filter(SourceExample.dataset_id == dataset_id)
        .order_by(SourceExample.external_id)
        .all()
    )
    assert [e.external_id for e in examples] == ["row_0_a", "row_0_b"]
    assert {e.payload["candidate_document"] for e in examples} == {"A", "B"}
    for example in examples:
        assert example.payload["metadata"] == {"id": "p1"}


def test_upload_validates_pointwise_missing_query(client: TestClient, project_id: str) -> None:
    rows = [{"candidate_document": "c"}]
    response = _upload(client, project_id, "bad.jsonl", _jsonl(rows))
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["errors"][0]["row"] == 0
    assert "query" in detail["errors"][0]["missing"]


def test_upload_validates_empty_string_treated_as_missing(
    client: TestClient, project_id: str
) -> None:
    rows = [{"query": "   ", "candidate_document": "c"}]
    response = _upload(client, project_id, "bad.jsonl", _jsonl(rows))
    assert response.status_code == 400


def test_upload_validates_pairwise_missing_candidate_b(client: TestClient, project_id: str) -> None:
    rows = [{"query": "q", "candidate_a": "A", "candidate_b": ""}]
    response = _upload(client, project_id, "bad.jsonl", _jsonl(rows))
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "candidate_b" in detail["errors"][0]["missing"]


def test_upload_atomic_on_validation_failure(
    client: TestClient, project_id: str, db_session
) -> None:
    rows = [{"candidate_document": "c"}]
    _upload(client, project_id, "bad.jsonl", _jsonl(rows))
    list_response = client.get(f"/api/projects/{project_id}/datasets")
    assert list_response.json() == []
    assert db_session.query(SourceExample).count() == 0


def test_upload_unsupported_extension(client: TestClient, project_id: str) -> None:
    response = _upload(client, project_id, "x.txt", b"hello")
    assert response.status_code == 400


def test_upload_unknown_project(client: TestClient) -> None:
    response = _upload(
        client,
        str(uuid.uuid4()),
        "x.jsonl",
        _jsonl([{"query": "q", "candidate_document": "c"}]),
    )
    assert response.status_code == 404


def test_upload_skips_within_file_duplicates(client: TestClient, project_id: str) -> None:
    rows = [
        {"query": "q", "candidate_document": "c", "document_id": "same"},
        {"query": "q", "candidate_document": "c", "document_id": "same"},
    ]
    response = _upload(client, project_id, "dup.jsonl", _jsonl(rows))
    assert response.status_code == 201
    data = response.json()
    assert data["inserted_count"] == 1
    assert data["skipped_duplicate_count"] == 1
    assert data["existing_duplicate_count"] == 0
    assert data["row_count"] == 1


def test_upload_skips_existing_project_duplicates(client: TestClient, project_id: str) -> None:
    rows = [{"query": "q", "candidate_document": "c", "document_id": "same"}]
    first = _upload(client, project_id, "first.jsonl", _jsonl(rows))
    assert first.status_code == 201
    second = _upload(client, project_id, "second.jsonl", _jsonl(rows))
    assert second.status_code == 201
    data = second.json()
    assert data["inserted_count"] == 0
    assert data["existing_duplicate_count"] == 1
    assert data["row_count"] == 0


def test_list_datasets_after_upload(client: TestClient, project_id: str) -> None:
    _upload(
        client,
        project_id,
        "test.jsonl",
        _jsonl([{"query": "q", "candidate_document": "c"}]),
    )
    response = client.get(f"/api/projects/{project_id}/datasets")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1


def test_list_datasets_unknown_project(client: TestClient) -> None:
    response = client.get(f"/api/projects/{uuid.uuid4()}/datasets")
    assert response.status_code == 404


def test_upload_malformed_jsonl(client: TestClient, project_id: str) -> None:
    response = _upload(client, project_id, "bad.jsonl", b"{not json\n")
    assert response.status_code == 400
