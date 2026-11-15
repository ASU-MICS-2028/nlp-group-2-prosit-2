"""Live runner (F-12, D-011): run a generated project as its own server, so people can really call it.

Each live API is a separate uvicorn process in its own throwaway folder, on a free port of THIS computer
(127.0.0.1, not reachable from outside). F-13 passes calls from /apis/{id}/... through to that port.

Limits, because the free server is small (512 MB on Render):
- at most MAX_RUNNING at once: starting one more stops the one nobody has used for the longest time;
- an API nobody has used for IDLE_SECONDS is stopped ("sleeping"); its files are kept by the caller,
  so it can be started again, but its data (app.db, inside the folder) is gone;
- an API that does not answer within START_TIMEOUT_SECONDS is stopped with a plain error.
"""

import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from backend.runner import is_inside, minimal_environment

MAX_RUNNING = 3  # D-011 starts with 3; measure memory on Render before trusting it
IDLE_SECONDS = 10 * 60
START_TIMEOUT_SECONDS = 30


class LiveError(Exception):
    """The API could not be started. The message is a plain sentence, safe to show to a person."""


@dataclass
class LiveApi:
    project_id: str
    port: int
    process: subprocess.Popen
    folder: tempfile.TemporaryDirectory
    last_used: float  # time.monotonic() of the last call; the idle and limit rules read it


# The APIs running now, by project id.
running: dict[str, LiveApi] = {}

# Two requests at the same moment could both see "2 running" and both start one, going over the limit.
# The lock lets only one start or stop happen at a time. (A start waits for its API to answer while
# holding it, so a second start waits too; that is fine for a demo with a handful of people.)
lock = threading.Lock()


def free_port() -> int:
    # Ask the system for any free port: binding to port 0 means "you choose". Then let it go again for uvicorn.
    # (Another program could take it in between; on our small server that is very unlikely.)
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def answers(port: int) -> bool:
    # Every FastAPI app serves /openapi.json, so a reply there means the API is up.
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/openapi.json", timeout=1):
            return True
    except (urllib.error.URLError, ConnectionError, TimeoutError):
        return False


def write_project(folder: Path, files: dict[str, str]) -> None:
    for name, content in files.items():
        if not is_inside(folder, name):  # the same "../" check as the test runner
            raise LiveError(f"Unsafe file name: {name}")
        target = folder / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)


def end_process(api: LiveApi) -> None:
    # Ask the server to stop; if it hasn't stopped after 5 seconds, force it.
    if api.process.poll() is None:  # poll() is None while the process is still running
        api.process.terminate()
        try:
            api.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            api.process.kill()
            api.process.wait()
    # Only now delete the folder: on Windows a running process keeps its files (like app.db) locked.
    api.folder.cleanup()


def start(project_id: str, files: dict[str, str], root_path: str = "") -> LiveApi:
    """Start this project's API, or give back the one already running. Raises LiveError if it can't start.

    root_path is the address our backend shows it under (F-13: "/apis/p_1"). The API then tells its own
    Swagger page to load "/apis/p_1/openapi.json" and send "Try it out" calls there, instead of to our backend.
    """
    with lock:
        api = running.get(project_id)
        if api is not None and api.process.poll() is None:
            api.last_used = time.monotonic()
            return api
        if api is not None:  # it had crashed: delete its old folder, then start afresh
            end_process(running.pop(project_id))

        stop_idle_locked()
        while len(running) >= MAX_RUNNING:
            # min(..., key=...) picks the API with the smallest last_used: the one unused for longest.
            oldest = min(running.values(), key=lambda other: other.last_used)
            end_process(running.pop(oldest.project_id))

        # ignore_cleanup_errors: if Windows still holds a file for a moment, don't crash; it is a temp folder.
        folder = tempfile.TemporaryDirectory(prefix="live_", ignore_cleanup_errors=True)
        try:
            write_project(Path(folder.name), files)
        except LiveError:
            folder.cleanup()
            raise

        port = free_port()
        command = [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)]
        if root_path:
            command += ["--root-path", root_path]
        process = subprocess.Popen(
            command,  # the same Python as our server (sys.executable), so uvicorn and FastAPI are there
            cwd=folder.name,  # the project's folder, so "app.main" and its app.db are found there
            env=minimal_environment(),  # no API key (backend/runner.py)
            # Throw its log away. A pipe nobody reads would fill up and freeze the API.
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        api = LiveApi(project_id, port, process, folder, last_used=time.monotonic())

        deadline = time.monotonic() + START_TIMEOUT_SECONDS
        while not answers(port):
            if process.poll() is not None:  # it ended by itself: broken code, a missing import, ...
                end_process(api)
                raise LiveError("The API could not start. Its code has a problem.")
            if time.monotonic() > deadline:
                end_process(api)
                raise LiveError(f"The API did not answer within {START_TIMEOUT_SECONDS} seconds, so it was stopped.")
            time.sleep(0.2)

        running[project_id] = api
        return api


def touch(project_id: str) -> None:
    # A call went through to this API (F-13 calls this), so it is not idle.
    api = running.get(project_id)
    if api is not None:
        api.last_used = time.monotonic()


def port_of(project_id: str) -> int | None:
    # The port of a running API, or None. .get(): it may have been stopped a moment ago by another request.
    api = running.get(project_id)
    return api.port if api is not None and api.process.poll() is None else None


def is_running(project_id: str) -> bool:
    api = running.get(project_id)
    return api is not None and api.process.poll() is None


def stop(project_id: str) -> None:
    with lock:
        api = running.pop(project_id, None)
        if api is not None:
            end_process(api)


def stop_idle_locked() -> None:
    # The caller must already hold the lock.
    now = time.monotonic()
    for api in list(running.values()):  # list(...): we remove items while going through them
        if now - api.last_used >= IDLE_SECONDS:
            end_process(running.pop(api.project_id))


def stop_idle() -> None:
    with lock:
        stop_idle_locked()


def stop_all() -> None:
    # For tests and for the server shutting down: no live API is left running.
    with lock:
        for project_id in list(running):
            end_process(running.pop(project_id))
