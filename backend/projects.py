"""Project endpoints (W-5). The shapes follow docs/api-contract.md."""

import asyncio
import io
import math
import os
import re
import zipfile
from collections.abc import AsyncIterator, Callable
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from fastapi.sse import EventSourceResponse
from pydantic import BaseModel, ConfigDict, Field

from agent import llm
from agent.prompts import builder_instruction
from agent.retry import build_with_retries
from agent.takehome import takehome_files
from backend import live
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

# Stop a running build (F-18). Each build runs as its own asyncio "task" (a job Python can cancel);
# `building` keeps its handle until it ends. `stop_asked` remembers who the person asked to stop, so a
# build cancelled for another reason (the server shutting down) is not reported as "you stopped it".
building: dict[str, asyncio.Task[BuildResult]] = {}
stop_asked: set[str] = set()
STOPPED_TEXT = "You stopped this build. Nothing was kept."

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
    # The live API (F-13, D-011). Only for a ready project; null before that.
    api_url: str | None = None  # e.g. "/apis/p_1"; its Swagger page is api_url + "/docs"
    live_status: str | None = None  # "running" or "sleeping" (stopped to save memory, or the server restarted)


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


# The agent's first sentence names what it builds (builder.md step 1), e.g. "Building a Reading Club Library API with...".
# The name: words starting with a capital letter or a digit, ending in "API". Only letters, digits, spaces and
# the marks - & ' in between, so a long sentence can't become the name.
API_NAME = re.compile(r"\b(?:[Bb]uild|[Bb]uilding)\s+(?:an?\s+|the\s+)?([A-Z0-9][\w&'\- ]{0,58}?\sAPI)\b")


def api_name(text: str) -> str | None:
    # "Building a Reading Club Library API with a books table." -> "Reading Club Library API"; None if there is no name.
    match = API_NAME.search(text)
    return match.group(1).strip() if match else None


def display_name(project: dict[str, str]) -> str:
    # The API's own name once the agent has said it; until then (or after a refusal), the start of the request.
    return project.get("name") or short_name(project["request"])


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
    # A refused request's name comes on its final event ("Church Website (not built)", backend/builder.py).
    if "name" not in projects[project_id] and isinstance(event.get("name"), str):
        projects[project_id]["name"] = str(event["name"])
    # The agent's own words may name the API. Only the first name counts, so a later sentence can't rename it.
    step = event.get("step")
    if "name" not in projects[project_id] and isinstance(step, dict) and step.get("kind") == "Thinking":
        name = api_name(str(step.get("text", "")))
        if name:
            projects[project_id]["name"] = name


def failed(project_id: str, reason: str) -> None:
    # End the build with one plain sentence. A final status also ends the live stream.
    add_event(project_id, {"status": "failed", "step": {"kind": "Result", "text": reason, "state": "failed", "phase": "finishing"}})


def stopped(project_id: str) -> None:
    # The person pressed Stop (F-18). Same shape as failed(), with its own status word.
    add_event(project_id, {"status": "stopped", "step": {"kind": "Result", "text": STOPPED_TEXT, "state": "failed", "phase": "finishing"}})


def report_to(project_id: str) -> Callable[[dict[str, object]], None]:
    # Where the agent's steps go. After Stop, a step that was already on its way is dropped, so nothing
    # can appear on the timeline after "You stopped this build".
    def report(event: dict[str, object]) -> None:
        if project_id not in stop_asked:
            add_event(project_id, event)

    return report


async def run_build(project_id: str, request: str) -> None:
    # The build job (W-9): runs after POST /projects has already answered.
    if project_id in stop_asked:
        stopped(project_id)  # Stop was pressed before the build even began: don't start it
        return
    model = os.environ.get("LLM_MODEL", "")
    if not model:
        # With no model name, ADK quietly picks its own default, so we stop and say so instead.
        failed(project_id, "The server has no AI model set (LLM_MODEL).")
        return
    # Until F-2 adds a plan the person approves, the AI gets the request in the person's own words.
    message = f"There is no plan yet. Build a small API for this request:\n\n{request}"
    # Opei's retry loop (F-4) around the builder (W-3). Every step it reports goes into this project's diary.
    # It runs as its own task, kept in `building`, so POST /projects/{id}/stop can cancel it.
    job = asyncio.create_task(
        build_with_retries(
            message,
            builder_instruction(),
            model,
            report=report_to(project_id),
            backup_model=llm.backup_model(),  # only used if the main model is busy 3 times (D-018)
        )
    )
    building[project_id] = job
    try:
        result = await job
    except asyncio.CancelledError:
        # CancelledError is not an Exception, so the safety net below never hides it.
        if project_id not in stop_asked:
            raise  # not the person's Stop (e.g. the server is shutting down): let the cancel carry on
        stopped(project_id)
        return
    except Exception:
        # Last safety net: an error we didn't expect (e.g. no API key). Without this the project stays
        # "working" forever and the screen spins. A plain sentence is better than a spinner.
        failed(project_id, "Something went wrong on our side. Please try again.")
        return
    finally:
        building.pop(project_id, None)  # the job is over either way
    if project_id in stop_asked:
        # Stop came in the very moment the build finished: the person asked to stop, so honour it.
        stopped(project_id)
        return
    results[project_id] = result
    if results[project_id].status == "ready":
        await start_live_api(project_id)  # D-011: once the tests pass, the API goes live at its link


async def start_live_api(project_id: str) -> None:
    # live.start waits (up to 30 s) for the API to answer. to_thread runs that wait on the side,
    # so the server keeps answering everyone else meanwhile.
    try:
        await asyncio.to_thread(live.start, project_id, results[project_id].files, f"/apis/{project_id}")
    except live.LiveError:
        pass  # the build is still ready and downloadable; the page shows "sleeping" and offers Wake it up


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


@router.post("/projects/{project_id}/stop", status_code=202)
async def stop_project(project: dict[str, str] = Depends(find_project)) -> dict[str, str]:
    # Stop a running build (F-18). 202 Accepted = "asked; it happens in a moment": the build's own
    # job writes the "stopped" event, and the live stream shows it and hangs up.
    # async def: this runs on the server's own event loop, the only place a task may be cancelled from.
    if project["status"] in FINAL_STATUSES:
        raise HTTPException(status_code=409, detail="This build has already finished, so there is nothing to stop.")
    stop_asked.add(project["id"])  # pressing Stop twice is harmless: a set holds each id once
    job = building.get(project["id"])
    if job is not None:
        # cancel() raises CancelledError inside the build at its next "await" (an AI call, a wait between
        # tries). A test run already going finishes first, because it does not stop at an await.
        job.cancel()
    # No job yet means the build has not begun: run_build sees stop_asked and ends it as stopped.
    return {"status": "stopping"}


@router.get("/projects", response_model=list[ProjectSummary])
def list_projects() -> list[ProjectSummary]:
    # Newest first: sort by updated_at, biggest (latest) time first. This works on the text because
    # ISO 8601 times are written biggest part first (year, month, day, hour...), so text order = time order.
    newest_first = sorted(projects.values(), key=lambda project: project["updated_at"], reverse=True)
    return [
        ProjectSummary(
            id=project["id"],
            name=display_name(project),
            status=project["status"],
            updated_at=project["updated_at"],
        )
        for project in newest_first
    ]


# {project_id} in the path is a placeholder: FastAPI hands whatever is there to find_project.
# Depends(find_project) means "run find_project first and give me its answer" (or stop with 404).
@router.get("/projects/{project_id}", response_model=ProjectResponse)
def get_project(project: dict[str, str] = Depends(find_project)) -> ProjectResponse:
    answer = ProjectResponse(id=project["id"], name=display_name(project), status=project["status"])
    result = results.get(project["id"])  # None while the build is still going
    if result is not None:
        answer.file_count = len(result.files)
        # Size of all files together, rounded UP to whole kilobytes (1 KB = 1024 bytes), so a tiny project shows 1, not 0.
        answer.size_kb = math.ceil(sum(len(text.encode()) for text in result.files.values()) / 1024)
        answer.tests_passed, answer.tests_total = count_tests(result.test_output)
        if project["status"] == "ready":
            answer.api_url = f"/apis/{project['id']}"
            answer.live_status = "running" if live.is_running(project["id"]) else "sleeping"
    return answer


def zip_name(project: dict[str, str]) -> str:
    # The take-home file is named after the API: "Clinic Appointment API" -> "clinic-appointment-api.zip".
    # Only a-z, 0-9 and "-" are kept, so the name is safe on every computer; the frontend uses the same rule.
    words = re.findall(r"[a-z0-9]+", display_name(project).lower())
    slug = "-".join(words)[:60].strip("-")
    return f"{slug or project['id']}.zip"


def zip_files(files: dict[str, str]) -> bytes:
    # Pack the project into a zip in memory (BytesIO is a file that lives in RAM), so no temp file is left behind.
    buffer = io.BytesIO()
    # ZIP_DEFLATED = compress the files (the default, ZIP_STORED, only puts them side by side).
    # Add the run files (F-6: Dockerfile, HOW_TO_RUN.md, ...). Written second, the project's own files win
    # if the agent happened to write a file with the same name.
    with_run_files = {**takehome_files(), **files}
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, text in with_run_files.items():
            # The names are already safe: the agent's write_file tool refuses "../" and drive paths (W-1).
            archive.writestr(name, text)
    return buffer.getvalue()


@router.get("/projects/{project_id}/download")
def download_project(project: dict[str, str] = Depends(find_project)) -> Response:
    # The take-home zip (F-5). Only for a ready project: a failed build's files have failing tests.
    result = results.get(project["id"])
    if project["status"] != "ready" or result is None:
        # 409 Conflict = "not at this step yet" (docs/api-contract.md).
        raise HTTPException(status_code=409, detail="The API is not ready yet, so there is nothing to download.")
    # "attachment" tells the browser to save the file instead of showing it, under this name.
    headers = {"Content-Disposition": f'attachment; filename="{zip_name(project)}"'}
    return Response(content=zip_files(result.files), media_type="application/zip", headers=headers)


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


# The most a call to a live API may send or get back. A generated API only handles small JSON, and a
# bigger reply would sit in our small server's memory (D-011: caps on request and output size).
MAX_PASS_THROUGH_BYTES = 1_000_000  # 1 MB
PASS_THROUGH_TIMEOUT_SECONDS = 30


def ready_files(project: dict[str, str]) -> dict[str, str]:
    # The files of a ready project; 409 for any other status (the same rule as the download).
    result = results.get(project["id"])
    if project["status"] != "ready" or result is None:
        raise HTTPException(status_code=409, detail="The API is not ready yet.")
    return result.files


@router.post("/projects/{project_id}/wake", status_code=202)
async def wake_project(project: dict[str, str] = Depends(find_project)) -> dict[str, str]:
    # Start a sleeping API again from its stored files (D-011). On a running one, live.start does nothing new.
    await start_or_explain(project)
    return {"live_status": "running"}


async def start_or_explain(project: dict[str, str]) -> int:
    # Start the project's live API (or find the running one) and give back its port.
    # If it can't start, stop with 503 and the runner's message, which is already a plain sentence.
    files = ready_files(project)
    try:
        api = await asyncio.to_thread(live.start, project["id"], files, f"/apis/{project['id']}")
    except live.LiveError as error:
        raise HTTPException(status_code=503, detail=str(error))
    return api.port


# Every method, and any path after /apis/{id}/ ({path:path} also matches "a/b/c").
# include_in_schema=False: these calls belong to the generated API, not to our own API's description.
@router.api_route(
    "/apis/{project_id}/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    include_in_schema=False,
)
async def pass_through(path: str, request: Request, project: dict[str, str] = Depends(find_project)) -> Response:
    ready_files(project)  # 409 if the project isn't ready
    await asyncio.to_thread(live.stop_idle)  # a good moment to put unused APIs to sleep
    port = live.port_of(project["id"])
    if port is None:
        # Asleep: wake it now instead of answering "asleep". A page may still show the link from
        # before the API went to sleep (seen live on Render), and the person should just get their API.
        port = await start_or_explain(project)
    live.touch(project["id"])  # it is being used, so it is not idle

    body = await request.body()
    if len(body) > MAX_PASS_THROUGH_BYTES:
        raise HTTPException(status_code=413, detail="The request is too big.")
    # Pass on the method, the path WITHOUT "/apis/p_1" (the API was started with that as its root path),
    # the query (?a=1), the body and its content type. Nothing else: no cookies or other headers of ours.
    headers = {"content-type": request.headers["content-type"]} if "content-type" in request.headers else {}
    try:
        async with httpx.AsyncClient(timeout=PASS_THROUGH_TIMEOUT_SECONDS) as http:
            reply = await http.request(
                request.method,
                f"http://127.0.0.1:{port}/{path}",
                params=request.query_params,
                content=body,
                headers=headers,
            )
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="The API did not answer. Try again, or wake it up.")
    if len(reply.content) > MAX_PASS_THROUGH_BYTES:
        raise HTTPException(status_code=502, detail="The API's answer is too big to pass on.")
    # Its own status and body come back unchanged, so its own errors (like 404) reach the person as they are.
    return Response(content=reply.content, status_code=reply.status_code, media_type=reply.headers.get("content-type"))
