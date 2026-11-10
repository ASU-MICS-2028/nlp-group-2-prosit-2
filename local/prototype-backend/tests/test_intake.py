"""Phase 2 M1: Understand step, guided questions, confirmation card and demand log (LLM replaced by fakes)."""

import json
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import intake
from app.config import settings
from app.main import app
from app.models import Analysis, FieldSpec, Question, Understanding
from app.openapi_builder import build_openapi
from app.packager import write_project, zip_project
from app.policy import REFUSAL_MESSAGE
from app.scaffold import render_project
from app.validators import blueprint_problems

PRODUCT_BLUEPRINT = {
    "title": "Products API",
    "description": "Products the shop sells.",
    "resource_name": "product",
    "resource_plural": "products",
    "fields": [
        {"name": "name", "type": "str", "required": True, "description": "Product name"},
        {"name": "price", "type": "float", "required": True, "description": "Price"},
        {"name": "quantity_in_stock", "type": "int", "required": False, "description": "Stock"},
    ],
}

SHOP_VAGUE = {
    "verdict": "vague",
    "message": "I'll start with your products.",
    "requested_items": [{"text": "online shop", "built": True}],
    "blueprint": PRODUCT_BLUEPRINT,
    "not_included": [{"category": "more_record_types", "text": "Customers and orders as linked lists (coming soon)"}],
    "questions": [
        {"id": "sell", "text": "What do you sell?", "kind": "single_choice",
         "options": ["Physical products", "Digital products", "Services"], "default": "Physical products"},
        {"id": "currency", "text": "Which currency do you use?", "kind": "single_choice",
         "options": ["Ghana cedi (GHS)", "US dollar (USD)"], "default": "Ghana cedi (GHS)"},
    ],
}


class FakeLLM:
    """Returns queued replies and records the messages it was sent."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls: list[list[dict]] = []

    def __call__(self, messages, json_mode=False, use_fallback_first=False):
        self.calls.append(messages)
        reply = self.replies.pop(0)
        return reply if isinstance(reply, str) else json.dumps(reply)


@pytest.fixture
def fake_llm(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    monkeypatch.setattr(settings, "demand_log_path", str(tmp_path / "demand.jsonl"))
    # The "at least 5 questions" re-ask is tested on its own below; here it would use up queued replies
    monkeypatch.setattr(intake, "MIN_QUESTIONS", 0)

    def install(*replies):
        fake = FakeLLM(*replies)
        monkeypatch.setattr(intake, "chat", fake)
        return fake

    return install


client = TestClient(app)


# --------------------------------------------------------------------------- understand


def test_clear_request_skips_questions(fake_llm) -> None:
    """Clear requests go straight to the confirmation card, even if the model asked questions."""
    fake_llm({**SHOP_VAGUE, "verdict": "clear", "not_included": []})
    result = intake.understand("Create an inventory API for products with name, price and stock.")
    assert result.verdict == "clear"
    assert result.questions == []
    assert result.blueprint.resources[0].plural == "products"


def test_disallowed_uses_fixed_policy_text(fake_llm) -> None:
    """Refusals always use the written policy text, never the model's wording."""
    fake_llm({"verdict": "disallowed", "message": "This is unethical and you should feel bad.", "blueprint": PRODUCT_BLUEPRINT})
    result = intake.understand("Collect phone numbers from Facebook profiles")
    assert result.verdict == "disallowed"
    assert result.message == REFUSAL_MESSAGE
    assert result.blueprint is None and result.questions == []


def test_unbuilt_requests_are_never_silently_dropped(fake_llm) -> None:
    """Anything the model marks as not built ends up in "Not included yet", even if it forgot to list it."""
    fake_llm({
        **SHOP_VAGUE,
        "verdict": "reducible",
        "requested_items": [
            {"text": "products", "built": True},
            {"text": "Mobile money payments", "built": False},
            {"text": "Email for every order", "built": False},
        ],
        "not_included": [{"category": "payments", "text": "Mobile money payments"}],
    })
    result = intake.understand("A shop with mobile money payments and an email for every order")
    texts = [item.text for item in result.not_included]
    assert "Mobile money payments" in texts
    assert "Email for every order" in texts
    assert len(texts) == 2


def test_reducible_with_nothing_left_out_becomes_clear(fake_llm) -> None:
    fake_llm({**SHOP_VAGUE, "verdict": "reducible", "not_included": [], "questions": []})
    assert intake.understand("Products with name and price").verdict == "clear"


def test_questions_are_capped_and_cleaned(fake_llm) -> None:
    """At most 8 questions; every one has a usable kind, options and default."""
    questions = [
        {"id": f"q{i}", "text": f"Question {i}?", "kind": "single_choice", "options": ["A", "B"], "default": "Z"}
        for i in range(8)
    ] + [{"id": "q0", "text": "Do you deliver?", "kind": "yes_no", "default": False}]
    questions.insert(1, {"id": "q0", "text": "Do you deliver?", "kind": "yes_no", "default": False})
    questions.insert(2, {"id": "bad", "text": "Pick one", "kind": "single_choice", "options": ["Only"]})
    fake_llm({**SHOP_VAGUE, "questions": questions})
    result = intake.understand("Build me an online shop")
    assert len(result.questions) == 8
    first, yes_no, converted = result.questions[:3]
    assert first.default == "A"  # an invalid default falls back to the first option
    assert yes_no.options == ["Yes", "No"] and yes_no.default == "No" and yes_no.id != "q0"
    assert converted.kind == "short_text" and converted.options == []


def test_model_written_other_option_is_not_shown_twice(fake_llm) -> None:
    """The form adds its own "Other" box, so an "Other" option from the model is folded into it."""
    question = {"id": "currency", "text": "Which currency?", "kind": "single_choice",
                "options": ["Ghana cedi (GHS)", "US dollar (USD)", "Other"], "allow_other": False, "default": "Other"}
    fake_llm({**SHOP_VAGUE, "questions": [question]})
    result = intake.understand("Build me an online shop").questions[0]
    assert result.options == ["Ghana cedi (GHS)", "US dollar (USD)"]
    assert result.allow_other and result.default == "Ghana cedi (GHS)"


def test_jargon_is_replaced(fake_llm) -> None:
    """Users never see words like CRUD, endpoint or foreign key."""
    fake_llm({
        **SHOP_VAGUE,
        "message": "I will build CRUD endpoints for the product resource.",
        "not_included": [{"category": "more_record_types", "text": "Orders with a foreign key to customers"}],
    })
    result = intake.understand("Build me an online shop")
    combined = (result.message + " " + " ".join(i.text for i in result.not_included)).lower()
    for word in ("crud", "endpoint", "resource", "foreign key"):
        assert word not in combined


def test_invalid_output_is_retried_once_with_errors(fake_llm) -> None:
    """A design that breaks the rules triggers one "fix these errors" retry."""
    bad = {**SHOP_VAGUE, "blueprint": {**PRODUCT_BLUEPRINT, "fields": PRODUCT_BLUEPRINT["fields"][:1]}}
    fake = fake_llm(bad, SHOP_VAGUE)
    result = intake.understand("Build me an online shop")
    assert result.blueprint.resources[0].name == "product"
    assert len(fake.calls) == 2
    assert "Fix these errors" in fake.calls[1][-1]["content"]
    assert "between 2 and 10 details" in fake.calls[1][-1]["content"]


def test_unsupported_explains_and_offers_alternative(fake_llm) -> None:
    fake_llm({
        "verdict": "unsupported",
        "message": "I can't build websites yet.",
        "alternative": "I can build the data part behind your website: a list of members.",
        "blueprint": {**PRODUCT_BLUEPRINT, "resource_name": "member", "resource_plural": "members"},
        "not_included": [{"category": "website_or_app", "text": "The church website itself"}],
    })
    result = intake.understand("Make a website for my church with a photo gallery")
    assert result.verdict == "unsupported"
    assert "I build the data part of an app" in result.message
    assert result.alternative.startswith("I can build")
    assert result.blueprint.resources[0].plural == "members"


# --------------------------------------------------------------------------- answers


def _vague_understanding() -> Understanding:
    return intake.normalize_understanding(SHOP_VAGUE)


def test_skipped_answers_use_defaults(fake_llm) -> None:
    fake = fake_llm({"message": "ok", "blueprint": PRODUCT_BLUEPRINT, "not_included": []})
    intake.apply_answers("Build me an online shop", _vague_understanding(), {})
    sent = json.loads(fake.calls[0][-1]["content"])
    assert sent["answers"] == {"sell": "Physical products", "currency": "Ghana cedi (GHS)"}


def test_merge_keeps_previous_not_included_items(fake_llm) -> None:
    """Answers can add "Not included yet" items but never remove earlier ones."""
    fake_llm({"message": "ok", "blueprint": PRODUCT_BLUEPRINT,
              "not_included": [{"category": "file_uploads", "text": "Product photos"}]})
    result = intake.apply_answers("Build me an online shop", _vague_understanding(), {"sell": "Physical products"})
    texts = [item.text for item in result.not_included]
    assert texts == ["Customers and orders as linked lists (coming soon)", "Product photos"]
    assert result.questions == [] and result.verdict == "reducible"


def test_merge_failure_keeps_best_guess(fake_llm) -> None:
    fake_llm("not json", "still not json")
    current = _vague_understanding()
    result = intake.apply_answers("Build me an online shop", current, {})
    assert result.blueprint == current.blueprint
    assert result.questions == []


# --------------------------------------------------------------------------- rule checks


def _analysis(**changes) -> Analysis:
    """The product design with some of its (only) record type's settings changed."""
    base = Analysis(**PRODUCT_BLUEPRINT)
    return base.model_copy(update={"resources": [base.resources[0].model_copy(update=changes)]})


def test_blueprint_rules() -> None:
    assert blueprint_problems(_analysis()) == []
    one_field = _analysis(fields=[FieldSpec(name="name", type="str")])
    assert any("between 2 and 10" in p for p in blueprint_problems(one_field))
    eleven = _analysis(fields=[FieldSpec(name=f"f{i}", type="str") for i in range(11)])
    assert any("between 2 and 10" in p for p in blueprint_problems(eleven))
    dupes = _analysis(fields=[FieldSpec(name="name", type="str"), FieldSpec(name="name", type="int")])
    assert any("appears twice" in p for p in blueprint_problems(dupes))
    assert blueprint_problems(_analysis(plural="health"))
    assert blueprint_problems(_analysis(name="class"))
    assert blueprint_problems(_analysis(plural="product"))


# --------------------------------------------------------------------------- API flow


def test_session_flow_vague_to_build(fake_llm, monkeypatch, sign_in) -> None:
    """Vague request -> questions -> answers -> edited card -> build, with demand logged once per item."""
    me = sign_in()
    fake_llm(
        SHOP_VAGUE,
        {"message": "Products in GHS.", "blueprint": PRODUCT_BLUEPRINT,
         "not_included": [{"category": "payments", "text": "Mobile money payments"}]},
    )
    started = client.post("/sessions", json={"requirement": "Build me an online shop"}, headers=me)
    assert started.status_code == 200, started.text
    session = started.json()
    assert session["status"] == "needs_answers"
    assert len(session["understanding"]["questions"]) == 2

    assert client.post(f"/sessions/{session['id']}/build", headers=me).status_code == 409

    answered = client.post(
        f"/sessions/{session['id']}/answers", json={"answers": {"sell": "Services"}}, headers=me
    )
    assert answered.status_code == 200, answered.text
    assert answered.json()["status"] == "ready"

    edited = dict(PRODUCT_BLUEPRINT, fields=[
        *PRODUCT_BLUEPRINT["fields"],
        {"name": "Expiry Date", "type": "datetime", "required": False},
    ])
    saved = client.put(f"/sessions/{session['id']}/blueprint", json=edited, headers=me)
    assert saved.status_code == 200, saved.text
    assert saved.json()["understanding"]["blueprint"]["resources"][0]["fields"][-1]["name"] == "expiry_date"

    too_few = dict(PRODUCT_BLUEPRINT, fields=PRODUCT_BLUEPRINT["fields"][:1])
    rejected = client.put(f"/sessions/{session['id']}/blueprint", json=too_few, headers=me)
    assert rejected.status_code == 400 and "between 2 and 10 details" in rejected.json()["detail"]

    started_jobs = []
    monkeypatch.setattr("app.main.run_job", lambda job_id: started_jobs.append(job_id))
    built = client.post(f"/sessions/{session['id']}/build", headers=me)
    assert built.status_code == 200, built.text
    assert started_jobs == [built.json()["job_id"]]

    # Step 2: the demand log is admin-only
    assert client.get("/demand-log", headers=me).status_code == 403
    admin = sign_in("boss@example.com", role="admin")
    log = client.get("/demand-log", headers=admin).json()
    assert [entry["text"] for entry in log] == [
        "Customers and orders as linked lists (coming soon)",
        "Mobile money payments",
    ]
    assert all({"date", "category", "text"} <= entry.keys() for entry in log)


def test_session_refused(fake_llm, sign_in) -> None:
    me = sign_in()
    fake_llm({"verdict": "disallowed"})
    session = client.post(
        "/sessions", json={"requirement": "Scrape emails from LinkedIn profiles"}, headers=me
    ).json()
    assert session["status"] == "refused"
    assert client.post(f"/sessions/{session['id']}/build", headers=me).status_code == 409


def test_session_input_limits(fake_llm, sign_in) -> None:
    me = sign_in()
    fake_llm()
    assert client.post("/sessions", json={"requirement": "word " * 201}, headers=me).status_code == 400


def test_unknown_session_message_is_plain(sign_in) -> None:
    response = client.get("/sessions/missing", headers=sign_in())
    assert response.status_code == 404
    assert "start again" in response.json()["detail"]


# --------------------------------------------------------------------------- launcher


def test_export_has_double_click_launchers(tmp_path: Path) -> None:
    """Start.bat uses CRLF, Start.command uses LF and stays executable inside the ZIP."""
    analysis = _analysis()
    project = tmp_path / "project"
    write_project(project, render_project(analysis, build_openapi(analysis)))
    bat = (project / "Start.bat").read_bytes()
    command = (project / "Start.command").read_bytes()
    assert b"\r\n" in bat and b"uv run" in bat
    assert b"\r" not in command and command.startswith(b"#!/bin/bash\n")

    archive = zip_project(project, tmp_path / "project.zip")
    with zipfile.ZipFile(archive) as zf:
        mode = zf.getinfo("Start.command").external_attr >> 16
        assert mode & 0o111, oct(mode)
        assert "app/main.py" in zf.namelist()
