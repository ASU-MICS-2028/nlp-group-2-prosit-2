"""Checks what the REAL model does with realistic requests (costs a little OpenAI money per run).

    .venv\\Scripts\\python -m app.live_eval            shows the plan and the number of calls, spends nothing
    .venv\\Scripts\\python -m app.live_eval --yes      runs it for real
    .venv\\Scripts\\python -m app.live_eval --yes --no-build   skips building (fewer calls)

For each request: understand → (answer every question with its default) → check the design → build it
and run its own tests. Results go to the screen and to local/evidence/live_eval_<date>.json.
"""

from __future__ import annotations

import json
import sys
import tempfile
import time
from datetime import date
from pathlib import Path
from typing import Any

from app import intake, pipeline
from app.config import settings
from app.intake import MIN_QUESTIONS
from app.models import Analysis
from app.pipeline import generate_project
from app.validators import blueprint_problems

# (request, what a good result looks like)
REQUESTS: list[tuple[str, dict[str, Any]]] = [
    ("Manage my school: students, teachers, classes, tests and exams, and daily attendance",
     {"min_record_types": 4, "needs_links": True}),
    ("A school management system", {"vague": True, "min_record_types": 3, "needs_links": True}),
    ("Something for my hair salon", {"vague": True, "min_record_types": 1}),
    ("A clinic: patients, doctors, appointments and prescriptions", {"min_record_types": 3, "needs_links": True}),
    ("A todo API. Tasks have title, description and completed (yes/no).", {"min_record_types": 1, "clear": True}),
]

# Most calls per request: understand (+1 fix retry) +1 "too few questions" re-ask +1 merge; build: 2-4 more
MAX_CALLS_UNDERSTAND = 4
MAX_CALLS_BUILD = 4


class CallCounter:
    """Wraps the model call so every request to OpenAI is counted."""

    def __init__(self, real):
        self.real = real
        self.calls = 0

    def __call__(self, *args, **kwargs):
        self.calls += 1
        return self.real(*args, **kwargs)


def _design_facts(design: Analysis | None) -> dict[str, Any]:
    if design is None:
        return {"record_types": 0, "links": 0, "problems": ["no design"]}
    return {
        "record_types": len(design.resources),
        "names": [r.plural for r in design.resources],
        "links": sum(len(r.link_fields) for r in design.resources),
        "problems": blueprint_problems(design),
    }


def check_one(request: str, expect: dict[str, Any], build: bool) -> dict[str, Any]:
    started = time.perf_counter()
    result: dict[str, Any] = {"request": request, "expect": expect, "checks": {}}
    understanding = intake.understand(request)
    result["verdict"] = understanding.verdict
    result["questions"] = [{"text": q.text, "kind": q.kind} for q in understanding.questions]
    checks = result["checks"]
    if expect.get("vague"):
        checks[f"at least {MIN_QUESTIONS} questions"] = len(understanding.questions) >= MIN_QUESTIONS
    if expect.get("clear"):
        checks["no questions for a clear request"] = understanding.questions == []

    design = understanding.blueprint
    if understanding.questions and design is not None:
        # Answer like someone who accepts every default
        design = intake.apply_answers(request, understanding, {}).blueprint
    facts = _design_facts(design)
    result["design"] = facts
    checks["design follows every rule"] = facts["problems"] == []
    checks[f"at least {expect['min_record_types']} record type(s)"] = facts["record_types"] >= expect["min_record_types"]
    if expect.get("needs_links"):
        checks["record types are linked"] = facts["links"] > 0

    if build and design is not None and not facts["problems"]:
        with tempfile.TemporaryDirectory() as folder:
            built = generate_project(request, Path(folder), analysis=design)
        tests = built["tests"]
        result["build"] = {"tests": len(tests), "passed": sum(t["passed"] for t in tests),
                           "openapi": built["metrics"].get("openapi_source"),
                           "readme": built["metrics"].get("readme_source"), "tests_error": built["tests_error"]}
        checks["built API passes all its own tests"] = bool(tests) and all(t["passed"] for t in tests)
    result["seconds"] = round(time.perf_counter() - started, 1)
    return result


def main(args: list[str], out_dir: Path | None = None) -> int:
    build = "--no-build" not in args
    most = len(REQUESTS) * (MAX_CALLS_UNDERSTAND + (MAX_CALLS_BUILD if build else 0))
    print(f"{len(REQUESTS)} requests, at most about {most} model calls ({settings.openai_model} / "
          f"{settings.openai_fallback_model}).")
    if "--yes" not in args:
        print("Nothing was sent. Add --yes to run it for real (it uses your OpenAI key and costs a little).")
        return 2
    if not settings.openai_api_key:
        print("OPENAI_API_KEY is not set.")
        return 1

    counter = CallCounter(intake.chat)
    intake.chat = counter  # the same counter for every module that calls the model
    pipeline.chat = counter
    results = []
    for request, expect in REQUESTS:
        try:
            results.append(check_one(request, expect, build))
        except Exception as exc:  # one failure must not hide the others
            results.append({"request": request, "error": f"{type(exc).__name__}: {exc}", "checks": {"ran": False}})
        last = results[-1]
        passed = sum(bool(v) for v in last["checks"].values())
        print(f"\n{request!r}: {passed} of {len(last['checks'])} checks passed")
        for name, ok in last["checks"].items():
            print(f"  [{'OK ' if ok else 'NO '}] {name}")
        if "design" in last:
            print(f"  design: {last['design']}")
        if last.get("questions"):
            print(f"  {len(last['questions'])} questions: " + " | ".join(q["text"] for q in last["questions"]))
        if "build" in last:
            print(f"  build: {last['build']}")
        if "error" in last:
            print(f"  ERROR: {last['error']}")

    total = sum(len(r["checks"]) for r in results)
    ok = sum(sum(bool(v) for v in r["checks"].values()) for r in results)
    print(f"\nAll requests: {ok} of {total} checks passed, {counter.calls} model calls.")
    out = (out_dir or Path(__file__).resolve().parents[2] / "evidence") / f"live_eval_{date.today()}.json"
    out.write_text(json.dumps({"model_calls": counter.calls, "results": results}, indent=1), encoding="utf-8")
    print(f"Saved {out}")
    return 0 if ok == total else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
