"""Designs with several linked record types (e.g. a school), and the 5-question minimum."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app import intake, memory, retrieval
from app.config import settings
from app.models import Analysis, Understanding
from app.openapi_builder import build_openapi
from app.packager import write_project
from app.project_tests import run_project_tests
from app.scaffold import render_project, render_readme
from app.scaffold_code import count_checks
from app.validators import blueprint_problems, openapi_mismatches, readme_problems, validate_python_files


def f(name: str, type: str = "str", required: bool = True, links_to: str | None = None) -> dict:
    return {"name": name, "type": type, "required": required, "links_to": links_to}


SCHOOL = {
    "title": "School Management API",
    "description": "Students, teachers, classrooms, exams, results and attendance.",
    "resources": [
        # Deliberately not in creation order: students come before the classrooms they link to
        {"name": "student", "plural": "students", "fields": [f("full_name"), f("classroom_id", "link", True, "classroom")]},
        {"name": "teacher", "plural": "teachers", "fields": [f("full_name"), f("subject")]},
        {"name": "classroom", "plural": "classrooms", "fields": [f("name"), f("teacher_id", "link", False, "teacher")]},
        {"name": "exam", "plural": "exams", "fields": [f("title"), f("exam_date", "datetime"), f("classroom_id", "link", True, "classroom")]},
        {"name": "exam_result", "plural": "exam_results",
         "fields": [f("score", "float"), f("exam_id", "link", True, "exam"), f("student_id", "link", True, "student")]},
        {"name": "attendance", "plural": "attendances",
         "fields": [f("day", "datetime"), f("present", "bool"), f("student_id", "link", True, "student")]},
    ],
}


def school(**changes) -> Analysis:
    return Analysis.model_validate({**SCHOOL, **changes})


def with_resources(*resources: dict) -> Analysis:
    return Analysis.model_validate({"title": "T API", "description": "d", "resources": list(resources)})


# --------------------------------------------------------------------------- the model


def test_records_are_ordered_so_links_come_first() -> None:
    order = [r.name for r in school().in_creation_order()]
    assert order.index("teacher") < order.index("classroom") < order.index("student") < order.index("exam_result")
    assert [r.name for r, _ in school().children_of("classroom")] == ["student", "exam"]


def test_old_single_record_designs_still_load() -> None:
    old = Analysis.model_validate({
        "title": "Books API", "description": "Books.", "resource_name": "book", "resource_plural": "books",
        "fields": [f("title"), f("price", "float")],
    })
    assert [r.plural for r in old.resources] == ["books"]
    assert [x.name for x in old.resources[0].fields] == ["title", "price"]


# --------------------------------------------------------------------------- rule checks


def test_the_school_design_follows_every_rule() -> None:
    assert blueprint_problems(school()) == []


@pytest.mark.parametrize(
    ("resources", "expected"),
    [
        ([{"name": "student", "plural": "students", "fields": [f("full_name"), f("ghost_id", "link", True, "ghost")]}],
         "links to a record type that does not exist"),
        ([{"name": "staff", "plural": "staffs", "fields": [f("full_name"), f("staff_id", "link", True, "staff")]}],
         "links staffs to itself"),
        ([{"name": "a", "plural": "as_list", "fields": [f("x"), f("b_id", "link", True, "b")]},
          {"name": "b", "plural": "bs", "fields": [f("y"), f("a_id", "link", True, "a")]}],
         "go round in a circle"),
        ([{"name": "classroom", "plural": "classrooms", "fields": [f("name"), f("y")]},
          {"name": "student", "plural": "students", "fields": [f("full_name"), f("classroom", "link", True, "classroom")]}],
         "must end with _id"),
        ([{"name": "classroom", "plural": "classrooms", "fields": [f("name"), f("y")]},
          {"name": "student", "plural": "students", "fields": [f("classroom_id", "link", True, "classroom"), f("x_id", "link", True, "classroom")]}],
         "not a link"),
        ([{"name": "book", "plural": "books", "fields": [f("a"), f("b")]},
          {"name": "book", "plural": "books", "fields": [f("a"), f("b")]}],
         "same name"),
        ([{"name": f"r{i}", "plural": f"r{i}s", "fields": [f("a"), f("b")]} for i in range(9)],
         "at most 8 record types"),
    ],
    ids=["missing-target", "self-link", "circle", "link-name", "only-links", "duplicate", "too-many"],
)
def test_broken_designs_are_explained(resources: list[dict], expected: str) -> None:
    problems = blueprint_problems(with_resources(*resources))
    assert any(expected in p for p in problems), problems


# --------------------------------------------------------------------------- reading the model's reply


def test_a_multi_record_reply_is_cleaned_up() -> None:
    raw = {
        "title": "School API", "description": "d",
        "resources": [
            {"name": "Class", "plural": "Classes", "fields": [f("Name"), f("year", "int")]},
            {"name": "student", "plural": "students",
             "fields": [f("full name"), {"name": "class", "type": "link", "links_to": "class"}, f("id", "int")]},
        ],
    }
    design = intake.normalize_analysis(raw)
    classroom, student = design.resources
    assert (classroom.name, classroom.plural) == ("classroom", "classrooms")  # "class" is a Python word
    assert [x.name for x in student.fields] == ["full_name", "classroom_id"]  # link renamed, "id" dropped
    assert student.fields[1].links_to == "classroom"
    assert blueprint_problems(design) == []


def test_an_old_style_single_record_reply_still_works() -> None:
    design = intake.normalize_analysis({"title": "T", "resource_name": "book", "resource_plural": "books",
                                        "fields": [f("title"), f("price", "float")]})
    assert [r.plural for r in design.resources] == ["books"]


# --------------------------------------------------------------------------- at least 5 questions


def _vague(n_questions: int) -> dict:
    questions = [{"id": f"q{i}", "text": f"Question {i}?", "kind": "yes_no", "why": "It changes the design."}
                 for i in range(n_questions)]
    return {"verdict": "vague", "message": "ok", "blueprint": SCHOOL, "questions": questions}


@pytest.fixture
def replies(monkeypatch):
    sent: list[list[dict]] = []

    def install(*queued):
        queue = list(queued)

        def fake_chat(messages, json_mode=False, use_fallback_first=False):
            sent.append(messages)
            if not queue:
                raise RuntimeError("no more replies")
            return json.dumps(queue.pop(0))

        monkeypatch.setattr(intake, "chat", fake_chat)
        return sent

    return install


def test_too_few_questions_are_asked_for_again(replies) -> None:
    sent = replies(_vague(2), _vague(6))
    result = intake.understand("school management system")
    assert len(result.questions) == 6
    assert "You asked only 2 questions" in sent[1][-1]["content"]


def test_if_asking_again_fails_the_first_design_is_kept(replies) -> None:
    replies(_vague(2))  # the second call gets no reply (like the LLM being down)
    result = intake.understand("school management system")
    assert len(result.questions) == 2 and result.blueprint is not None


def test_enough_questions_or_a_clear_request_are_not_asked_again(replies) -> None:
    sent = replies(_vague(5))
    assert len(intake.understand("school management system").questions) == 5
    assert len(sent) == 1
    sent = replies({**_vague(0), "verdict": "clear"})
    assert intake.understand("Students with name, classrooms with name").questions == []
    assert len(sent) == 2  # one new call only (the list collects all calls)


def test_questions_are_capped_at_8(replies) -> None:
    replies(_vague(12))
    assert len(intake.understand("school management system").questions) == 8


# --------------------------------------------------------------------------- the generated school API


def test_a_generated_school_api_passes_its_own_54_checks(tmp_path: Path) -> None:
    design = school()
    spec = build_openapi(design)
    assert openapi_mismatches(spec, design) == []
    files = render_project(design, spec)
    assert validate_python_files(files) == []
    assert {f"app/routers/{r.plural}.py" for r in design.resources} <= files.keys()
    write_project(tmp_path / "project", files)

    outcomes = run_project_tests(tmp_path / "project")

    assert count_checks(design) == 6 + 5 * 6 + 3 * 6 == 54
    assert len(outcomes) == 54 and all(o["passed"] for o in outcomes), [o for o in outcomes if not o["passed"]]
    names = {o["name"] for o in outcomes}
    assert {"student needs a real classroom", "find students by classroom",
            "classroom in use by students cannot be deleted"} <= names


def test_the_readme_lists_every_record_type_and_explains_links() -> None:
    readme = render_readme(school())
    assert readme_problems(readme, school()) == []
    for plural in ("students", "teachers", "classrooms", "exams", "exam_results", "attendances"):
        assert f"`/{plural}`" in readme
    assert "## How the records link together" in readme
    assert "?classroom_id=1" in readme or "?teacher_id=1" in readme


def test_openapi_documents_filters_422_and_409() -> None:
    import yaml

    paths = yaml.safe_load(build_openapi(school()))["paths"]
    assert [p["name"] for p in paths["/students"]["get"]["parameters"]] == ["classroom_id"]
    assert "422" in paths["/students"]["post"]["responses"]
    assert "409" in paths["/classrooms/{item_id}"]["delete"]["responses"]
    assert "409" not in paths["/attendances/{item_id}"]["delete"]["responses"]  # nothing links to attendance


# --------------------------------------------------------------------------- the API, memory and RAG


def test_editing_a_multi_record_plan_tidies_every_name(client, sign_in, monkeypatch) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    monkeypatch.setattr("app.main.understand",
                        lambda r, background="": Understanding(verdict="clear", message="ok", blueprint=school()))
    me = sign_in()
    session_id = client.post("/sessions", json={"requirement": "School management system"}, headers=me).json()["id"]
    edited = json.loads(school().model_dump_json())
    edited["resources"][0]["fields"].append(f("Parent Phone", "str", False))

    saved = client.put(f"/sessions/{session_id}/blueprint", json=edited, headers=me)

    assert saved.status_code == 200, saved.text
    students = saved.json()["understanding"]["blueprint"]["resources"][0]
    assert students["fields"][-1]["name"] == "parent_phone"

    broken = json.loads(school().model_dump_json())
    broken["resources"][0]["fields"][1]["links_to"] = "ghost"
    refused = client.put(f"/sessions/{session_id}/blueprint", json=broken, headers=me)
    assert refused.status_code == 400 and "does not exist" in refused.json()["detail"]


def test_memory_notices_added_and_removed_record_types() -> None:
    before = school()
    after = Analysis.model_validate({**SCHOOL, "resources": [*SCHOOL["resources"][:5],
                                                              {"name": "fee", "plural": "fees", "fields": [f("amount", "float"), f("paid", "bool")]}]})
    changes = memory.describe_changes(before, after)
    assert "Added record type 'fees'" in changes
    assert "Removed record type 'attendances'" in changes


def test_rag_describes_and_compares_whole_designs() -> None:
    line = retrieval.example_line(retrieval.Example("School Management API", "", school(), "seed"))
    assert "students with full_name (str, required), classroom_id (classroom link, required)" in line
    assert retrieval._same_design(school(), school())
    assert not retrieval._same_design(school(), Analysis.model_validate({**SCHOOL, "resources": SCHOOL["resources"][:2]}))
