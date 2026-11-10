"""Build jobs. Step 1: saved in SQLite, so progress and finished downloads survive a restart.

Changing a Job object does NOT save it: call save_job() afterwards.
"""

from __future__ import annotations

import json
import traceback
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlmodel import Session as DbSession
from sqlmodel import select

from app.config import settings
from app.db import JobRow, get_engine, now_iso
from app.models import Analysis, JobPublic
from app.pipeline import generate_project

INTERRUPTED = "The builder restarted during this build. Please click the build button again."


@dataclass
class Job:
    id: str
    owner_id: int
    requirement: str
    analysis: Analysis | None = None
    status: str = "queued"
    stage: str = "queued"
    error: str | None = None
    title: str | None = None
    files: list[str] = field(default_factory=list)
    latency_s: float | None = None
    metrics: dict[str, Any] = field(default_factory=dict)
    zip_path: str | None = None
    created_at: str = field(default_factory=now_iso)
    # The build timeline and the generated project's own test results (see add_step / run_job)
    steps: list[dict[str, Any]] = field(default_factory=list)
    tests: list[dict[str, Any]] = field(default_factory=list)

    def public(self) -> JobPublic:
        return JobPublic(
            id=self.id,
            status=self.status,
            stage=self.stage,
            error=self.error,
            title=self.title,
            files=self.files,
            latency_s=self.latency_s,
            metrics=self.metrics,
            steps=self.steps,
            tests=self.tests,
        )


def _to_row(job: Job) -> JobRow:
    return JobRow(
        id=job.id,
        owner_id=job.owner_id,
        requirement=job.requirement,
        analysis_json=job.analysis.model_dump_json() if job.analysis else None,
        status=job.status,
        stage=job.stage,
        error=job.error,
        title=job.title,
        files_json=json.dumps(job.files),
        latency_s=job.latency_s,
        metrics_json=json.dumps(job.metrics),
        zip_path=job.zip_path,
        created_at=job.created_at,
        steps_json=json.dumps(job.steps),
        tests_json=json.dumps(job.tests),
    )


def _from_row(row: JobRow) -> Job:
    return Job(
        id=row.id,
        owner_id=row.owner_id,
        requirement=row.requirement,
        analysis=Analysis.model_validate_json(row.analysis_json) if row.analysis_json else None,
        status=row.status,
        stage=row.stage,
        error=row.error,
        title=row.title,
        files=json.loads(row.files_json),
        latency_s=row.latency_s,
        metrics=json.loads(row.metrics_json),
        zip_path=row.zip_path,
        created_at=row.created_at,
        # Rows saved before the timeline existed have no steps or tests yet
        steps=json.loads(row.steps_json or "[]"),
        tests=json.loads(row.tests_json or "[]"),
    )


def save_job(job: Job) -> None:
    with DbSession(get_engine()) as db:
        # merge = insert if new, update if the id already exists
        db.merge(_to_row(job))
        db.commit()


def create_job(requirement: str, owner_id: int, analysis: Analysis | None = None) -> Job:
    job = Job(id=uuid.uuid4().hex[:12], owner_id=owner_id, requirement=requirement, analysis=analysis)
    save_job(job)
    return job


def get_job(job_id: str) -> Job | None:
    with DbSession(get_engine()) as db:
        row = db.get(JobRow, job_id)
        return _from_row(row) if row else None


def recover_interrupted_jobs() -> int:
    """Called when the server starts. A build thread cannot survive a restart, so any job still
    'queued' or 'running' is dead: mark it failed with a plain message instead of leaving it stuck."""
    with DbSession(get_engine()) as db:
        rows = db.exec(select(JobRow).where(JobRow.status.in_(["queued", "running"]))).all()
        for row in rows:
            row.status = "failed"
            row.stage = "failed"
            row.error = INTERRUPTED
            # End the timeline with the reason, so no step is left looking "in progress"
            steps = [{**step, "state": "done"} if step["state"] == "current" else step
                     for step in json.loads(row.steps_json or "[]")]
            steps.append({"kind": "Result", "text": INTERRUPTED, "state": "failed"})
            row.steps_json = json.dumps(steps)
            db.add(row)
        db.commit()
        return len(rows)


# --------------------------------------------------------------------------- the build timeline


def add_step(job: Job, kind: str, text: str, state: str = "current", output: str | None = None) -> None:
    """Adds one line to the timeline. The step that was 'current' before it is now 'done'."""
    for step in job.steps:
        if step["state"] == "current":
            step["state"] = "done"
    step: dict[str, Any] = {"kind": kind, "text": text, "state": state}
    if output:
        step["output"] = output
    job.steps.append(step)


def _stage_steps(job: Job, stage: str) -> list[tuple[str, str]]:
    """The plain-English timeline lines for one pipeline stage."""
    design = job.analysis
    if stage == "analyzing":
        return [("Thinking", "Reading your request and choosing a design.")]
    if stage == "generating_openapi":
        lines = [("Doing", "Writing the API description (openapi.yaml).")]
        if design:
            things = ", ".join(r.plural.replace("_", " ") for r in design.resources)
            lines.insert(0, ("Thinking", f"I will build {things}, then test them."))
        return lines
    if stage == "generating_code":
        return [("Doing", "Writing the project files.")]
    if stage == "testing":
        return [("Doing", "Running the project's own tests.")]
    if stage == "packaging":
        return [("Doing", "Packing your download.")]
    return []


def _finish_steps(job: Job, tests: list[dict[str, Any]], tests_error: str) -> None:
    if tests_error:
        add_step(job, "Result", "The tests could not run, so they are not checked yet.", "failed", tests_error)
        return
    failed = [test for test in tests if not test["passed"]]
    if not failed:
        add_step(job, "Result", f"All {len(tests)} tests passed. Your API is ready.", "done")
        return
    output = "\n".join(f"FAILED {test['name']}: {test['message']}" for test in failed)
    add_step(job, "Result", f"{len(failed)} of {len(tests)} tests failed. The download includes TEST_RESULTS.md.", "failed", output)


def run_job(job_id: str) -> None:
    job = get_job(job_id)
    if not job:
        return
    job.status = "running"
    save_job(job)
    output_dir = Path(settings.generated_dir) / job.id

    def on_stage(name: str) -> None:
        job.stage = name
        for kind, text in _stage_steps(job, name):
            add_step(job, kind, text)
        save_job(job)  # so the person polling /jobs/{id} sees each stage

    try:
        result = generate_project(job.requirement, output_dir, on_stage=on_stage, analysis=job.analysis)
        job.status = "succeeded"
        job.stage = "done"
        job.title = result["analysis"].get("title")
        job.files = result["files"]
        job.latency_s = result["latency_s"]
        job.metrics = result["metrics"]
        job.zip_path = result["zip_path"]
        job.tests = result.get("tests", [])
        _finish_steps(job, job.tests, result.get("tests_error", ""))
    except Exception as exc:
        job.status = "failed"
        job.stage = "failed"
        job.error = str(exc)
        job.metrics = {"traceback": traceback.format_exc()[-2000:]}
        add_step(job, "Result", "Building stopped. Approve the plan again to retry.", "failed", str(exc))
    save_job(job)
