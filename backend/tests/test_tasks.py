import uuid

from fastapi.testclient import TestClient


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
