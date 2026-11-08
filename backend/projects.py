"""Project endpoints (W-5). The shapes follow docs/api-contract.md."""

from fastapi import APIRouter, HTTPException
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


class ProjectResponse(BaseModel):
    # Only what exists today. The contract's other fields (name, file_count, api_url, ...)
    # are added once the agent can actually fill them in.
    id: str
    status: str


# {project_id} in the path is a placeholder: FastAPI hands whatever is there to the function.
@router.get("/projects/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str) -> ProjectResponse:
    project = projects.get(project_id)  # .get gives None instead of crashing when the id isn't there
    if project is None:
        # HTTPException stops here and sends this status code and message back to the caller.
        raise HTTPException(status_code=404, detail="Project not found.")
    return ProjectResponse(id=project["id"], status=project["status"])


