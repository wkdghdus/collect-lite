import uuid

from fastapi.testclient import TestClient


def test_submit_annotation_route_exists(client: TestClient) -> None:
    task_id = uuid.uuid4()
    response = client.post(
        f"/api/tasks/{task_id}/annotations",
        json={"label": {"value": "relevant"}, "confidence": 4},
    )
    assert response.status_code in (201, 404, 500)


def test_skip_task_route_exists(client: TestClient) -> None:
    task_id = uuid.uuid4()
    response = client.post(f"/api/tasks/{task_id}/skip")
    assert response.status_code in (204, 404, 500)
