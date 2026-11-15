"""Tests for the take-home zip, GET /projects/{id}/download (F-5)."""

import io
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agent import prompts
from agent.takehome import takehome_files
from agent.tests.test_prompts import example_files  # pulls the example project out of the builder prompt
from backend import projects
from backend.builder import BuildResult
from backend.main import app
from backend.runner import run_tests

client = TestClient(app)

NOTES_FILES = {"app/__init__.py": "", "app/main.py": "print('hello')\n", "tests/test_notes.py": "def test_ok():\n    pass\n"}


# Starting a project must never call the real AI in tests, so the build job does nothing (as in test_projects.py).
@pytest.fixture(autouse=True)
def no_real_builds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(projects, "run_build", lambda project_id, request: None)


def project_with(status: str, files: dict[str, str] | None) -> str:
    # A project whose build ended with `status` and handed back `files` (None = the build is still going).
    project_id = client.post("/projects", json={"request": "A notes API"}).json()["id"]
    projects.projects[project_id]["status"] = status
    if files is not None:
        projects.results[project_id] = BuildResult(status=status, reason="", files=files)
    return project_id


def unzip(content: bytes) -> dict[str, str]:
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        return {name: archive.read(name).decode() for name in archive.namelist()}


def test_a_ready_project_downloads_as_a_zip_of_its_files() -> None:
    project_id = project_with("ready", NOTES_FILES)

    response = client.get(f"/projects/{project_id}/download")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    # "attachment" makes the browser save the file instead of opening it; the name is what the person sees.
    assert response.headers["content-disposition"] == f'attachment; filename="{project_id}.zip"'
    # The project's own files, plus the run files every zip gets (F-6: Dockerfile, HOW_TO_RUN.md, ...).
    assert unzip(response.content) == {**takehome_files(), **NOTES_FILES}


def test_a_project_that_is_still_building_cannot_be_downloaded() -> None:
    project_id = project_with("working", None)

    response = client.get(f"/projects/{project_id}/download")

    assert response.status_code == 409
    assert response.json() == {"detail": "The API is not ready yet, so there is nothing to download."}


def test_a_failed_build_cannot_be_downloaded_even_if_it_wrote_files() -> None:
    # The contract: only when the status is ready. Half-finished code with failing tests is not a take-home.
    project_id = project_with("failed", NOTES_FILES)

    assert client.get(f"/projects/{project_id}/download").status_code == 409


def test_an_unknown_project_is_404() -> None:
    response = client.get("/projects/p_does_not_exist/download")

    assert response.status_code == 404
    assert response.json() == {"detail": "Project not found."}


def test_the_unzipped_project_passes_its_own_tests(tmp_path: Path) -> None:
    # PLAN's "done when" for F-5: unzip the download, run pytest, and the tests pass.
    # The builder prompt's example project is a real generated-style project (Notes API), so no AI is needed.
    files = example_files(prompts.load_prompt("builder"))
    project_id = project_with("ready", files)

    response = client.get(f"/projects/{project_id}/download")
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        archive.extractall(tmp_path)  # what the person does after downloading

    unzipped = {str(path.relative_to(tmp_path).as_posix()): path.read_text() for path in tmp_path.rglob("*") if path.is_file()}
    assert unzipped == {**takehome_files(), **files}  # nothing lost or changed on the way, plus the run files
    assert run_tests(unzipped, timeout_seconds=60).passed
