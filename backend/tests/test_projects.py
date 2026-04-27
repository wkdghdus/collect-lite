import uuid

from fastapi.testclient import TestClient



def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_projects_empty(client: TestClient) -> None:
    response = client.get("/api/projects")
    assert response.status_code == 200
    assert response.json() == []


def test_create_project(client: TestClient) -> None:
    response = client.post(
        "/api/projects",
        json={"name": "Test Project", "task_type": "classification"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Project"
    assert data["task_type"] == "classification"
    assert data["status"] == "draft"
    assert "id" in data


def test_list_projects_after_create(client: TestClient) -> None:
    client.post("/api/projects", json={"name": "P1", "task_type": "classification"})
    client.post("/api/projects", json={"name": "P2", "task_type": "relevance_rating"})
    response = client.get("/api/projects")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_project_not_found(client: TestClient) -> None:
    response = client.get(f"/api/projects/{uuid.uuid4()}")
    assert response.status_code == 404
