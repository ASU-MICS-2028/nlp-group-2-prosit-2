"""The plain check before the AI (agent/scope.py, D-023) inside a real build job: refused at once, no AI request."""

import asyncio

import pytest
from fastapi.testclient import TestClient

from backend import projects
from backend.builder import BuildResult
from backend.main import app

client = TestClient(app)
real_run_build = projects.run_build


@pytest.fixture
def ai_calls(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    monkeypatch.setenv("LLM_MODEL", "fake-model")
    monkeypatch.setattr(projects, "run_build", lambda project_id, request: None)  # POST /projects starts nothing
    calls: list[str] = []

    async def pretend_ai(message, instruction, model, report, backup_model=None):
        calls.append(message)
        return BuildResult(status="failed", reason="pretend", files={}, kind="no_files")

    monkeypatch.setattr(projects, "build_with_retries", pretend_ai)
    return calls


def build(request: str) -> str:
    project_id = client.post("/projects", json={"request": request}).json()["id"]
    asyncio.run(real_run_build(project_id, request))
    return project_id


def test_a_school_website_is_refused_without_asking_the_ai(ai_calls):
    project_id = build("A school website where parents can see news and the term calendar.")

    assert ai_calls == []  # no AI request, so no quota used
    body = client.get(f"/projects/{project_id}").json()
    assert (body["status"], body["name"]) == ("failed", "School Website (not built)")
    last = projects.events[project_id][-1]
    assert last["step"]["phase"] == "finishing"
    assert "API" in last["step"]["text"]
    listed = {p["id"]: p for p in client.get("/projects").json()}
    assert listed[project_id]["name"] == "School Website (not built)"  # the sidebar shows "Not built" from this


def test_scraping_people_from_linkedin_is_refused_without_asking_the_ai(ai_calls):
    project_id = build("Scrape names and email addresses from LinkedIn.")

    assert ai_calls == []
    assert projects.projects[project_id]["name"] == "Personal Data Collector (not built)"


def test_an_ordinary_request_still_goes_to_the_ai(ai_calls):
    build("An API for my school website: students, classes and teachers.")

    assert len(ai_calls) == 1
