"""Tests for the scorer's live mode (E-2): it builds through a running server's API, like a user does.
A pretend server (httpx.MockTransport) answers, so no real build or AI call happens."""

import asyncio
import io
import json
import zipfile

import httpx

from evaluation import score
from evaluation.tests.test_score import BOOKS, MAIN_PY, REFUSE

DATABASE_PY = "CREATE TABLE IF NOT EXISTS books (id INTEGER PRIMARY KEY)"


def zipped(files: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, text in files.items():
            archive.writestr(name, text)
    return buffer.getvalue()


def pretend_server(final_status: str, final_text: str, files: dict[str, str], tries: int = 1, polls_before_end: int = 1):
    # Answers like our backend: POST /projects, GET /projects/{id} (working, then the final status),
    # GET /projects/{id}/events (the diary), GET /projects/{id}/download (zip, or 409 unless ready).
    seen = {"polls": 0}
    events = [{"status": "working", "attempt": n, "max_attempts": 3} for n in range(1, tries + 1)]
    events.append({"status": final_status, "step": {"kind": "Result", "text": final_text, "state": "done"}})

    def handle(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "POST" and path == "/projects":
            return httpx.Response(201, json={"id": "p_1", "status": "waiting", "questions": []})
        if path == "/projects/p_1":
            seen["polls"] += 1
            status = "working" if seen["polls"] <= polls_before_end else final_status
            return httpx.Response(200, json={"id": "p_1", "status": status, "file_count": len(files)})
        if path == "/projects/p_1/events":
            body = "".join(f"data: {json.dumps(event)}\n\n" for event in events)
            return httpx.Response(200, text=body, headers={"content-type": "text/event-stream"})
        if path == "/projects/p_1/download":
            if final_status != "ready":
                return httpx.Response(409, json={"detail": "The API is not ready yet."})
            return httpx.Response(200, content=zipped(files), headers={"content-type": "application/zip"})
        return httpx.Response(404)

    return httpx.MockTransport(handle)


def run_live(spec, transport):
    build = score.live_build("http://test", transport=transport, poll_seconds=0)
    return asyncio.run(score.score_one(spec, build, time_limit=5))


def test_a_ready_build_on_the_server_is_scored_from_its_download():
    files = {"app/main.py": MAIN_PY, "app/database.py": DATABASE_PY, "Dockerfile": "FROM python"}
    result = run_live(BOOKS, pretend_server("ready", "All tests pass.", files, polls_before_end=2))

    assert result.outcome == "pass"
    assert result.tables == 1


def test_tries_are_counted_from_the_servers_events():
    files = {"app/main.py": MAIN_PY, "app/database.py": DATABASE_PY}
    result = run_live(BOOKS, pretend_server("ready", "All tests pass.", files, tries=2))

    assert result.retries == 1


def test_a_failed_build_on_the_server_fails():
    result = run_live(BOOKS, pretend_server("failed", "Still not working after 3 tries. The tests still fail.", {"app/main.py": "x"}))

    assert result.outcome == "fail"
    assert "tests still fail" in result.reason


def test_the_daily_limit_on_the_server_is_a_limit():
    result = run_live(BOOKS, pretend_server("failed", "Today's free AI limit is used up. Please try again tomorrow.", {}))

    assert result.outcome == "limit"


def test_a_refusal_that_still_wrote_files_on_the_server_fails():
    result = run_live(REFUSE, pretend_server("failed", "The tests still fail after 3 tries.", {"app/main.py": "x"}))

    assert result.outcome == "fail"


def test_a_refusal_with_nothing_written_on_the_server_passes():
    result = run_live(REFUSE, pretend_server("failed", "The AI wrote no files.", {}))

    assert result.outcome == "pass"


def test_a_project_that_disappears_says_the_server_restarted():
    # Seen in E-2 run 1 (r01): the live server restarted during a build, so the project was gone (404).
    def handle(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(201, json={"id": "p_1", "status": "waiting", "questions": []})
        return httpx.Response(404, json={"detail": "Project not found."})

    result = run_live(BOOKS, httpx.MockTransport(handle))

    assert result.outcome == "error"
    assert result.reason == "The build crashed: ProjectGone."
