"""Project endpoints (W-5). The shapes follow docs/api-contract.md."""

import asyncio
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.sse import EventSourceResponse
from pydantic import BaseModel, Field

# A router is a group of endpoints; main.py plugs it into the app.
router = APIRouter(tags=["projects"])

# Projects are kept in memory for now, so they are lost when the server restarts (D-013).
projects: dict[str, dict[str, str]] = {}

# Each project's diary: every event that happened to it, in order.
# The agent (W-3) will add to it with add_event(); the live stream reads from it.
events: dict[str, list[dict[str, object]]] = {}

# When a project reaches one of these, nothing more will happen, so the stream hangs up.
FINAL_STATUSES = {"ready", "failed", "stopped"}


class StartRequest(BaseModel):
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
    # Only what exists today. The contract's other fields (name, file_count, api_url, ...)
    # are added once the agent can actually fill them in.
    id: str
    status: str


def find_project(project_id: str) -> dict[str, str]:
    # Shared by every endpoint that needs one project, so the "not found" rule lives in one place.
    project = projects.get(project_id)  # .get gives None instead of crashing when the id isn't there
    if project is None:
        # HTTPException stops here and sends this status code and message back to the caller.
        raise HTTPException(status_code=404, detail="Project not found.")
    return project


def add_event(project_id: str, event: dict[str, object]) -> None:
    # Write one new entry in the project's diary. The agent (W-3) will call this as it works.
    events[project_id].append(event)
    status = event.get("status")
    if isinstance(status, str):  # keep the project's current status up to date too
        projects[project_id]["status"] = status


@router.post("/projects", status_code=201, response_model=StartResponse)
def start_project(body: StartRequest) -> StartResponse:
    project_id = f"p_{len(projects) + 1}"  # p_1, p_2, ...
    projects[project_id] = {"id": project_id, "request": body.request, "status": "waiting"}
    events[project_id] = [{"status": "waiting"}]  # the diary's first entry
    return StartResponse(id=project_id, status="waiting", questions=[])


# {project_id} in the path is a placeholder: FastAPI hands whatever is there to find_project.
# Depends(find_project) means "run find_project first and give me its answer" (or stop with 404).
@router.get("/projects/{project_id}", response_model=ProjectResponse)
def get_project(project: dict[str, str] = Depends(find_project)) -> ProjectResponse:
    return ProjectResponse(id=project["id"], status=project["status"])


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
