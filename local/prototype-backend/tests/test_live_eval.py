"""The live evaluation script, run against a FAKE model (no money spent)."""

from __future__ import annotations

import json

from app import intake, live_eval, pipeline
from app.config import settings
from tests.test_multi_record import SCHOOL


def _fake_model(messages, json_mode=False, use_fallback_first=False):
    system = messages[0]["content"]
    if "update a draft design" in system:  # the merge step after answers
        return json.dumps({"message": "ok", "blueprint": SCHOOL, "not_included": []})
    if "help a non-developer" in system:  # understand
        request = messages[-1]["content"].lower()
        if "todo" in request:
            todo = {"title": "Todo API", "description": "Tasks.", "resources": [
                {"name": "task", "plural": "tasks", "fields": [{"name": "title", "type": "str"},
                                                               {"name": "completed", "type": "bool"}]}]}
            return json.dumps({"verdict": "clear", "message": "ok", "blueprint": todo})
        questions = [{"id": f"q{i}", "text": f"Question {i}?", "kind": "yes_no", "why": "w"} for i in range(6)]
        return json.dumps({"verdict": "vague", "message": "ok", "blueprint": SCHOOL, "questions": questions})
    raise RuntimeError("OpenAPI/README: use the templates")  # like an outage: the builder falls back


def test_without_yes_nothing_is_sent(monkeypatch, capsys) -> None:
    monkeypatch.setattr(intake, "chat", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no calls")))
    assert live_eval.main([]) == 2
    assert "Nothing was sent" in capsys.readouterr().out


def test_a_full_run_with_a_fake_model(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "fake")
    monkeypatch.setattr(intake, "chat", _fake_model)
    monkeypatch.setattr(pipeline, "chat", _fake_model)

    code = live_eval.main(["--yes"], out_dir=tmp_path)

    report = json.loads(next(tmp_path.glob("live_eval_*.json")).read_text(encoding="utf-8"))
    results = {r["request"]: r for r in report["results"]}
    school = results["A school management system"]
    assert school["checks"] == {
        "at least 5 questions": True, "design follows every rule": True, "at least 3 record type(s)": True,
        "record types are linked": True, "built API passes all its own tests": True,
    }
    assert school["build"]["passed"] == school["build"]["tests"] == 54
    assert results["A todo API. Tasks have title, description and completed (yes/no)."]["checks"][
        "no questions for a clear request"] is True
    assert report["model_calls"] > 0
    assert code == 0, capsys.readouterr().out
