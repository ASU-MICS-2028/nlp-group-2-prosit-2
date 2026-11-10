from __future__ import annotations

import secrets
from dataclasses import dataclass

from app.models import Analysis
from app.scaffold_code import (
    access_tests_py,
    main_py,
    models_py,
    resource_tests_py,
    router_py,
    sample_json,
    schemas_py,
    support_py,
    words,
)


@dataclass(frozen=True)
class ProjectKeys:
    """Step 3: the two keys every generated API ships with (written to its .env file).

    editor: can look at records and change them. reader: can only look.
    """

    editor: str
    reader: str


def new_keys() -> ProjectKeys:
    # 32 random bytes → 43 URL-safe characters each: far too many to guess
    return ProjectKeys(editor=secrets.token_urlsafe(32), reader=secrets.token_urlsafe(32))


# Keys shorter than this are refused by the generated API (stops weak keys like "1234" or "change-me")
MIN_KEY_LENGTH = 16

def render_project(
    analysis: Analysis,
    openapi_yaml: str,
    readme: str | None = None,
    keys: ProjectKeys | None = None,
) -> dict[str, str]:
    # A fresh pair of keys for every project, unless the caller (a test) passes its own
    keys = keys or new_keys()
    files: dict[str, str] = {
        "app/__init__.py": "",
        "app/routers/__init__.py": "",
        "app/db.py": _db_py(),
        "app/auth.py": _auth_py(),
        "app/models.py": models_py(analysis),
        "app/schemas.py": schemas_py(analysis),
        "app/main.py": main_py(analysis),
        # Without pythonpath, a bare `pytest` puts tests/ on sys.path and `import app` fails.
        "pytest.ini": "[pytest]\npythonpath = .\ntestpaths = tests\n",
        "tests/conftest.py": _conftest_py(analysis),
        "tests/support.py": support_py(analysis),
        "tests/test_access.py": access_tests_py(analysis),
        "requirements.txt": _requirements(),
        "Dockerfile": _dockerfile(),
        "docker-compose.yml": _compose(),
        "Start.bat": _start_bat(),
        "Start.command": _start_command(),
        # The real keys. Only the project's owner can download the zip (builder step 2).
        ".env": _env_file(keys),
        # Names only, no values: if .env is lost, the API refuses everything until keys are added
        ".env.example": _env_example(),
        "openapi.yaml": openapi_yaml,
        "README.md": readme or render_readme(analysis),
        ".gitignore": "data/\n__pycache__/\n.pytest_cache/\ntest.db\n.env\n",
        # Keep the API key, local databases and caches out of the image built by `COPY . .`.
        ".dockerignore": ".env\ndata/\ntest.db\nTEST_RESULTS.md\n__pycache__/\n.pytest_cache/\nStart.bat\nStart.command\n",
    }
    # One router and one test file per record type
    for resource in analysis.resources:
        files[f"app/routers/{resource.plural}.py"] = router_py(analysis, resource)
        files[f"tests/test_{resource.plural}.py"] = resource_tests_py(analysis, resource)
    return files


def _records_table(analysis: Analysis) -> str:
    """A README table: each record type, its address, what it stores, and what it links to."""
    rows = ["| Record type | Address | Details | Links to |", "|---|---|---|---|"]
    for resource in analysis.in_creation_order():
        details = ", ".join(f"`{f.name}`" for f in resource.value_fields)
        links = ", ".join(f"`{f.name}` → one {words(f.links_to or '')}" for f in resource.link_fields) or "-"
        rows.append(f"| {words(resource.plural).capitalize()} | `/{resource.plural}` | {details} | {links} |")
    return "\n".join(rows)


def _links_section(analysis: Analysis) -> str:
    linked = [(r, f) for r in analysis.in_creation_order() for f in r.link_fields]
    if not linked:
        return ""
    child, field = linked[0]
    target = analysis.resource(field.links_to or "")
    target_plural = target.plural if target else ""
    return f"""
## How the records link together

A link is a detail that holds the id of another record, for example `{field.name}` on {words(child.plural)}.
- Add the {words(field.links_to or '')} first, then use its `id` when you add {words(child.plural)}.
- A link to a record that does not exist is refused (422).
- A record that others still link to cannot be deleted (409): delete or change those first.
- List only the {words(child.plural)} of one {words(field.links_to or '')}:

```bash
curl "http://localhost:8000/{child.plural}?{field.name}=1" -H "X-API-Key: YOUR_READER_KEY"
```

(The {words(target_plural)} must exist before you add {words(child.plural)} that link to them.)
"""


def render_readme(analysis: Analysis) -> str:
    first = analysis.in_creation_order()[0]
    plural = first.plural
    create = sample_json(first)
    field = first.value_fields[0]
    update = '{ "' + field.name + '": "Updated ' + words(field.name) + '" }' if field.type == "str" else "{}"
    return f"""# {analysis.title}

{analysis.description}

This project is a FastAPI API with SQLite, SQLModel, and API-key authentication.
You do not need to write any code to run it.

## What it stores

{_records_table(analysis)}

Each record type can be added (POST), listed (GET), opened (GET /…/{{id}}), changed (PUT) and deleted (DELETE).

## Your keys

This API has two keys, made just for you. They are in the `.env` file in this folder
(open it with Notepad or TextEdit):

- `EDITOR_KEY` can look at records **and change them** (add, edit, delete). Keep it private.
- `READER_KEY` can **only look**. You can share it with people who just need to read.

Send a key on every request except `/health`, in the header `X-API-Key`.
In the examples below, replace `YOUR_EDITOR_KEY` or `YOUR_READER_KEY` with the value from `.env`.
In the interactive docs, click **Authorize** and paste a key.
Using the reader key to change something is refused with 403 (Forbidden).
There is no default key: without keys in `.env`, the API refuses every request.

## Start the API (no installs needed)

Double-click **`Start.bat`** on Windows or **`Start.command`** on macOS.

The first start downloads Python and the API's packages, which takes a minute or two. Your browser then
opens the interactive docs. Keep the window open while you use the API; close it to stop.

On macOS, if you see "cannot be opened because it is from an unidentified developer", right-click
`Start.command`, choose **Open**, then **Open** again.

## Start the API with Docker (for developers)

1. Keep the `.env` file in this folder: Docker reads your keys from it.
2. From this folder, run:

```bash
docker compose up --build
```

The API will be available at http://localhost:8000
Interactive docs: http://localhost:8000/docs

## Example requests ({words(plural)})

Health check (no key required):

```bash
curl http://localhost:8000/health
```

Create:

```bash
curl -X POST http://localhost:8000/{plural} \\
  -H "X-API-Key: YOUR_EDITOR_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{create}'
```

List:

```bash
curl http://localhost:8000/{plural} -H "X-API-Key: YOUR_READER_KEY"
```

Get by id:

```bash
curl http://localhost:8000/{plural}/1 -H "X-API-Key: YOUR_READER_KEY"
```

Update:

```bash
curl -X PUT http://localhost:8000/{plural}/1 \\
  -H "X-API-Key: YOUR_EDITOR_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{update}'
```

Delete:

```bash
curl -X DELETE http://localhost:8000/{plural}/1 -H "X-API-Key: YOUR_EDITOR_KEY"
```

The other record types work the same way at their own address (see the table above).
{_links_section(analysis)}
## Run tests

Requires Python 3.10 or newer. From this folder (the one containing `pytest.ini`), run:

```bash
pip install -r requirements.txt
pytest
```

After the tests run, open `TEST_RESULTS.md` in this folder for a plain-English summary of
what was checked and whether each check passed.
"""



def _db_py() -> str:
    return '''from __future__ import annotations

import os
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

_raw_url = os.getenv("DATABASE_URL", "sqlite:///./data/app.db")
if _raw_url.startswith("sqlite:///") and ":memory:" not in _raw_url:
    # Create whichever folder the SQLite file lives in, not just ./data.
    Path(_raw_url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)

connect_args = {"check_same_thread": False} if _raw_url.startswith("sqlite") else {}
engine = create_engine(_raw_url, connect_args=connect_args)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
'''


_KEYS_HELP = (
    "# Keys for this API. Send one in the X-API-Key header on every request except /health.\n"
    "# EDITOR_KEY can look at records AND change them (add, edit, delete). Keep it private.\n"
    "# READER_KEY can only look. You may share it with people who just need to read.\n"
    f"# To change a key: replace it with a new random value (at least {MIN_KEY_LENGTH} characters), then restart.\n"
)


def _env_file(keys: ProjectKeys) -> str:
    return f"{_KEYS_HELP}EDITOR_KEY={keys.editor}\nREADER_KEY={keys.reader}\n"


def _env_example() -> str:
    return (
        f"# Copy this file to .env and put in two long random keys (at least {MIN_KEY_LENGTH} characters each).\n"
        f"{_KEYS_HELP}EDITOR_KEY=\nREADER_KEY=\n"
    )


def _auth_py() -> str:
    return f'''"""Who may use this API. Two keys live in the .env file:

- EDITOR_KEY: can look at records and change them (add, edit, delete). Keep it private.
- READER_KEY: can only look at records. Safe to give to people who just need to read.

Send a key in the X-API-Key header. There is no default key: if the keys are not set up,
the API refuses every request instead of letting anyone in.
"""

from __future__ import annotations

import hmac
import os

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

EDITOR = "editor"
READER = "reader"
MIN_KEY_LENGTH = {MIN_KEY_LENGTH}


def _same(given: str, expected: str) -> bool:
    # compare_digest takes the same time however much of the key matches, so timing gives no hints
    return bool(expected) and hmac.compare_digest(given.encode(), expected.encode())


def _configured_keys() -> tuple[str, str]:
    editor_key = os.getenv("EDITOR_KEY", "").strip()
    reader_key = os.getenv("READER_KEY", "").strip()
    if len(editor_key) < MIN_KEY_LENGTH or (reader_key and len(reader_key) < MIN_KEY_LENGTH):
        raise HTTPException(
            status_code=503,
            detail=(
                "This API has no safe keys set up. Put EDITOR_KEY and READER_KEY, each at least "
                f"{{MIN_KEY_LENGTH}} characters, in the .env file, then restart the API."
            ),
        )
    return editor_key, reader_key


def role_for(key: str | None) -> str | None:
    """Which role a key gives: "editor", "reader", or None for a missing or wrong key."""
    editor_key, reader_key = _configured_keys()
    if not key:
        return None
    if _same(key, editor_key):
        return EDITOR
    if _same(key, reader_key):
        return READER
    return None


def require_reader(key: str | None = Security(api_key_header)) -> str:
    """For looking at records: the reader key or the editor key."""
    role = role_for(key)
    if role is None:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return role


def require_editor(key: str | None = Security(api_key_header)) -> str:
    """For adding, editing and deleting: only the editor key."""
    role = role_for(key)
    if role is None:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    if role != EDITOR:
        raise HTTPException(
            status_code=403,
            detail="This key can only look at records. Use the EDITOR_KEY to add, edit or delete.",
        )
    return role
'''


_CONFTEST_TEMPLATE = '''import os
import time
from pathlib import Path

# Anchor to the project root so tests behave the same from any working directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
API_TITLE = __API_TITLE__

test_db = PROJECT_ROOT / "test.db"
if test_db.exists():
    test_db.unlink()

# Test keys only (the real ones are in .env). Long enough to pass the minimum-length rule.
os.environ["EDITOR_KEY"] = "test-editor-key-0123456789"
os.environ["READER_KEY"] = "test-reader-key-0123456789"
os.environ["DATABASE_URL"] = f"sqlite:///{test_db.as_posix()}"


# ---------------------------------------------------------------------------
# Plain-language report: every test run rewrites TEST_RESULTS.md in this folder.
# Each test's docstring reads "Check name: what it means for you".

_checks: dict[str, dict] = {}
_start_errors: list[str] = []


def _first_line(text: str) -> str:
    lines = [line.strip() for line in str(text).strip().splitlines() if line.strip()]
    line = lines[0] if lines else "Unknown error"
    for prefix in ("AssertionError: ", "E   "):
        line = line.removeprefix(prefix)
    return line.replace("|", "/")[:300]


def pytest_collection_modifyitems(items):
    for item in items:
        function = getattr(item, "function", None)
        doc = ((function.__doc__ if function else None) or "").strip()
        name, _, meaning = doc.partition(":")
        _checks[item.nodeid] = {
            "name": name.strip() or item.name,
            "meaning": meaning.strip() or "-",
            "result": "not run",
            "problem": "",
        }


def pytest_collectreport(report):
    if report.failed:
        _start_errors.append(_first_line(report.longreprtext.strip().splitlines()[-1]))


def pytest_runtest_logreport(report):
    check = _checks.get(report.nodeid)
    if check is None:
        return
    if report.failed:
        check["result"] = "failed"
        crash = getattr(report.longrepr, "reprcrash", None)
        check["problem"] = _first_line(crash.message if crash else report.longreprtext)
    elif report.when == "call" and check["result"] != "failed":
        check["result"] = "skipped" if report.skipped else "passed"


def pytest_sessionfinish(session, exitstatus):
    checks = list(_checks.values())
    passed = sum(c["result"] == "passed" for c in checks)
    failed = [c for c in checks if c["result"] == "failed"]
    lines = [f"# Test Results: {API_TITLE}", "", f"Checked on {time.strftime('%Y-%m-%d at %H:%M')}.", ""]

    if _start_errors or not checks:
        lines += [
            "## ❌ The tests could not start",
            "",
            "Nothing was checked yet. This usually means the project's dependencies are not installed, "
            "or the tests were started from the wrong place.",
            "",
            "**How to fix it:** open a terminal in this project folder (the one containing `pytest.ini`) and run:",
            "",
            "```bash",
            "pip install -r requirements.txt",
            "pytest",
            "```",
            "",
            "Error reported:",
            "",
            *[f"- `{error}`" for error in (_start_errors or ["No tests were found."])],
        ]
    elif not failed:
        lines += [
            f"## ✅ All {len(checks)} checks passed",
            "",
            "The API works as expected: it starts, protects your data with keys "
            "(the reader key can only look; the editor key can also change), "
            "and lets you add, view, edit and delete records.",
        ]
    else:
        lines += [
            f"## ❌ {len(failed)} of {len(checks)} checks failed",
            "",
            "Some parts of the API are not working. See **Problems found** below.",
        ]

    if checks:
        lines += ["", "## Checks", "", "| Check | What it means for you | Result |", "|---|---|---|"]
        icons = {"passed": "✅ Passed", "failed": "❌ Failed", "skipped": "⏭️ Skipped"}
        for check in checks:
            lines.append(f"| {check['name']} | {check['meaning']} | {icons.get(check['result'], check['result'])} |")
        lines += ["", f"**{passed} of {len(checks)} checks passed.**"]

    if failed:
        lines += ["", "## Problems found", ""]
        lines += [f"- **{check['name']}**: {check['problem']}" for check in failed]
        lines += [
            "",
            "If you changed the code, undo the last change and run the checks again. "
            "Otherwise, generate the project again or share this file with a developer.",
        ]

    lines += [
        "",
        "## Run the checks again",
        "",
        "From this folder, run `pytest`. This file is rewritten every time the checks run.",
    ]
    (PROJECT_ROOT / "TEST_RESULTS.md").write_text("\\n".join(lines) + "\\n", encoding="utf-8")
'''


def _conftest_py(analysis: Analysis) -> str:
    return _CONFTEST_TEMPLATE.replace("__API_TITLE__", repr(analysis.title))


def _requirements() -> str:
    return """fastapi>=0.115.0
uvicorn[standard]>=0.32.0
sqlmodel>=0.0.22
pydantic>=2.0
httpx>=0.27.0
pytest>=8.0
python-dotenv>=1.0
"""


def _dockerfile() -> str:
    return """FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p /app/data
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
"""


_UV_RUN = (
    "uv run --no-project --python 3.12 --env-file .env --with-requirements requirements.txt "
    "uvicorn app.main:app --host 127.0.0.1 --port 8000"
)


def _start_bat() -> str:
    # No parentheses inside the if-block echo lines: cmd.exe would end the block early.
    lines = [
        "@echo off",
        'cd /d "%~dp0"',
        "title API server - close this window to stop",
        "where uv >nul 2>nul",
        "if errorlevel 1 (",
        "  echo Installing uv, a one-time setup that manages Python for you...",
        '  powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"',
        '  set "PATH=%USERPROFILE%\\.local\\bin;%PATH%"',
        ")",
        "if not exist .env copy .env.example .env >nul",
        "echo Starting your API at http://localhost:8000 - the first start can take a minute or two.",
        'start "" /b powershell -NoProfile -Command "while ($true) { try { if ((Invoke-WebRequest '
        "-UseBasicParsing http://localhost:8000/health).StatusCode -eq 200) { break } } catch {}; "
        "Start-Sleep -Seconds 1 }; Start-Process 'http://localhost:8000/docs'\"",
        _UV_RUN,
        "echo.",
        "echo The API has stopped. If this was unexpected, read the messages above.",
        "pause",
    ]
    return "\r\n".join(lines) + "\r\n"


def _start_command() -> str:
    return f"""#!/bin/bash
cd "$(dirname "$0")" || exit 1
if ! command -v uv >/dev/null 2>&1; then
  echo "Installing uv, a one-time setup that manages Python for you..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi
[ -f .env ] || cp .env.example .env
echo "Starting your API at http://localhost:8000 - the first start can take a minute or two."
( until curl -sf http://localhost:8000/health >/dev/null; do sleep 1; done; open http://localhost:8000/docs ) &
{_UV_RUN}
echo
echo "The API has stopped. If this was unexpected, read the messages above."
read -r -p "Press Enter to close this window."
"""


def _compose() -> str:
    return """services:
  api:
    build: .
    ports:
      - "8000:8000"
    # Your keys come from the .env file (it is kept out of the image by .dockerignore)
    env_file:
      - .env
    environment:
      DATABASE_URL: sqlite:///./data/app.db
    volumes:
      - api-data:/app/data

volumes:
  api-data:
"""
