"""Project endpoints (W-5). The shapes follow docs/api-contract.md."""

from fastapi import APIRouter
from pydantic import BaseModel

# A router is a group of endpoints; main.py plugs it into the app.
router = APIRouter(tags=["projects"])

# Projects are kept in memory for now, so they are lost when the server restarts.
projects: dict[str, dict[str, str]] = {}


class StartRequest(BaseModel):
    request: str  # the user's plain-English description of the API they want


class Question(BaseModel):
    id: str
    text: str
    why: str
    options: list[str]


class StartResponse(BaseModel):
    id: str
    status: str
    questions: list[Question]  # empty for now: the AI that asks questions isn't built yet


@router.post("/projects", status_code=201, response_model=StartResponse)
def start_project(body: StartRequest) -> StartResponse:
    project_id = f"p_{len(projects) + 1}"  # p_1, p_2, ...
    projects[project_id] = {"id": project_id, "request": body.request, "status": "waiting"}
    return StartResponse(id=project_id, status="waiting", questions=[])
