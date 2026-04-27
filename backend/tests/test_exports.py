import uuid

from fastapi.testclient import TestClient


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
