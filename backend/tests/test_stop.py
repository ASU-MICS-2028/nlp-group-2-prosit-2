"""Tests for stopping a running build (F-18): POST /projects/{id}/stop.

A pretend builder stands in for the AI, so no AI service is called. The build and the Stop run on the same
event loop (asyncio.run), as they do on the real server."""

import asyncio

import pytest
from fastapi.testclient import TestClient

from backend import live, projects
from backend.builder import BuildResult
from backend.main import app

client = TestClient(app)
real_run_build = projects.run_build
THINKING = {"status": "working", "step": {"kind": "Thinking", "text": "Building a Notes API.", "state": "done"}}


@pytest.fixture(autouse=True)
def pretend_builds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_MODEL", "fake-model")
    monkeypatch.setattr(projects, "run_build", lambda project_id, request: None)  # POST /projects starts nothing


def new_project() -> str:
    return client.post("/projects", json={"request": "A notes API"}).json()["id"]


def slow_build(started: asyncio.Event):
    # A build that writes one step, then "thinks" for a long time, like waiting for the AI.
    async def build(message, instruction, model, report, backup_model=None):
        report(THINKING)
        started.set()
        await asyncio.sleep(60)
        return BuildResult(status="ready", reason="All tests pass.", files={"app/main.py": ""})

    return build


async def stop(project_id: str) -> dict[str, str]:
    # Call the endpoint's function on this event loop, as the server would.
    return await projects.stop_project(projects.projects[project_id])


def last_event(project_id: str) -> dict[str, object]:
    return projects.events[project_id][-1]


def test_stop_ends_a_running_build_as_stopped(monkeypatch):
    project_id = new_project()

    async def scenario():
        started = asyncio.Event()
        monkeypatch.setattr(projects, "build_with_retries", slow_build(started))
        build = asyncio.create_task(real_run_build(project_id, "A notes API"))
        await started.wait()
        assert await stop(project_id) == {"status": "stopping"}
        await asyncio.wait_for(build, timeout=5)  # ends at once, not after the 60 s "thinking"

    asyncio.run(scenario())
    assert projects.projects[project_id]["status"] == "stopped"
    assert last_event(project_id)["step"]["text"] == projects.STOPPED_TEXT
    assert project_id not in projects.results  # nothing was kept: no download, no live link
    assert project_id not in projects.building
    assert not live.is_running(project_id)
    assert client.get(f"/projects/{project_id}/download").status_code == 409


def test_steps_before_the_stop_stay_on_the_timeline(monkeypatch):
    project_id = new_project()

    async def scenario():
        started = asyncio.Event()
        monkeypatch.setattr(projects, "build_with_retries", slow_build(started))
        build = asyncio.create_task(real_run_build(project_id, "A notes API"))
        await started.wait()
        await stop(project_id)
        await build

    asyncio.run(scenario())
    statuses = [event["status"] for event in projects.events[project_id]]
    assert statuses == ["waiting", "working", "stopped"]
    assert projects.projects[project_id]["name"] == "Notes API"  # the name the agent gave is kept


def test_stop_during_the_retry_loops_wait_ends_it(monkeypatch):
    # The real retry loop (F-4): try 1 ends "busy", so the loop waits 30 s before try 2. Stop during that wait.
    from agent import retry

    project_id = new_project()
    tries = []

    async def busy_build(message, instruction, model, report, start_files=None):
        tries.append(model)
        return BuildResult(status="failed", reason="The AI service is busy.", files={}, kind="service_busy")

    monkeypatch.setattr(retry, "build_project", busy_build)

    async def scenario():
        build = asyncio.create_task(real_run_build(project_id, "A notes API"))
        while not tries:
            await asyncio.sleep(0.01)  # wait until try 1 has run
        await asyncio.sleep(0.1)  # now the loop is in its 30 s wait
        await stop(project_id)
        await asyncio.wait_for(build, timeout=5)  # far less than the 30 s wait

    asyncio.run(scenario())
    assert len(tries) == 1  # try 2 never started
    assert projects.projects[project_id]["status"] == "stopped"


def test_a_step_arriving_after_stop_is_dropped():
    project_id = new_project()
    projects.stop_asked.add(project_id)
    projects.report_to(project_id)(THINKING)  # e.g. the AI's answer that was already on its way
    assert [event["status"] for event in projects.events[project_id]] == ["waiting"]


def test_stop_before_the_build_began_never_starts_it(monkeypatch):
    project_id = new_project()
    called = []

    async def must_not_run(*args, **kwargs):
        called.append(True)

    monkeypatch.setattr(projects, "build_with_retries", must_not_run)

    async def scenario():
        await stop(project_id)  # still "waiting": no job yet
        await real_run_build(project_id, "A notes API")

    asyncio.run(scenario())
    assert called == []
    assert projects.projects[project_id]["status"] == "stopped"


def test_pressing_stop_twice_gives_one_stopped_event(monkeypatch):
    project_id = new_project()

    async def scenario():
        started = asyncio.Event()
        monkeypatch.setattr(projects, "build_with_retries", slow_build(started))
        build = asyncio.create_task(real_run_build(project_id, "A notes API"))
        await started.wait()
        await stop(project_id)
        await stop(project_id)  # a double click
        await build

    asyncio.run(scenario())
    assert [event["status"] for event in projects.events[project_id]].count("stopped") == 1


def test_a_finished_build_cannot_be_stopped():
    project_id = new_project()
    projects.projects[project_id]["status"] = "ready"
    answer = client.post(f"/projects/{project_id}/stop")
    assert answer.status_code == 409
    assert answer.json()["detail"] == "This build has already finished, so there is nothing to stop."
    assert projects.projects[project_id]["status"] == "ready"  # unchanged


def test_stop_of_an_unknown_project_gives_404():
    assert client.post("/projects/p_does_not_exist/stop").status_code == 404


def test_stop_through_the_api_answers_202():
    # Through HTTP: a project that has not begun building (run_build is switched off in these tests).
    project_id = new_project()
    answer = client.post(f"/projects/{project_id}/stop")
    assert (answer.status_code, answer.json()) == (202, {"status": "stopping"})
    assert project_id in projects.stop_asked


def test_a_cancel_that_is_not_the_persons_stop_is_not_called_stopped(monkeypatch):
    # The server shutting down also cancels jobs. That must not say "You stopped this build".
    project_id = new_project()

    async def scenario():
        started = asyncio.Event()
        monkeypatch.setattr(projects, "build_with_retries", slow_build(started))
        build = asyncio.create_task(real_run_build(project_id, "A notes API"))
        await started.wait()
        projects.building[project_id].cancel()  # not through stop_project
        with pytest.raises(asyncio.CancelledError):
            await build

    asyncio.run(scenario())
    assert projects.projects[project_id]["status"] == "working"
    assert "stopped" not in [event["status"] for event in projects.events[project_id]]


def test_the_stopped_stream_ends(monkeypatch):
    # The live stream hangs up after "stopped", like after "ready" or "failed".
    project_id = new_project()
    projects.stop_asked.add(project_id)
    asyncio.run(real_run_build(project_id, "A notes API"))
    with client.stream("GET", f"/projects/{project_id}/events") as stream:
        body = "".join(stream.iter_text())
    assert '"status":"stopped"' in body.replace(" ", "")
    assert projects.STOPPED_TEXT in body
