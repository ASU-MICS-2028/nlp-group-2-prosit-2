"""Tests for the files added to every take-home zip (F-6)."""

import io
import re
import zipfile

from agent import prompts
from agent.takehome import TAKEHOME_NAMES, takehome_files
from backend.projects import zip_files


def test_every_run_file_is_there_and_not_empty():
    files = takehome_files()

    assert sorted(files) == sorted(TAKEHOME_NAMES)
    assert all(text.strip() for text in files.values())


def test_the_dockerfile_starts_the_app_the_builder_writes():
    # builder.md makes every project put its FastAPI `app` in app/main.py and list its libraries in requirements.txt.
    dockerfile = takehome_files()["Dockerfile"]
    builder = prompts.load_prompt("builder")

    assert "app/main.py" in builder and "requirements.txt" in builder
    assert "COPY requirements.txt ." in dockerfile
    assert '"app.main:app"' in dockerfile
    assert '"--host", "0.0.0.0"' in dockerfile  # reachable from outside the container
    assert re.search(r"^FROM python:3\.1[1-9]", dockerfile, re.MULTILINE)  # the Python version our code needs


def test_docker_compose_matches_the_contract_run_command_and_port():
    compose = takehome_files()["docker-compose.yml"]
    instructions = takehome_files()["HOW_TO_RUN.md"]

    assert "build: ." in compose
    assert '"8000:8000"' in compose
    assert "docker compose up" in instructions  # docs/api-contract.md's run_command


def test_the_instructions_cover_docker_python_windows_mac_and_the_docs_page():
    instructions = takehome_files()["HOW_TO_RUN.md"]

    for words in ("docker compose up", "uvicorn app.main:app", "pip install -r requirements.txt",
                  ".venv\\Scripts\\activate", "source .venv/bin/activate", "http://localhost:8000/docs",
                  "python -m pytest -q"):
        assert words in instructions, words


def test_dockerignore_keeps_local_setup_and_data_out():
    ignored = takehome_files()[".dockerignore"].splitlines()

    for name in (".venv", "app.db", "__pycache__"):
        assert name in ignored


def test_the_zip_gets_the_run_files_but_the_project_s_own_file_wins():
    project = {"app/main.py": "app = 1\n", "HOW_TO_RUN.md": "The agent's own notes\n"}

    with zipfile.ZipFile(io.BytesIO(zip_files(project))) as archive:
        names = set(archive.namelist())
        own_notes = archive.read("HOW_TO_RUN.md").decode()

    assert {"Dockerfile", "docker-compose.yml", ".dockerignore", "app/main.py"} <= names
    assert own_notes == "The agent's own notes\n"  # never overwrite what the project already has
