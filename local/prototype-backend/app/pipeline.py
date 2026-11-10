from __future__ import annotations

import time
from typing import Any, Callable

from app.intake import understand
from app.llm import chat, parse_markdown_text, parse_yaml_text
from app.models import Analysis
from app.openapi_builder import build_openapi
from app.packager import write_project, zip_project
from app.project_tests import TestOutcome, run_project_tests
from app.prompts import OPENAPI_FIX_SYSTEM, OPENAPI_SYSTEM, README_SYSTEM
from app.scaffold import render_project, render_readme
from app.validators import (
    blueprint_problems,
    openapi_mismatches,
    readme_problems,
    validate_openapi_yaml,
    validate_python_files,
)


StageCallback = Callable[[str], None]


def _check_openapi(yaml_text: str, analysis: Analysis) -> None:
    validate_openapi_yaml(yaml_text)
    mismatches = openapi_mismatches(yaml_text, analysis)
    if mismatches:
        raise ValueError("Spec does not match the generated code:\n- " + "\n- ".join(mismatches))


def _openapi_contract(analysis: Analysis) -> str:
    paths = ", ".join(
        f"/{r.plural} (get, post), /{r.plural}/{{item_id}} (get, put, delete)" for r in analysis.resources
    )
    schemas = ", ".join(f"{r.class_name}, {r.class_name}Create, {r.class_name}Update" for r in analysis.resources)
    return (
        f"Use exactly these paths: /health (get), {paths}. The path parameter must be named item_id.\n"
        f"Use exactly these schema names in components.schemas: {schemas}. "
        "The plain name has id plus every field; Create and Update have every non-auto field. "
        "Link fields are integers (the id of the linked record)."
    )


def generate_openapi(analysis: Analysis) -> tuple[str, dict[str, Any]]:
    metrics: dict[str, Any] = {"openapi_retries": 0, "openapi_source": "llm"}
    user_payload = f"{analysis.model_dump_json(indent=2)}\n\n{_openapi_contract(analysis)}"
    messages = [
        {"role": "system", "content": OPENAPI_SYSTEM},
        {"role": "user", "content": user_payload},
    ]
    try:
        yaml_text = parse_yaml_text(chat(messages))
    except Exception as exc:
        # The LLM is down or rate-limited. The template builder makes a correct file without it,
        # so the build carries on instead of failing (before, only bad YAML fell back here).
        metrics["openapi_source"] = "fallback_builder"
        metrics["openapi_llm_mismatches"] = [f"OpenAPI generation failed: {exc}"]
        yaml_text = build_openapi(analysis)
        validate_openapi_yaml(yaml_text)
        return yaml_text, metrics
    try:
        metrics["openapi_llm_mismatches"] = openapi_mismatches(yaml_text, analysis)
    except Exception:
        metrics["openapi_llm_mismatches"] = ["LLM output was not parseable YAML"]
    try:
        _check_openapi(yaml_text, analysis)
        return yaml_text, metrics
    except Exception as first_error:
        metrics["openapi_retries"] = 1
        fix_messages = [
            {"role": "system", "content": OPENAPI_FIX_SYSTEM},
            {
                "role": "user",
                "content": (
                    f"Errors:\n{first_error}\n\n{_openapi_contract(analysis)}\n\n"
                    f"Current YAML:\n{yaml_text}"
                ),
            },
        ]
        try:
            yaml_text = parse_yaml_text(chat(fix_messages, use_fallback_first=True))
            _check_openapi(yaml_text, analysis)
            return yaml_text, metrics
        except Exception:
            metrics["openapi_source"] = "fallback_builder"
            yaml_text = build_openapi(analysis)
            validate_openapi_yaml(yaml_text)
            return yaml_text, metrics


def generate_readme(analysis: Analysis) -> tuple[str, dict[str, Any]]:
    metrics: dict[str, Any] = {"readme_source": "llm", "readme_llm_problems": []}
    first = analysis.in_creation_order()[0]
    plural = first.plural
    others = ", ".join(f"/{r.plural}" for r in analysis.resources if r is not first) or "none"
    fields = "; ".join(f"/{r.plural}: {', '.join(f.name for f in r.user_fields)}" for r in analysis.resources)
    contract = (
        f"Full curl examples for {plural} only: GET /health, GET /{plural}, POST /{plural}, GET /{plural}/1, "
        f"PUT /{plural}/1, DELETE /{plural}/1. Base URL http://localhost:8000. "
        f"Also list the other record types and their addresses ({others}), and explain the links "
        "(a link is the id of another record; a missing linked record is refused with 422; "
        "a record still linked to cannot be deleted, 409). "
        "Keys: there is NO default key. Two keys are already in the project's .env file: "
        "EDITOR_KEY (can add, edit and delete) and READER_KEY (can only look). "
        "In curl examples write YOUR_EDITOR_KEY for create, update and delete, and YOUR_READER_KEY "
        "for list and get. Never write a real-looking key. "
        f"Request bodies may only use these fields, per address: {fields}."
    )
    try:
        messages = [
            {"role": "system", "content": README_SYSTEM},
            {"role": "user", "content": f"{analysis.model_dump_json(indent=2)}\n\n{contract}"},
        ]
        text = parse_markdown_text(chat(messages))
        problems = readme_problems(text, analysis)
        metrics["readme_llm_problems"] = problems
        if not problems:
            return text, metrics
    except Exception as exc:
        metrics["readme_llm_problems"] = [f"README generation failed: {exc}"]
    metrics["readme_source"] = "template"
    return render_readme(analysis), metrics


def generate_project(
    requirement: str,
    output_dir,
    on_stage: StageCallback | None = None,
    analysis: Analysis | None = None,
) -> dict[str, Any]:
    """Build the project from a confirmed blueprint, or understand the requirement first when none is given."""
    started = time.perf_counter()

    def stage(name: str) -> None:
        if on_stage:
            on_stage(name)

    understanding = None
    if analysis is None:
        stage("analyzing")
        understanding = understand(requirement)
        if understanding.blueprint is None:
            raise RuntimeError(understanding.message)
        analysis = understanding.blueprint
    problems = blueprint_problems(analysis)
    if problems:
        raise ValueError(" ".join(problems))

    stage("generating_openapi")
    openapi_yaml, openapi_metrics = generate_openapi(analysis)

    stage("generating_code")
    readme, readme_metrics = generate_readme(analysis)
    files = render_project(analysis, openapi_yaml, readme)
    syntax_errors = validate_python_files(files)
    if syntax_errors:
        raise RuntimeError("Generated Python failed syntax checks: " + "; ".join(syntax_errors))

    project_dir = output_dir / "project"
    write_project(project_dir, files)

    # Run the project's own tests, so the timeline and the ready card show real results
    stage("testing")
    tests: list[TestOutcome] = []
    tests_error = ""
    try:
        tests = run_project_tests(project_dir)
    except RuntimeError as exc:
        tests_error = str(exc)  # the build still finishes; the person is told the tests did not run

    stage("packaging")
    zip_path = zip_project(project_dir, output_dir / "project.zip")

    return {
        "analysis": analysis.model_dump(),
        "understanding": understanding.model_dump() if understanding else None,
        "files": sorted(files.keys()),
        "zip_path": str(zip_path),
        "project_dir": str(project_dir),
        "latency_s": round(time.perf_counter() - started, 2),
        "tests": tests,
        "tests_error": tests_error,
        "metrics": {
            **openapi_metrics,
            **readme_metrics,
            "openapi_valid": True,
            "file_count": len(files),
        },
    }
