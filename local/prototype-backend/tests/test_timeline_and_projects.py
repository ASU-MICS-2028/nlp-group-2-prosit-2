"""The build timeline (real test results, Thinking/Doing/Result steps) and the sidebar's GET /projects."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from app import auth
from app.config import settings
from app.jobs import INTERRUPTED, Job, add_step, create_job, get_job, recover_interrupted_jobs, run_job, save_job
from app.models import Analysis, FieldSpec, Understanding
from app.openapi_builder import build_openapi
from app.packager import write_project
from app.project_tests import run_project_tests
from app.scaffold import render_project

BOOKS = Analysis(
    title="Bookshop API", description="Books in the shop.", resource_name="book", resource_plural="books",
    fields=[FieldSpec(name="title", type="str", required=True), FieldSpec(name="price", type="float", required=False)],
)


def _project(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    return tmp_path / "project", render_project(BOOKS, build_openapi(BOOKS))


# --------------------------------------------------------------------------- running the generated tests


def test_a_generated_projects_tests_run_and_pass(tmp_path: Path) -> None:
    project, files = _project(tmp_path)
    write_project(project, files)

    outcomes = run_project_tests(project)

    assert len(outcomes) == 11 and all(o["passed"] for o in outcomes)
    assert "reader cannot change" in [o["name"] for o in outcomes]  # plain words, not test_reader_cannot_change
    # Left for the person: the plain report. Tidied away: the test database, the XML, caches
    assert (project / "TEST_RESULTS.md").exists()
    assert not (project / "test.db").exists()
    assert not (project / ".builder-tests.xml").exists()
    assert not list(project.rglob("__pycache__"))


def test_a_failing_test_is_reported_with_its_reason(tmp_path: Path) -> None:
    project, files = _project(tmp_path)
    router = "app/routers/books.py"
    files[router] = files[router].replace("status.HTTP_204_NO_CONTENT", "status.HTTP_200_OK")
    write_project(project, files)

    failed = [o for o in run_project_tests(project) if not o["passed"]]

    assert [o["name"] for o in failed] == ["delete book"]
    assert "200 instead of 204" in failed[0]["message"]


def test_tests_that_cannot_start_raise_a_plain_error(tmp_path: Path) -> None:
    project, files = _project(tmp_path)
    del files["app/main.py"]
    write_project(project, files)
    # A missing app makes pytest stop while collecting; the report still exists but holds an error,
    # or no report is written at all. Either way nothing passes.
    try:
        outcomes = run_project_tests(project)
    except RuntimeError as error:
        assert "could not start" in str(error)
    else:
        assert not any(o["passed"] for o in outcomes)


# --------------------------------------------------------------------------- the whole build, offline


@pytest.fixture
def owner(sign_in, tmp_path, monkeypatch) -> int:
    sign_in()
    monkeypatch.setattr(settings, "generated_dir", str(tmp_path / "generated"))
    return auth.find_user("ama@example.com").id


def test_a_real_build_fills_the_timeline_and_runs_11_tests(owner: int) -> None:
    # No real LLM in tests: the OpenAPI file and README fall back to the templates, which is enough here
    job = create_job("bookshop", owner_id=owner, analysis=BOOKS)
    run_job(job.id)
    done = get_job(job.id)

    assert done.status == "succeeded"
    assert len(done.tests) == 11 and all(t["passed"] for t in done.tests)
    assert [s["kind"] for s in done.steps] == ["Thinking", "Doing", "Doing", "Doing", "Doing", "Result"]
    assert done.steps[0]["text"] == "I will build books, then test them."
    assert done.steps[-1] == {"kind": "Result", "text": "All 11 tests passed. Your API is ready.", "state": "done"}
    assert all(s["state"] == "done" for s in done.steps)  # nothing left "in progress"
    with zipfile.ZipFile(done.zip_path) as archive:
        names = archive.namelist()
    assert "TEST_RESULTS.md" in names and "test.db" not in names


def test_failed_tests_end_the_timeline_with_the_details(owner: int, monkeypatch) -> None:
    def broken_tests(project_dir):
        return [{"name": "health", "passed": True, "message": ""},
                {"name": "delete", "passed": False, "message": "answered 200 instead of 204"}]

    monkeypatch.setattr("app.pipeline.run_project_tests", broken_tests)
    job = create_job("bookshop", owner_id=owner, analysis=BOOKS)
    run_job(job.id)
    last = get_job(job.id).steps[-1]

    assert get_job(job.id).status == "succeeded"  # the zip is still there to inspect
    assert last["state"] == "failed" and last["text"].startswith("1 of 2 tests failed")
    assert last["output"] == "FAILED delete: answered 200 instead of 204"


def test_tests_that_could_not_run_are_said_plainly(owner: int, monkeypatch) -> None:
    def cannot_run(project_dir):
        raise RuntimeError("The tests took longer than 120 seconds and were stopped.")

    monkeypatch.setattr("app.pipeline.run_project_tests", cannot_run)
    job = create_job("bookshop", owner_id=owner, analysis=BOOKS)
    run_job(job.id)
    last = get_job(job.id).steps[-1]

    assert last["state"] == "failed" and "could not run" in last["text"]
    assert "120 seconds" in last["output"]


def test_add_step_marks_the_previous_step_done() -> None:
    job = Job(id="j", owner_id=1, requirement="x")
    add_step(job, "Thinking", "one")
    add_step(job, "Doing", "two", output="log")
    assert job.steps == [
        {"kind": "Thinking", "text": "one", "state": "done"},
        {"kind": "Doing", "text": "two", "state": "current", "output": "log"},
    ]


def test_a_build_cut_off_by_a_restart_ends_its_timeline(owner: int) -> None:
    job = create_job("bookshop", owner_id=owner, analysis=BOOKS)
    job.status = "running"
    add_step(job, "Doing", "Writing the project files.")
    save_job(job)

    recover_interrupted_jobs()
    steps = get_job(job.id).steps

    assert steps[0]["state"] == "done"
    assert steps[-1] == {"kind": "Result", "text": INTERRUPTED, "state": "failed"}


# --------------------------------------------------------------------------- GET /projects


def test_projects_list_your_projects_newest_first_with_a_status(client, sign_in, monkeypatch) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    ready = Understanding(verdict="clear", message="ok", blueprint=BOOKS)
    refused = Understanding(verdict="disallowed", message="no")
    replies = iter([ready, ready, ready, refused])
    monkeypatch.setattr("app.main.understand", lambda requirement, background="": next(replies))
    monkeypatch.setattr("app.main.run_job", lambda job_id: None)
    monkeypatch.setattr("app.main.after_approval", lambda session_id: None)
    ama, kofi = sign_in("ama@example.com"), sign_in("kofi@example.com")

    def start(text: str) -> str:
        return client.post("/sessions", json={"requirement": text}, headers=ama).json()["id"]

    waiting = start("A bookshop where I can add books")
    building = start("Another bookshop for my sister")
    client.post(f"/sessions/{building}/build", headers=ama)
    finished = start("A third bookshop for my cousin")
    client.post(f"/sessions/{finished}/build", headers=ama)
    job = get_job(client.get(f"/sessions/{finished}", headers=ama).json()["job_id"])
    job.status, job.title = "succeeded", "Cousin's Books API"
    save_job(job)
    stopped = start("Something not allowed at all")

    projects = client.get("/projects", headers=ama).json()

    assert [(p["id"], p["status"]) for p in projects] == [
        (stopped, "stopped"),
        (finished, "ready"),
        (building, "working"),
        (waiting, "waiting"),
    ]
    assert projects[1]["name"] == "Cousin's Books API"  # the build's title wins
    assert projects[0]["name"] == "Something not allowed at all"  # no design: the request's start
    assert client.get("/projects", headers=kofi).json() == []  # never someone else's
    assert client.get("/projects").status_code == 401


def test_openapi_falls_back_to_the_template_when_the_llm_is_down() -> None:
    """Found while building the timeline: an LLM outage used to fail the whole build here."""
    from app.pipeline import generate_openapi

    yaml_text, metrics = generate_openapi(BOOKS)  # conftest blocks the real LLM, like an outage

    assert metrics["openapi_source"] == "fallback_builder"
    assert yaml_text == build_openapi(BOOKS)


def test_tests_run_from_a_relative_folder_like_the_real_server(tmp_path: Path, monkeypatch) -> None:
    """Found by the live check: the server's generated/ folder is relative, and the report went missing."""
    monkeypatch.chdir(tmp_path)
    project, files = Path("generated") / "job1" / "project", render_project(BOOKS, build_openapi(BOOKS))
    write_project(project, files)

    outcomes = run_project_tests(project)

    assert len(outcomes) == 11 and all(o["passed"] for o in outcomes)
    assert not list(tmp_path.rglob(".builder-tests.xml"))  # no stray report left anywhere


def test_projects_with_the_same_name_are_numbered(client, sign_in, monkeypatch) -> None:
    """Found in the browser check: two "School Management API" projects looked identical."""
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    ready = Understanding(verdict="clear", message="ok", blueprint=BOOKS)
    monkeypatch.setattr("app.main.understand", lambda requirement, background="": ready)
    me = sign_in()
    first = client.post("/sessions", json={"requirement": "A bookshop for my town"}, headers=me).json()["id"]
    second = client.post("/sessions", json={"requirement": "Another bookshop for me"}, headers=me).json()["id"]
    third = client.post("/sessions", json={"requirement": "A third bookshop please"}, headers=me).json()["id"]

    names = {p["id"]: p["name"] for p in client.get("/projects", headers=me).json()}

    assert names == {first: "Bookshop API", second: "Bookshop API (2)", third: "Bookshop API (3)"}
