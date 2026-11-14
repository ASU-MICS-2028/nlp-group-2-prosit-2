"""Tests for the project endpoints (W-5)."""

import asyncio

import pytest
from fastapi.testclient import TestClient

from backend import projects
from backend.main import app
from backend.projects import add_event

client = TestClient(app)

# Keep the real build job before the fixture below swaps it, so we can still test it directly.
real_run_build = projects.run_build

# Every build our fake was asked to start, as (project id, request text).
started: list[tuple[str, str]] = []


def fake_run_build(project_id: str, request: str) -> None:
    started.append((project_id, request))  # only note the call: no AI, no cost, instant


# autouse=True: every test in this file uses this automatically, without asking for it.
# Starting a project must never call the real AI in tests (slow, costs free-tier quota),
# so we swap the build job for the fake above. monkeypatch puts the real one back after each test.
@pytest.fixture(autouse=True)
def no_real_builds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(projects, "run_build", fake_run_build)


def test_start_project_starts_its_build() -> None:
    start = client.post("/projects", json={"request": "A notes API"})

    # TestClient waits for background jobs to finish, so the fake has already been called.
    assert started[-1] == (start.json()["id"], "A notes API")


def new_project_id() -> str:
    # A project to build into. Its own build is the fake above, so nothing else happens to it.
    return client.post("/projects", json={"request": "A notes API"}).json()["id"]


def test_build_reports_go_into_the_projects_diary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_MODEL", "fake-model")
    asked: list[str] = []

    # A pretend retry loop: notes the AI's first message and reports one final step, like the real one.
    async def fake_build(message, instruction, model, report):
        asked.append(message)
        report({"status": "ready", "attempt": 1, "max_attempts": 3})

    monkeypatch.setattr(projects, "build_with_retries", fake_build)
    project_id = new_project_id()

    asyncio.run(real_run_build(project_id, "A notes API"))

    assert "A notes API" in asked[0]  # the AI got the person's request
    assert projects.events[project_id][-1] == {"status": "ready", "attempt": 1, "max_attempts": 3}
    assert projects.projects[project_id]["status"] == "ready"


def test_build_without_a_model_fails_with_a_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_MODEL", "")
    project_id = new_project_id()

    asyncio.run(real_run_build(project_id, "A notes API"))

    last = projects.events[project_id][-1]
    assert last["status"] == "failed"
    assert "LLM_MODEL" in last["step"]["text"]


def test_unexpected_crash_still_ends_the_build(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_MODEL", "fake-model")

    async def crashing_build(message, instruction, model, report):
        raise ValueError("no API key")  # an error the builder doesn't catch itself

    monkeypatch.setattr(projects, "build_with_retries", crashing_build)
    project_id = new_project_id()

    asyncio.run(real_run_build(project_id, "A notes API"))

    # A final status, so the live stream ends instead of spinning forever.
    assert projects.projects[project_id]["status"] == "failed"


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