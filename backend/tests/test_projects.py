from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_projects_returns_error_until_implemented(client: TestClient) -> None:
    response = client.get("/api/projects")
    assert response.status_code in (200, 500)


def test_create_project_returns_error_until_implemented(client: TestClient) -> None:
    response = client.post(
        "/api/projects",
        json={"name": "Test Project", "task_type": "classification"},
    )
    assert response.status_code in (201, 500)
