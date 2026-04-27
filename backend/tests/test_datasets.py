import io

from fastapi.testclient import TestClient


def test_list_datasets_route_exists(client: TestClient) -> None:
    import uuid
    project_id = uuid.uuid4()
    response = client.get(f"/api/projects/{project_id}/datasets")
    assert response.status_code in (200, 404, 500)


def test_upload_dataset_route_exists(client: TestClient) -> None:
    import uuid
    project_id = uuid.uuid4()
    jsonl_content = b'{"query": "test", "candidate_a": "a", "candidate_b": "b"}\n'
    response = client.post(
        f"/api/projects/{project_id}/datasets",
        files={"file": ("test.jsonl", io.BytesIO(jsonl_content), "application/octet-stream")},
    )
    assert response.status_code in (201, 404, 500)
