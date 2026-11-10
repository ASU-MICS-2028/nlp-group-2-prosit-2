"""Step 3: every generated API gets its own editor and reader keys, and no default key."""

from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
import yaml

from app import pipeline
from app.models import Analysis, FieldSpec
from app.openapi_builder import build_openapi
from app.packager import write_project, zip_project
from app.scaffold import MIN_KEY_LENGTH, ProjectKeys, new_keys, render_project, render_readme
from app.validators import readme_problems

ANALYSIS = Analysis(
    title="Bookshop API",
    description="Books in the shop.",
    resource_name="book",
    resource_plural="books",
    fields=[
        FieldSpec(name="title", type="str", required=True),
        FieldSpec(name="price", type="float", required=False),
    ],
)


def _env_values(text: str) -> dict[str, str]:
    """Reads NAME=value lines, skipping comments (like the launchers and Docker do)."""
    values = {}
    for line in text.splitlines():
        if line.strip() and not line.startswith("#"):
            name, _, value = line.partition("=")
            values[name.strip()] = value.strip()
    return values


def _files(keys: ProjectKeys | None = None) -> dict[str, str]:
    return render_project(ANALYSIS, build_openapi(ANALYSIS), keys=keys)


# --------------------------------------------------------------------------- the keys


def test_every_project_gets_its_own_long_random_keys() -> None:
    first, second = new_keys(), new_keys()
    assert first != second
    for key in (first.editor, first.reader):
        assert len(key) >= 40  # 32 random bytes
    assert first.editor != first.reader


def test_env_file_holds_the_keys_and_the_example_holds_none() -> None:
    keys = ProjectKeys(editor="e" * 20, reader="r" * 20)
    files = _files(keys)
    assert _env_values(files[".env"]) == {"EDITOR_KEY": "e" * 20, "READER_KEY": "r" * 20}
    assert _env_values(files[".env.example"]) == {"EDITOR_KEY": "", "READER_KEY": ""}
    # Two builds of the same design still get different keys
    assert _files()[".env"] != _files()[".env"]


def test_no_file_mentions_the_old_default_key() -> None:
    for name, content in _files().items():
        assert "demo-api-key" not in content, name


def test_keys_stay_out_of_git_and_docker_images_but_are_in_the_zip(tmp_path: Path) -> None:
    files = _files()
    assert ".env" in files[".gitignore"].splitlines()
    assert ".env" in files[".dockerignore"].splitlines()
    assert "env_file:\n      - .env" in files["docker-compose.yml"]
    project = tmp_path / "project"
    write_project(project, files)
    with zipfile.ZipFile(zip_project(project, tmp_path / "project.zip")) as archive:
        # The owner (only they can download it, builder step 2) gets the keys
        assert ".env" in archive.namelist()


# --------------------------------------------------------------------------- the generated API really uses them

# Runs inside the generated project: loads ITS .env, then tries each key on the real app
_PROBE = """
import json, os, sys
from pathlib import Path
for line in Path(".env").read_text().splitlines():
    if line.strip() and not line.startswith("#"):
        name, _, value = line.partition("=")
        os.environ[name.strip()] = value.strip()
os.environ["DATABASE_URL"] = "sqlite:///" + sys.argv[1]
from fastapi.testclient import TestClient
from app.db import init_db
from app.main import app
init_db()
client = TestClient(app)
editor = {"X-API-Key": os.environ["EDITOR_KEY"]}
reader = {"X-API-Key": os.environ.get("READER_KEY", "")}
codes = {
    "editor adds": client.post("/books", json={"title": "Half of a Yellow Sun"}, headers=editor).status_code,
    "reader lists": client.get("/books", headers=reader).status_code,
    "reader opens": client.get("/books/1", headers=reader).status_code,
    "reader adds": client.post("/books", json={"title": "x"}, headers=reader).status_code,
    "reader edits": client.put("/books/1", json={"title": "x"}, headers=reader).status_code,
    "reader deletes": client.delete("/books/1", headers=reader).status_code,
    "wrong key": client.get("/books", headers={"X-API-Key": "wrong-key-0123456789"}).status_code,
    "no key": client.get("/books").status_code,
    "health": client.get("/health").status_code,
    "editor deletes": client.delete("/books/1", headers=editor).status_code,
}
detail = client.get("/books", headers=editor).json()
print(json.dumps({"codes": codes, "detail": detail}))
"""


def _probe(project: Path, tmp_path: Path) -> dict:
    proc = subprocess.run(
        [sys.executable, "-c", _PROBE, str(tmp_path / "probe.db")],
        cwd=project,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return json.loads(proc.stdout.strip().splitlines()[-1])


def test_the_shipped_env_file_works_with_the_real_app(tmp_path: Path) -> None:
    project = tmp_path / "project"
    write_project(project, _files())

    result = _probe(project, tmp_path)

    assert result["codes"] == {
        "editor adds": 201,
        "reader lists": 200,
        "reader opens": 200,
        "reader adds": 403,
        "reader edits": 403,
        "reader deletes": 403,
        "wrong key": 401,
        "no key": 401,
        "health": 200,
        "editor deletes": 204,
    }


@pytest.mark.parametrize(
    "env_text",
    [
        "EDITOR_KEY=\nREADER_KEY=\n",  # someone used .env.example as it is
        "EDITOR_KEY=change-me\nREADER_KEY=\n",  # a weak, guessable key
        f"EDITOR_KEY={'e' * 30}\nREADER_KEY=short\n",  # a weak reader key
    ],
    ids=["no-keys", "short-editor-key", "short-reader-key"],
)
def test_missing_or_weak_keys_refuse_everything(tmp_path: Path, env_text: str) -> None:
    project = tmp_path / "project"
    files = _files()
    files[".env"] = env_text
    write_project(project, files)

    result = _probe(project, tmp_path)

    assert result["codes"]["health"] == 200  # still says it is running
    for check in ("editor adds", "reader lists", "wrong key", "no key"):
        assert result["codes"][check] == 503, check
    assert f"at least {MIN_KEY_LENGTH} characters" in result["detail"]["detail"]


# --------------------------------------------------------------------------- README and OpenAPI


def test_readme_explains_both_keys_and_uses_placeholders() -> None:
    readme = render_readme(ANALYSIS)
    assert readme_problems(readme, ANALYSIS) == []
    assert 'curl http://localhost:8000/books -H "X-API-Key: YOUR_READER_KEY"' in readme
    assert 'curl -X DELETE http://localhost:8000/books/1 -H "X-API-Key: YOUR_EDITOR_KEY"' in readme


def test_readme_check_catches_the_old_demo_key_and_missing_key_names() -> None:
    readme = render_readme(ANALYSIS)
    old_style = readme.replace("YOUR_READER_KEY", "demo-api-key").replace("READER_KEY", "the key")
    problems = readme_problems(old_style, ANALYSIS)
    assert any("demo-api-key" in p for p in problems)
    assert any("READER_KEY" in p for p in problems)


def test_an_llm_readme_with_the_old_demo_key_is_replaced_by_the_template(monkeypatch) -> None:
    llm_text = render_readme(ANALYSIS).replace("YOUR_EDITOR_KEY", "demo-api-key")
    monkeypatch.setattr(pipeline, "chat", lambda messages: llm_text)

    text, metrics = pipeline.generate_readme(ANALYSIS)

    assert metrics["readme_source"] == "template"
    assert "demo-api-key" not in text


def test_openapi_documents_403_only_where_data_changes() -> None:
    spec = yaml.safe_load(build_openapi(ANALYSIS))
    paths = spec["paths"]
    assert "403" in paths["/books"]["post"]["responses"]
    assert "403" in paths["/books/{item_id}"]["put"]["responses"]
    assert "403" in paths["/books/{item_id}"]["delete"]["responses"]
    assert "403" not in paths["/books"]["get"]["responses"]
    assert "403" not in paths["/books/{item_id}"]["get"]["responses"]
