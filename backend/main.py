"""The platform server: the front door that the web UI talks to.

Run from the repo root:  uvicorn backend.main:app --reload
Interactive docs:        http://localhost:8000/docs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.config import allowed_origins
from backend.projects import router as projects_router

app = FastAPI(
    title="Mesora API Builder",
    description="Turns a plain-English request into a tested FastAPI project.",
    version="0.1.0",
)

# CORS: browsers only let a web page call a server if the server says that page is allowed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins(),
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

# Plug in the project endpoints from backend/projects.py.
app.include_router(projects_router)


class Health(BaseModel):
    status: str


@app.get("/health", response_model=Health, tags=["system"])
def health() -> Health:
    """Is the server awake? The web UI calls this first so it can show a "waking up" message."""
    return Health(status="ok")
