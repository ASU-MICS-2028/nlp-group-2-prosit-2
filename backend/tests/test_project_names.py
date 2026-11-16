"""Project names (after E-4): a short API name taken from the agent's first sentence, instead of the typed request."""

import pytest
from fastapi.testclient import TestClient

from backend import projects
from backend.main import app
from backend.projects import add_event, api_name

client = TestClient(app)


@pytest.fixture(autouse=True)
def no_real_builds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(projects, "run_build", lambda project_id, request: None)  # never call the AI in tests


@pytest.mark.parametrize(
    ("sentence", "name"),
    [
        ("Building a Reading Club Library API with a books table and 5 endpoints.", "Reading Club Library API"),
        ("Building a School Management System API with students, teachers and classes.", "School Management System API"),
        ("Building an Online Shop API with products, customers and orders tables.", "Online Shop API"),
        ("Building a To-Do List API with a tasks table.", "To-Do List API"),
        ("I will build the Clinic Appointment API: patients, doctors and appointments.", "Clinic Appointment API"),
    ],
)
def test_the_api_name_is_read_from_the_agents_first_sentence(sentence: str, name: str) -> None:
    assert api_name(sentence) == name


@pytest.mark.parametrize(
    "sentence",
    [
        "Writing app/main.py",  # no name in it
        "Building an API for my shop.",  # "API" alone is not a name
        "The tests failed, so I will fix the books table, then the API.",  # not an opening sentence with a name
    ],
)
def test_no_name_when_the_sentence_has_none(sentence: str) -> None:
    assert api_name(sentence) is None


def new_project(request: str = "A small library for a reading club with books and borrowing") -> str:
    return client.post("/projects", json={"request": request}).json()["id"]


def thinking(text: str) -> dict[str, object]:
    return {"status": "working", "step": {"kind": "Thinking", "text": text, "state": "done", "phase": "planning"}}


def test_the_project_takes_the_name_from_the_first_sentence() -> None:
    project_id = new_project()

    add_event(project_id, thinking("Building a Reading Club Library API with a books table and 5 endpoints."))

    assert client.get(f"/projects/{project_id}").json()["name"] == "Reading Club Library API"
    listed = {p["id"]: p["name"] for p in client.get("/projects").json()}
    assert listed[project_id] == "Reading Club Library API"


def test_the_first_name_sticks() -> None:
    project_id = new_project()
    add_event(project_id, thinking("Building a Reading Club Library API with a books table."))

    add_event(project_id, thinking("Building a Bookshop API instead."))  # a later sentence must not rename it

    assert client.get(f"/projects/{project_id}").json()["name"] == "Reading Club Library API"


def test_without_any_name_the_typed_request_is_shown_as_before() -> None:
    project_id = new_project("Make me a website with a nice homepage and a photo gallery for my church.")
    refusal = {"status": "failed", "step": {"kind": "Result", "text": "I cannot build websites, but a backend API could be built.", "state": "failed", "phase": "finishing"}}

    add_event(project_id, refusal)  # a Result step, not the agent's opening sentence: never a name

    assert client.get(f"/projects/{project_id}").json()["name"] == "Make me a website with a nice homepage…"


def test_a_refused_project_takes_the_name_from_its_final_event() -> None:
    project_id = new_project("Make me a website with a nice homepage and a photo gallery for my church.")
    refusal = {
        "status": "failed",
        "name": "Church Website (not built)",
        "step": {"kind": "Result", "text": "I cannot build websites.", "state": "failed", "phase": "finishing"},
    }

    add_event(project_id, refusal)

    assert client.get(f"/projects/{project_id}").json()["name"] == "Church Website (not built)"
