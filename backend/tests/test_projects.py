"""Tests for the project endpoints (W-5)."""

from fastapi.testclient import TestClient

from backend.main import app
from backend.projects import add_event

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

def test_events_stream_sends_the_history_and_ends() -> None:
    start = client.post("/projects", json={"request": "A to-do list API"})
    project_id = start.json()["id"]
    # Pretend to be the AI agent: say the build failed (a final status, so the stream ends).
    add_event(project_id, {"status": "failed"})

    response = client.get(f"/projects/{project_id}/events")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    # Each SSE message is a line starting with "data: ", followed by the JSON.
    assert 'data: {"status":"waiting"}' in response.text
    assert 'data: {"status":"failed"}' in response.text


def test_events_for_unknown_project_gives_404() -> None:
    response = client.get("/projects/p_999/events")

    assert response.status_code == 404


def test_request_of_only_spaces_is_refused() -> None:
    # "   " is 3 characters long, but it says nothing, so it counts as empty.
    response = client.post("/projects", json={"request": "   "})

    assert response.status_code == 422

def test_broken_json_gives_a_plain_sentence() -> None:
    # The closing } is missing, so this isn't valid JSON at all.
    broken = '{"request": "A bookshop"'
    response = client.post("/projects", content=broken, headers={"Content-Type": "application/json"})

    assert response.status_code == 422
    assert response.json()["detail"] == "The request body is not valid JSON."

def test_list_projects_shows_newest_first() -> None:
    first = client.post("/projects", json={"request": "A to-do list API"}).json()["id"]
    second = client.post("/projects", json={"request": "A bookshop API"}).json()["id"]

    response = client.get("/projects")

    assert response.status_code == 200
    listed = [project["id"] for project in response.json()]
    # The two we just made are the newest, so they come first, newest at the top.
    assert listed[:2] == [second, first]


def test_listed_project_has_the_contract_fields() -> None:
    client.post("/projects", json={"request": "A recipe book API"})

    newest = client.get("/projects").json()[0]

    assert set(newest) == {"id", "name", "status", "updated_at"}
    assert newest["name"] == "A recipe book API"  # until a plan gives it a real name

def test_long_request_gets_a_short_name_in_the_list() -> None:
    long_request = "A bookshop where I can add books, list them, change their prices and remove them"
    client.post("/projects", json={"request": long_request})

    newest = client.get("/projects").json()[0]

    # Cut at a word (no half-words), about 40 characters, with "…" to show it was cut.
    assert newest["name"] == "A bookshop where I can add books, list…"
    assert len(newest["name"]) <= 41  # 40 characters plus the "…"