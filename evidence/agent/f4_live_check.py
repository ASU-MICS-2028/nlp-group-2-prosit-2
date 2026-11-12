"""F-4 live check: can the retry loop get a seeded FAILING project to pass with real Gemini?

The seeded project is a small Notes API with one planted bug: deleting a note that does not exist
answers 204 ("done") instead of 404 ("not found"). Its own test catches that, so it starts out failing.
Needs GEMINI_API_KEY and LLM_MODEL in the repo's .env. It never prints the key.
Run from the repo root:  python evidence/agent/f4_live_check.py
"""

import asyncio
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))  # so "agent" and "backend" can be imported when run as a script

from dotenv import dotenv_values  # noqa: E402

from agent.prompts import builder_instruction, builder_message  # noqa: E402
from agent.retry import build_with_retries  # noqa: E402
from backend.runner import run_tests  # noqa: E402

settings = dotenv_values(REPO / ".env")
os.environ["GOOGLE_API_KEY"] = settings["GEMINI_API_KEY"]  # the name ADK looks for
MODEL = settings["LLM_MODEL"]

DATABASE = '''import sqlite3

DB_PATH = "app.db"


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def create_tables() -> None:
    connection = connect()
    connection.execute("CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL)")
    connection.commit()
    connection.close()
'''

MAIN = '''from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field

from app import database

app = FastAPI(title="Notes API", description="Keep a list of notes.")
database.create_tables()


class NoteIn(BaseModel):
    title: str = Field(min_length=1)


class Note(NoteIn):
    id: int


@app.get("/notes", summary="See all notes")
def list_notes() -> list[Note]:
    connection = database.connect()
    rows = connection.execute("SELECT * FROM notes ORDER BY id").fetchall()
    connection.close()
    return [Note(id=row["id"], title=row["title"]) for row in rows]


@app.post("/notes", status_code=201, summary="Add a note")
def create_note(note: NoteIn) -> Note:
    connection = database.connect()
    cursor = connection.execute("INSERT INTO notes (title) VALUES (?)", (note.title,))
    connection.commit()
    connection.close()
    return Note(id=cursor.lastrowid, title=note.title)


@app.delete("/notes/{note_id}", status_code=204, summary="Delete a note")
def delete_note(note_id: int) -> Response:
    connection = database.connect()
    connection.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    connection.commit()
    connection.close()
    return Response(status_code=204)  # BUG: never checks that the note existed
'''

CONFTEST = '''import pytest
from fastapi.testclient import TestClient

from app import database
from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "test.db"))
    database.create_tables()
    return TestClient(app)
'''

TESTS = '''def test_add_and_list(client):
    client.post("/notes", json={"title": "Milk"})
    assert [note["title"] for note in client.get("/notes").json()] == ["Milk"]


def test_empty_title_is_refused(client):
    assert client.post("/notes", json={"title": ""}).status_code == 422


def test_delete_a_note(client):
    client.post("/notes", json={"title": "Milk"})
    assert client.delete("/notes/1").status_code == 204
    assert client.get("/notes").json() == []


def test_deleting_a_missing_note_gives_404(client):
    assert client.delete("/notes/99").status_code == 404
'''

SEEDED = {
    "requirements.txt": "fastapi==0.162.0\nuvicorn==0.54.0\npytest==9.2.0\nhttpx==0.28.1\n",
    "conftest.py": CONFTEST,
    "app/__init__.py": "",
    "app/database.py": DATABASE,
    "app/main.py": MAIN,
    "tests/test_notes.py": TESTS,
}

PLAN = {
    "name": "Notes API",
    "summary": "Keep a list of notes.",
    "endpoints": [
        {"method": "GET", "path": "/notes", "description": "See all notes"},
        {"method": "POST", "path": "/notes", "description": "Add a note"},
        {"method": "DELETE", "path": "/notes/{note_id}", "description": "Delete a note"},
    ],
    "tables": [{"name": "notes", "fields": [{"name": "id", "type": "int", "auto": True},
                                             {"name": "title", "type": "str", "required": True}]}],
    "test_count": 4,
}


def show(event: dict[str, object]) -> None:
    step = event.get("step") or {}
    attempt = f" attempt {event['attempt']}/{event['max_attempts']}" if "attempt" in event else ""
    text = str(step.get("text", "")).replace("\n", " ")[:160]
    print(f"{event['status']:9}{attempt} {step.get('kind', ''):8} {text}")


async def main() -> None:
    before = run_tests(SEEDED)
    print(f"Model: {MODEL}")
    print(f"Seeded project before the loop: passed={before.passed}; {before.output.strip().splitlines()[-1]}")
    started = time.time()
    result = await build_with_retries(builder_message(PLAN), builder_instruction(), MODEL, show, start_files=SEEDED)
    print(f"\nTook {time.time() - started:.0f}s. Final: {result.status} ({result.kind}): {result.reason}")
    after = run_tests(result.files)
    print(f"Our own test run on the final files: passed={after.passed}; {after.output.strip().splitlines()[-1]}")


asyncio.run(main())
