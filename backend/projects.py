"""Project endpoints (W-5). The shapes follow docs/api-contract.md."""

import asyncio
import math
import os
import re
from collections.abc import AsyncIterator
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.sse import EventSourceResponse
from pydantic import BaseModel, ConfigDict, Field

from agent.prompts import builder_instruction
from agent.retry import build_with_retries
from backend.builder import BuildResult

# A router is a group of endpoints; main.py plugs it into the app.
router = APIRouter(tags=["projects"])

# Projects are kept in memory for now, so they are lost when the server restarts (D-013).
projects: dict[str, dict[str, str]] = {}

# Each project's diary: every event that happened to it, in order.
# The agent (W-3) will add to it with add_event(); the live stream reads from it.
events: dict[str, list[dict[str, object]]] = {}

# What each finished build handed back (its files and our own test output), for GET /projects/{id}.
results: dict[str, BuildResult] = {}

# When a project reaches one of these, nothing more will happen, so the stream hangs up.
FINAL_STATUSES = {"ready", "failed", "stopped"}

# Until a plan gives a project its real name (F-2), the sidebar shows the start of the request, cut to this length.
NAME_LENGTH = 40


class StartRequest(BaseModel):
    # Trim spaces from the start and end of text BEFORE the length is checked,
    # so "   " becomes "" and is refused, and " A bookshop " is saved as "A bookshop".
    model_config = ConfigDict(str_strip_whitespace=True)

    # The user's plain-English description of the API they want.
    # Field(...) sets the allowed length (1 to 2000 characters, as in the contract).
    # FastAPI checks it before our function runs, and answers 422 if it's wrong.
    request: str = Field(min_length=1, max_length=2000)


class Question(BaseModel):
    id: str
    text: str
    why: str
    options: list[str]


class StartResponse(BaseModel):
    id: str
    status: str
    questions: list[Question]  # empty for now: the AI that asks questions isn't built yet


class ProjectResponse(BaseModel):
    # The contract's fields that exist today. run_command, api_url and live_status come with F-5 and F-13.
    id: str
    name: str
    status: str
    # None (null in JSON) until a build has finished: the page hides what it doesn't have.
    file_count: int | None = None
    size_kb: int | None = None
    tests_passed: int | None = None
    tests_total: int | None = None


class ProjectSummary(BaseModel):
    # One line in the sidebar (W-8). Same fields as the contract's GET /projects.
    id: str
    name: str
    status: str
    updated_at: str  # when the project last changed, as an ISO 8601 date and time, e.g. 2026-11-11T09:30:00+00:00


def now() -> str:
    # The current time as text. UTC (world time), so it means the same on every computer and server.
    return datetime.now(timezone.utc).isoformat()


def short_name(request: str) -> str:
    # A stand-in name until F-2's plan gives a real one, e.g. "A bookshop where I can add…".
    if len(request) <= NAME_LENGTH:
        return request
    cut = request[:NAME_LENGTH]
    cut = cut.rsplit(" ", 1)[0]  # drop the last, half-cut word: split at the last space, keep the left part
    return cut.rstrip(",.;:") + "…"  # tidy a trailing comma or full stop, and add "…" to show it was cut


def find_project(project_id: str) -> dict[str, str]:
    # Shared by every endpoint that needs one project, so the "not found" rule lives in one place.
    project = projects.get(project_id)  # .get gives None instead of crashing when the id isn't there
    if project is None:
        # HTTPException stops here and sends this status code and message back to the caller.
        raise HTTPException(status_code=404, detail="Project not found.")
    return project


def add_event(project_id: str, event: dict[str, object]) -> None:
    # Write one new entry in the project's diary. The agent (W-3) will call this as it works.
    # An unknown id raises KeyError on purpose: only our own code calls this, always with a real id,
    # so a KeyError here means a bug in our code, and it should be loud.
    events[project_id].append(event)
    status = event.get("status")
    if isinstance(status, str):  # keep the project's current status up to date too
        projects[project_id]["status"] = status
    projects[project_id]["updated_at"] = now()  # any new event counts as a change, so the sidebar moves it up


def failed(project_id: str, reason: str) -> None:
    # End the build with one plain sentence. A final status also ends the live stream.
    add_event(project_id, {"status": "failed", "step": {"kind": "Result", "text": reason, "state": "failed"}})


async def run_build(project_id: str, request: str) -> None:
    # The build job (W-9): runs after POST /projects has already answered.
    model = os.environ.get("LLM_MODEL", "")
    if not model:
        # With no model name, ADK quietly picks its own default, so we stop and say so instead.
        failed(project_id, "The server has no AI model set (LLM_MODEL).")
        return
    # Until F-2 adds a plan the person approves, the AI gets the request in the person's own words.
    message = f"There is no plan yet. Build a small API for this request:\n\n{request}"
    try:
        # Opei's retry loop (F-4) around the builder (W-3). Every step it reports goes into this project's diary.
        results[project_id] = await build_with_retries(
            message, builder_instruction(), model, report=lambda event: add_event(project_id, event)
        )
    except Exception:
        # Last safety net: an error we didn't expect (e.g. no API key). Without this the project stays
        # "working" forever and the screen spins. A plain sentence is better than a spinner.
        failed(project_id, "Something went wrong on our side. Please try again.")


@router.post("/projects", status_code=201, response_model=StartResponse)
def start_project(body: StartRequest, background: BackgroundTasks) -> StartResponse:
    project_id = f"p_{len(projects) + 1}"  # p_1, p_2, ...
    projects[project_id] = {
        "id": project_id,
        "request": body.request,
        "status": "waiting",
        "updated_at": now(),
    }
    events[project_id] = [{"status": "waiting"}]  # the diary's first entry
    # Start the build AFTER this reply is sent: the page gets the id at once and opens the live stream,
    # instead of waiting minutes for an answer. Until F-2 adds approve, sending a request starts the build.
    background.add_task(run_build, project_id, body.request)
    return StartResponse(id=project_id, status="waiting", questions=[])


@router.get("/projects", response_model=list[ProjectSummary])
def list_projects() -> list[ProjectSummary]:
    # Newest first: sort by updated_at, biggest (latest) time first. This works on the text because
    # ISO 8601 times are written biggest part first (year, month, day, hour...), so text order = time order.
    newest_first = sorted(projects.values(), key=lambda project: project["updated_at"], reverse=True)
    return [
        ProjectSummary(
            id=project["id"],
            name=short_name(project["request"]),
            status=project["status"],
            updated_at=project["updated_at"],
        )
        for project in newest_first
    ]


# {project_id} in the path is a placeholder: FastAPI hands whatever is there to find_project.
# Depends(find_project) means "run find_project first and give me its answer" (or stop with 404).
@router.get("/projects/{project_id}", response_model=ProjectResponse)
def get_project(project: dict[str, str] = Depends(find_project)) -> ProjectResponse:
    answer = ProjectResponse(id=project["id"], name=short_name(project["request"]), status=project["status"])
    result = results.get(project["id"])  # None while the build is still going
    if result is not None:
        answer.file_count = len(result.files)
        # Size of all files together, rounded UP to whole kilobytes (1 KB = 1024 bytes), so a tiny project shows 1, not 0.
        answer.size_kb = math.ceil(sum(len(text.encode()) for text in result.files.values()) / 1024)
        answer.tests_passed, answer.tests_total = count_tests(result.test_output)
    return answer


def count_tests(output: str) -> tuple[int, int]:
    # pytest's last line looks like "1 failed, 4 passed in 0.31s". Read the number in front of each word.
    lines = output.strip().splitlines()
    last = lines[-1] if lines else ""  # no output at all: the tests never ran
    passed = sum(int(number) for number in re.findall(r"(\d+) passed", last))
    not_passed = sum(int(number) for number in re.findall(r"(\d+) (?:failed|errors?)", last))
    return passed, passed + not_passed


# The live stream (SSE). Each `yield` sends one message to the browser straight away.
# We use Depends here too: the 404 check must happen BEFORE the stream starts,
# because once streaming has begun the status code (200) has already been sent.
@router.get("/projects/{project_id}/events", response_class=EventSourceResponse)
async def stream_events(project: dict[str, str] = Depends(find_project)) -> AsyncIterator[dict[str, object]]:
    diary = events[project["id"]]
    sent = 0  # how many diary entries this browser has already received
    while True:
        # Send everything new. The first time round that is the whole history,
        # so a browser that reconnects still sees the full timeline (the contract asks for this).
        while sent < len(diary):
            yield diary[sent]
            sent += 1
        if project["status"] in FINAL_STATUSES:
            return  # nothing more will happen: hang up
        # Wait half a second, then look for news again. "await" lets the server serve others meanwhile.
        await asyncio.sleep(0.5)
