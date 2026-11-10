from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app import auth, demand, memory
from app.config import settings
from app.db import UserRow
from app.deps import can_see, check_daily_limit, current_token, current_user, require_admin
from app.intake import apply_answers, record_name, sanitize_ident, understand
from app.jobs import Job, create_job, get_job, recover_interrupted_jobs, run_job
from app.learning import after_approval, before_understanding
from app.models import (
    AnswersRequest,
    Analysis,
    Credentials,
    GenerateRequest,
    GenerateResponse,
    JobPublic,
    LoginResponse,
    MemoryPublic,
    ProjectSummary,
    SessionCreate,
    SessionPublic,
    UserPublic,
)
from app.sessions import Session, create_session, created_at, get_session, list_sessions, save_session
from app.validators import blueprint_problems, validate_requirement


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Runs once when the server starts: builds cut off by a restart are marked failed, not stuck
    recover_interrupted_jobs()
    yield


app = FastAPI(
    title="Backend Builder MVP",
    description="Generate a runnable FastAPI project from a short English description.",
    version="1.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

LOST_SESSION = "This conversation was lost, probably because the builder restarted. Please start again."


def _public_user(user: UserRow) -> UserPublic:
    return UserPublic(id=user.id, email=user.email, role=user.role)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# --------------------------------------------------------------------------- accounts (step 2)


@app.post("/auth/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def register(payload: Credentials) -> UserPublic:
    """Anyone can sign up. New accounts are always normal users; admins are made with app.make_admin."""
    try:
        user = auth.register(payload.email, payload.password)
    except auth.AuthError as error:
        # 409 for "already exists", 400 for a bad email
        code = 409 if "already exists" in str(error) else 400
        raise HTTPException(status_code=code, detail=str(error))
    return _public_user(user)


@app.post("/auth/login", response_model=LoginResponse)
def login(payload: Credentials) -> LoginResponse:
    try:
        token, user = auth.login(payload.email, payload.password)
    except auth.AuthError as error:
        raise HTTPException(status_code=401, detail=str(error))
    return LoginResponse(token=token, user=_public_user(user))


@app.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(token: str = Depends(current_token)) -> None:
    auth.logout(token)


@app.get("/auth/me", response_model=UserPublic)
def me(user: UserRow = Depends(current_user)) -> UserPublic:
    return _public_user(user)


# --------------------------------------------------------------------------- helpers


def _check_request(requirement: str) -> None:
    error = validate_requirement(requirement)
    if error:
        raise HTTPException(status_code=400, detail=error)
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY is missing. Add it to your .env file and restart the generator.",
        )


def _session_or_404(session_id: str, user: UserRow) -> Session:
    session = get_session(session_id)
    # Someone else's session gets the same 404 as a missing one, so outsiders learn nothing
    if not session or not can_see(session.owner_id, user):
        raise HTTPException(status_code=404, detail=LOST_SESSION)
    return session


def _job_or_404(job_id: str, user: UserRow) -> Job:
    job = get_job(job_id)
    if not job or not can_see(job.owner_id, user):
        raise HTTPException(status_code=404, detail="Job not found")
    return job


# --------------------------------------------------------------------------- sessions


@app.post("/sessions", response_model=SessionPublic)
def start_session(payload: SessionCreate, user: UserRow = Depends(current_user)) -> SessionPublic:
    """Understand a request: verdict, draft design, "Not included yet" list and any questions."""
    requirement = payload.requirement.strip()
    _check_request(requirement)
    # Checked after the free checks above, so a bad request does not use up the daily limit
    check_daily_limit(user, "session")
    # Steps 4 and 5: what we remember about this person, and similar designs approved before
    background = before_understanding(user.id, requirement)
    try:
        understanding = understand(requirement, background.text)
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="I couldn't understand that request just now. Please try again, or describe it in a different way.",
        )
    if understanding.verdict != "disallowed":
        # Tell the person what helped, so nothing is used behind their back
        understanding = understanding.model_copy(
            update={"memories_used": background.memories_used, "examples_used": background.examples_used}
        )
    return create_session(requirement, understanding, owner_id=user.id).public()


@app.get("/sessions/{session_id}", response_model=SessionPublic)
def session_status(session_id: str, user: UserRow = Depends(current_user)) -> SessionPublic:
    return _session_or_404(session_id, user).public()


@app.post("/sessions/{session_id}/answers", response_model=SessionPublic)
def answer_questions(
    session_id: str, payload: AnswersRequest, user: UserRow = Depends(current_user)
) -> SessionPublic:
    """Merge answers (or "Skip, use your best guess") into the design."""
    session = _session_or_404(session_id, user)
    if session.status != "needs_answers":
        raise HTTPException(status_code=409, detail="There are no questions waiting for an answer.")
    session.answers = {} if payload.skip else payload.answers
    session.set_understanding(apply_answers(session.requirement, session.understanding, session.answers))
    save_session(session)
    return session.public()


@app.put("/sessions/{session_id}/blueprint", response_model=SessionPublic)
def edit_blueprint(
    session_id: str, blueprint: Analysis, user: UserRow = Depends(current_user)
) -> SessionPublic:
    """Save the user's edits from the confirmation card. Rule checks apply; the card can't break them."""
    session = _session_or_404(session_id, user)
    if session.status == "refused":
        raise HTTPException(status_code=409, detail="This design can't be changed any more.")
    # Tidy every name the person typed ("Expiry Date" → expiry_date), in every record type and link
    cleaned = blueprint.model_copy(
        update={
            "resources": [
                resource.model_copy(
                    update={
                        "name": record_name(resource.name, ""),
                        "plural": record_name(resource.plural, ""),
                        "fields": [
                            f.model_copy(update={
                                "name": sanitize_ident(f.name, ""),
                                "links_to": record_name(f.links_to, "") if f.links_to else None,
                            })
                            for f in resource.fields
                        ],
                    }
                )
                for resource in blueprint.resources
            ]
        }
    )
    problems = blueprint_problems(cleaned)
    if problems:
        raise HTTPException(status_code=400, detail=" ".join(problems))
    if session.suggested is None:
        # Step 4: keep our suggestion from before the first edit, to learn what the person changed
        session.suggested = session.understanding.blueprint
    session.understanding = session.understanding.model_copy(update={"blueprint": cleaned, "questions": []})
    save_session(session)
    return session.public()


@app.post("/sessions/{session_id}/build", response_model=GenerateResponse)
def build_session(
    session_id: str, background: BackgroundTasks, user: UserRow = Depends(current_user)
) -> GenerateResponse:
    """The user clicked "Build this" on the confirmation card."""
    session = _session_or_404(session_id, user)
    blueprint = session.understanding.blueprint
    running = get_job(session.job_id) if session.job_id else None
    # A double-click returns the build already running instead of starting a second one
    if running and running.status in {"queued", "running"}:
        return GenerateResponse(job_id=running.id)
    if session.status == "needs_answers":
        raise HTTPException(status_code=409, detail="Please answer the questions, or click Skip, first.")
    if blueprint is None or session.status == "refused":
        raise HTTPException(status_code=409, detail="There is no design to build for this request.")
    problems = blueprint_problems(blueprint)
    if problems:
        raise HTTPException(status_code=400, detail=" ".join(problems))
    # The job belongs to the session's owner (an admin building it for them does not take it over)
    job = create_job(session.requirement, owner_id=session.owner_id, analysis=blueprint)
    session.job_id = job.id
    save_session(session)
    background.add_task(run_job, job.id)
    # Steps 4 and 5: learn from the approved plan. Added after the build, so it never delays it.
    background.add_task(after_approval, session.id)
    return GenerateResponse(job_id=job.id)


# --------------------------------------------------------------------------- projects (sidebar)


def project_status(session: Session, job: Job | None) -> str:
    """One word for the sidebar pill."""
    if session.status in {"refused", "unsupported"}:
        return "stopped"  # we will not or cannot build it
    if job is None:
        return "waiting"  # waiting for the person: answers, or approving the plan
    if job.status in {"queued", "running"}:
        return "working"
    return "ready" if job.status == "succeeded" else "failed"


@app.get("/projects", response_model=list[ProjectSummary])
def list_projects(user: UserRow = Depends(current_user)) -> list[ProjectSummary]:
    """Your projects, newest first. Only ever your own (admins too: this is "my projects")."""
    summaries = []
    for session in list_sessions(user.id):
        job = get_job(session.job_id) if session.job_id else None
        blueprint = session.understanding.blueprint
        # The design's title once there is one; until then, the start of what they asked for
        name = (job.title if job and job.title else None) or (blueprint.title if blueprint else None)
        name = name or (session.requirement[:40] + ("…" if len(session.requirement) > 40 else ""))
        summaries.append(
            ProjectSummary(
                id=session.id,
                name=name,
                status=project_status(session, job),
                created_at=created_at(session.id) or "",
            )
        )
    return number_repeated_names(summaries)


def number_repeated_names(newest_first: list[ProjectSummary]) -> list[ProjectSummary]:
    """Two projects called "School Management API" would look identical in the sidebar.
    The oldest keeps the plain name; later ones become "School Management API (2)", "(3)"."""
    seen: dict[str, int] = {}
    numbered: list[ProjectSummary] = []
    for summary in reversed(newest_first):  # oldest first, so numbers follow the order they were made
        seen[summary.name] = seen.get(summary.name, 0) + 1
        count = seen[summary.name]
        name = summary.name if count == 1 else f"{summary.name} ({count})"
        numbered.append(summary.model_copy(update={"name": name}))
    return list(reversed(numbered))


# --------------------------------------------------------------------------- memory (step 4)


@app.get("/memories", response_model=list[MemoryPublic])
def list_memories(user: UserRow = Depends(current_user)) -> list[MemoryPublic]:
    """Everything the builder remembers about you, newest first. Only ever your own (admins included)."""
    return [MemoryPublic(id=row.id, fact=row.fact, created_at=row.created_at) for row in memory.list_memories(user.id)]


@app.delete("/memories/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
def forget_memory(memory_id: int, user: UserRow = Depends(current_user)) -> None:
    if not memory.forget(user.id, memory_id):
        # Someone else's memory gets the same answer as a missing one
        raise HTTPException(status_code=404, detail="That memory was not found.")


@app.delete("/memories", status_code=status.HTTP_204_NO_CONTENT)
def forget_all_memories(user: UserRow = Depends(current_user)) -> None:
    memory.forget_all(user.id)


@app.get("/demand-log")
def demand_log(_: UserRow = Depends(require_admin)) -> list[dict]:
    """Every "Not included yet" item users asked for (category, text, date). Admins only."""
    return demand.read_all()


@app.post("/generate", response_model=GenerateResponse)
def generate(
    payload: GenerateRequest, background: BackgroundTasks, user: UserRow = Depends(current_user)
) -> GenerateResponse:
    """Phase 1 one-shot generation: understand and build with the best-guess design, no confirmation card."""
    _check_request(payload.requirement)
    check_daily_limit(user, "generate")
    job = create_job(payload.requirement.strip(), owner_id=user.id)
    background.add_task(run_job, job.id)
    return GenerateResponse(job_id=job.id)


# --------------------------------------------------------------------------- jobs


@app.get("/jobs/{job_id}", response_model=JobPublic)
def job_status(job_id: str, user: UserRow = Depends(current_user)) -> JobPublic:
    return _job_or_404(job_id, user).public()


@app.get("/jobs/{job_id}/download")
def download(job_id: str, user: UserRow = Depends(current_user)) -> FileResponse:
    job = _job_or_404(job_id, user)
    if job.status != "succeeded" or not job.zip_path:
        raise HTTPException(status_code=409, detail="The project is not ready to download yet.")
    filename = f"{(job.title or 'api-project').lower().replace(' ', '-')}.zip"
    return FileResponse(job.zip_path, filename=filename, media_type="application/zip")
