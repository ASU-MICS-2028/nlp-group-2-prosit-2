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

def test_empty_request_is_refused() -> None:
    response = client.post("/projects", json={"request": ""})

    # 422 means "I understood you, but this data isn't allowed".
    assert response.status_code == 422


def test_too_long_request_is_refused() -> None:
    too_long = "a" * 2001  # one character over the limit
    response = client.post("/projects", json={"request": too_long})

    assert response.status_code == 422

def test_bad_input_error_is_a_plain_sentence() -> None:
    response = client.post("/projects", json={"request": ""})

    # The contract says every error is {"detail": "a plain sentence"},
    # so Perfect's page can show it to the user without any extra work.
    detail = response.json()["detail"]
    assert isinstance(detail, str)  # a sentence, not a list
    assert "request" in detail  # it says which field was wrong

