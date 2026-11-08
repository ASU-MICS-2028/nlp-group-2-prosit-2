"""The platform server: the front door that the web UI talks to.

Run from the repo root:  uvicorn backend.main:app --reload
Interactive docs:        http://localhost:8000/docs
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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


# When input breaks a rule (for example an empty request), FastAPI normally sends back a list of
# technical details. The contract (docs/api-contract.md) promises one plain sentence instead,
# so this function turns that list into a sentence the web page can show as it is.
@app.exception_handler(RequestValidationError)
def plain_validation_error(request: Request, error: RequestValidationError) -> JSONResponse:
    # FastAPI always passes `request` to error handlers; we don't need it here, but it must be in the list.
    first = error.errors()[0]  # show only the first problem, to keep the message short
    field = first["loc"][-1]  # the name of the field with the problem, e.g. "request"
    return JSONResponse(status_code=422, content={"detail": f"Invalid {field}: {first['msg']}."})


class Health(BaseModel):
    status: str


@app.get("/health", response_model=Health, tags=["system"])
def health() -> Health:
    """Is the server awake? The web UI calls this first so it can show a "waking up" message."""
    return Health(status="ok")
