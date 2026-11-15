"""Tests for the live runner (F-12, D-011): a generated project runs as its own server on a local port.

These start real servers (uvicorn) on this computer, so they take a few seconds each. No AI is used."""

import json
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from agent import prompts
from agent.tests.test_prompts import example_files  # pulls the example project out of the builder prompt
from backend import live

# The builder prompt's example: a Notes API with the exact layout the builder writes.
NOTES = example_files(prompts.load_prompt("builder"))

# A tiny API that tells us whether it can see our secret key.
SPY = {
    "app/__init__.py": "",
    "app/main.py": (
        "import os\n"
        "from fastapi import FastAPI\n"
        "app = FastAPI()\n"
        "@app.get('/spy')\n"
        "def spy():\n"
        "    return {'key': os.environ.get('GEMINI_API_KEY')}\n"
    ),
}
BROKEN = {"app/__init__.py": "", "app/main.py": "this is not python\n"}
SLOW_TO_START = {"app/__init__.py": "", "app/main.py": "import time\ntime.sleep(60)\n"}


@pytest.fixture(autouse=True)
def stop_everything_after_each_test():
    yield
    live.stop_all()  # never leave a server running after a test, even a failed one


def get(port: int, path: str) -> tuple[int, object]:
    with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=5) as reply:
        return reply.status, json.loads(reply.read())


def answers(port: int) -> bool:
    try:
        get(port, "/openapi.json")
        return True
    except (urllib.error.URLError, ConnectionError, TimeoutError):
        return False


def test_a_sample_project_answers_a_real_http_call():
    # PLAN's "done when", part 1.
    api = live.start("p_1", NOTES)

    assert get(api.port, "/notes") == (200, [])  # the Notes API's own endpoint, with an empty table
    assert live.is_running("p_1")


def test_its_data_lasts_while_it_runs():
    api = live.start("p_1", NOTES)
    request = urllib.request.Request(
        f"http://127.0.0.1:{api.port}/notes",
        data=json.dumps({"title": "Buy bread"}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=5) as reply:
        assert reply.status == 201

    status, notes = get(api.port, "/notes")
    assert [note["title"] for note in notes] == ["Buy bread"]


def test_starting_one_more_than_the_limit_stops_the_least_recently_used(monkeypatch):
    # PLAN's "done when", part 2. A limit of 2 keeps the test fast; the real limit is MAX_RUNNING.
    monkeypatch.setattr(live, "MAX_RUNNING", 2)
    first = live.start("p_1", NOTES)
    live.start("p_2", NOTES)
    live.touch("p_1")  # p_1 was used just now, so p_2 is now the one nobody used for longest

    live.start("p_3", NOTES)

    assert live.is_running("p_1") and live.is_running("p_3")
    assert not live.is_running("p_2")
    assert answers(first.port)


def test_starting_a_running_api_again_reuses_it():
    first = live.start("p_1", NOTES)
    again = live.start("p_1", NOTES)

    assert again.port == first.port
    assert again.process.pid == first.process.pid  # no second server was started


def test_stop_ends_the_server_and_deletes_its_folder():
    api = live.start("p_1", NOTES)
    folder = Path(api.folder.name)

    live.stop("p_1")

    assert not live.is_running("p_1")
    assert api.process.poll() is not None  # poll() gives the exit code once the process has ended
    assert not folder.exists()
    assert not answers(api.port)


def test_stopping_an_api_that_is_not_running_does_nothing():
    live.stop("p_never_started")  # no error


def test_idle_apis_are_stopped(monkeypatch):
    live.start("p_1", NOTES)
    monkeypatch.setattr(live, "IDLE_SECONDS", 0)  # everything counts as idle now

    live.stop_idle()

    assert not live.is_running("p_1")


def test_a_project_that_cannot_start_gives_a_plain_error_and_leaves_nothing_behind():
    with pytest.raises(live.LiveError, match="The API could not start"):
        live.start("p_1", BROKEN)

    assert not live.is_running("p_1")
    assert live.running == {}


def test_a_project_that_takes_too_long_to_start_is_stopped(monkeypatch):
    monkeypatch.setattr(live, "START_TIMEOUT_SECONDS", 2)

    with pytest.raises(live.LiveError, match="did not answer within 2 seconds"):
        live.start("p_1", SLOW_TO_START)

    assert live.running == {}


def test_secret_keys_are_hidden_from_the_live_api(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "secret-for-this-test")

    api = live.start("p_1", SPY)

    assert get(api.port, "/spy") == (200, {"key": None})


def test_an_unsafe_file_name_is_refused():
    with pytest.raises(live.LiveError, match="Unsafe file name"):
        live.start("p_1", {**NOTES, "../escape.py": "x = 1\n"})

    assert live.running == {}


def test_two_starts_at_the_same_moment_never_go_over_the_limit(monkeypatch):
    import threading

    monkeypatch.setattr(live, "MAX_RUNNING", 1)
    started = []

    def start(project_id):
        started.append(live.start(project_id, NOTES))

    threads = [threading.Thread(target=start, args=(f"p_{n}",)) for n in (1, 2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(live.running) == 1
    # The one that was pushed out must really be stopped, not left running in the background.
    assert sum(api.process.poll() is None for api in started) == 1


def test_an_api_that_crashed_is_started_again():
    first = live.start("p_1", NOTES)
    first.process.kill()  # pretend it crashed
    first.process.wait()

    again = live.start("p_1", NOTES)

    assert again.process.pid != first.process.pid
    assert not Path(first.folder.name).exists()  # the crashed one's folder was cleaned up, not leaked
    assert get(again.port, "/notes") == (200, [])
