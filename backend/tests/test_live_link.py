"""Tests for the live link (F-13, D-011): /apis/{id}/... reaches the project's own running API.

These start real servers through backend/live.py, so they take a few seconds. No AI is used."""

import asyncio

import pytest
from fastapi.testclient import TestClient

from agent import prompts
from agent.tests.test_prompts import example_files  # the builder prompt's example: a Notes API
from backend import live, projects
from backend.builder import BuildResult
from backend.main import app

client = TestClient(app)
NOTES = example_files(prompts.load_prompt("builder"))
BROKEN = {"app/__init__.py": "", "app/main.py": "this is not python\n"}
real_run_build = projects.run_build


@pytest.fixture(autouse=True)
def no_real_builds_and_no_servers_left(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(projects, "run_build", lambda project_id, request: None)  # never call the AI
    yield
    live.stop_all()


def project_with(status: str, files: dict[str, str] | None) -> str:
    project_id = client.post("/projects", json={"request": "A notes API"}).json()["id"]
    projects.projects[project_id]["status"] = status
    if files is not None:
        projects.results[project_id] = BuildResult(status=status, reason="", files=files)
    return project_id


def awake_project() -> str:
    project_id = project_with("ready", NOTES)
    assert client.post(f"/projects/{project_id}/wake").status_code == 202
    return project_id


def test_a_finished_build_starts_its_live_api(monkeypatch):
    # D-011: "after the tests pass, the backend starts the generated project".
    monkeypatch.setenv("LLM_MODEL", "fake-model")

    async def fake_build(message, instruction, model, report, backup_model=None):
        return BuildResult(status="ready", reason="All tests pass.", files=NOTES, test_output="4 passed")

    monkeypatch.setattr(projects, "build_with_retries", fake_build)
    project_id = project_with("working", None)
    projects.projects[project_id]["status"] = "ready"  # build_with_retries' events set this in real life

    asyncio.run(real_run_build(project_id, "A notes API"))

    body = client.get(f"/projects/{project_id}").json()
    assert (body["api_url"], body["live_status"]) == (f"/apis/{project_id}", "running")
    # It was started under its link, so its Swagger page loads its own schema through us.
    assert f"/apis/{project_id}/openapi.json" in client.get(f"/apis/{project_id}/docs").text


def test_calls_go_through_to_the_live_api_and_its_data_lasts():
    project_id = awake_project()

    added = client.post(f"/apis/{project_id}/notes", json={"title": "Buy bread"})
    listed = client.get(f"/apis/{project_id}/notes")

    assert added.status_code == 201
    assert [note["title"] for note in listed.json()] == ["Buy bread"]


def test_the_live_apis_own_errors_come_back_unchanged():
    project_id = awake_project()

    response = client.get(f"/apis/{project_id}/notes/999")

    assert response.status_code == 404  # the Notes API's own "not found", not ours
    assert "999" in response.text or "not" in response.text.lower()


def test_its_swagger_page_works_behind_our_link():
    # PLAN's "done when": /apis/{id}/docs opens and "Try it out" works through our backend.
    project_id = awake_project()

    page = client.get(f"/apis/{project_id}/docs")
    schema = client.get(f"/apis/{project_id}/openapi.json").json()

    assert page.status_code == 200
    assert f"/apis/{project_id}/openapi.json" in page.text  # the page loads ITS schema, not ours
    assert schema["info"]["title"] == "Notes API"
    assert schema["servers"] == [{"url": f"/apis/{project_id}"}]  # so "Try it out" calls go through our link


def test_opening_a_sleeping_api_wakes_it_by_itself():
    # Seen live on Render: a page showed the link of an API that had gone to sleep, and the person got
    # "This API is asleep" instead of the Swagger page. Opening the link now starts it first.
    project_id = project_with("ready", NOTES)  # ready, but asleep (never started)
    assert client.get(f"/projects/{project_id}").json()["live_status"] == "sleeping"

    page = client.get(f"/apis/{project_id}/docs")

    assert page.status_code == 200
    assert f"/apis/{project_id}/openapi.json" in page.text
    assert client.get(f"/projects/{project_id}").json()["live_status"] == "running"


def test_a_sleeping_api_that_cannot_start_says_why_plainly():
    project_id = project_with("ready", BROKEN)

    response = client.get(f"/apis/{project_id}/docs")

    assert response.status_code == 503
    assert response.json() == {"detail": "The API could not start. Its code has a problem."}


def test_wake_starts_a_sleeping_api_and_does_nothing_new_when_it_runs():
    project_id = project_with("ready", NOTES)

    first = client.post(f"/projects/{project_id}/wake")
    pid = live.running[project_id].process.pid
    again = client.post(f"/projects/{project_id}/wake")

    assert (first.status_code, first.json()) == (202, {"live_status": "running"})
    assert again.status_code == 202
    assert live.running[project_id].process.pid == pid  # the same server, not a second one


def test_wake_on_a_project_that_cannot_start_is_a_plain_503():
    project_id = project_with("ready", BROKEN)

    response = client.post(f"/projects/{project_id}/wake")

    assert response.status_code == 503
    assert response.json() == {"detail": "The API could not start. Its code has a problem."}


def test_a_project_that_is_not_ready_has_no_live_api():
    project_id = project_with("working", None)

    body = client.get(f"/projects/{project_id}").json()

    assert (body["api_url"], body["live_status"]) == (None, None)
    assert client.post(f"/projects/{project_id}/wake").status_code == 409
    assert client.get(f"/apis/{project_id}/notes").status_code == 409


def test_unknown_projects_are_404():
    assert client.post("/projects/p_nope/wake").status_code == 404
    assert client.get("/apis/p_nope/docs").status_code == 404


def test_a_request_that_is_too_big_is_refused():
    project_id = awake_project()

    response = client.post(f"/apis/{project_id}/notes", content=b"x" * (projects.MAX_PASS_THROUGH_BYTES + 1))

    assert response.status_code == 413
    assert response.json() == {"detail": "The request is too big."}


def test_stopping_our_server_stops_every_live_api():
    # Without this, a restart (or every --reload on a laptop) would leave live APIs running on their own.
    with TestClient(app) as running_server:  # "with" runs the server's start-up and shut-down steps
        project_id = project_with("ready", NOTES)
        running_server.post(f"/projects/{project_id}/wake")
        process = live.running[project_id].process

    assert live.running == {}
    assert process.poll() is not None  # the live API's process has ended
