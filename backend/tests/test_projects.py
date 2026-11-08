"""Tests for the project endpoints (W-5)."""

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_start_project_gives_201_with_an_id() -> None:
    response = client.post("/projects", json={"request": "A bookshop where I can add books"})

    assert response.status_code == 201
    body = response.json()
    assert body["id"].startswith("p_")
    assert body["status"] == "waiting"
    assert body["questions"] == []

def test_get_project_shows_its_status() -> None:
    # First create a project, then ask for it by its id.
    start = client.post("/projects", json={"request": "A to-do list API"})
    project_id = start.json()["id"]

    response = client.get(f"/projects/{project_id}")

    assert response.status_code == 200
    assert response.json()["id"] == project_id
    assert response.json()["status"] == "waiting"


def test_get_unknown_project_gives_404() -> None:
    response = client.get("/projects/p_999")

    assert response.status_code == 404
    # The contract says errors are a plain-English sentence the UI can show.
    assert response.json()["detail"] == "Project not found."

def test_get_project_shows_its_status() -> None:
    # First create a project, then ask for it by its id.
    start = client.post("/projects", json={"request": "A to-do list API"})
    project_id = start.json()["id"]

    response = client.get(f"/projects/{project_id}")

    assert response.status_code == 200
    assert response.json()["id"] == project_id
    assert response.json()["status"] == "waiting"


def test_get_unknown_project_gives_404() -> None:
    response = client.get("/projects/p_999")

    assert response.status_code == 404
    # The contract says errors are a plain-English sentence the UI can show.
    assert response.json()["detail"] == "Project not found."