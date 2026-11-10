"""Runs a generated project's own tests, so the build timeline shows real passes and failures.

The generated code comes from our templates (not written freely by the LLM), and runs with a time
limit and without the builder's OpenAI key in its environment.
JUnit XML: a standard report format pytest can write; each <testcase> is one test, and a
<failure> or <error> inside it means the test did not pass.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ElementTree
from pathlib import Path
from typing import TypedDict

TIMEOUT_SECONDS = 120
REPORT_NAME = ".builder-tests.xml"


class TestOutcome(TypedDict):
    name: str  # plain words, e.g. "reader can look"
    passed: bool
    message: str  # first line of the failure, "" when it passed


def _plain_name(test_name: str) -> str:
    return test_name.removeprefix("test_").replace("_", " ")


def _read_report(report: Path) -> list[TestOutcome]:
    outcomes: list[TestOutcome] = []
    for case in ElementTree.parse(report).getroot().iter("testcase"):
        problem = case.find("failure")
        if problem is None:
            problem = case.find("error")
        if case.find("skipped") is not None:
            continue
        message = (problem.get("message") or "").splitlines()[0][:200] if problem is not None else ""
        outcomes.append({"name": _plain_name(case.get("name", "test")), "passed": problem is None, "message": message})
    return outcomes


def _tidy(project_dir: Path) -> None:
    """Remove what the test run left behind that should not be in the zip (TEST_RESULTS.md stays)."""
    (project_dir / "test.db").unlink(missing_ok=True)
    (project_dir / REPORT_NAME).unlink(missing_ok=True)
    for cache in project_dir.rglob("__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)


def run_project_tests(project_dir: Path) -> list[TestOutcome]:
    """Runs pytest in the project folder. Raises RuntimeError if the tests could not run at all."""
    # Full path first: pytest runs INSIDE the project folder, so a relative report path (the builder's
    # default "generated/..." is relative) would land one level too deep and never be found.
    project_dir = project_dir.resolve()
    # The builder's secrets are not the generated project's business
    env = {name: value for name, value in os.environ.items() if not name.startswith("OPENAI")}
    report = project_dir / REPORT_NAME
    try:
        subprocess.run(
            # -P: do not put the builder's own folder on the import path (both projects have an "app" package)
            [sys.executable, "-P", "-m", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={report}"],
            cwd=project_dir,
            env=env,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
        if not report.exists():
            raise RuntimeError("The tests could not start, so no results were written.")
        return _read_report(report)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"The tests took longer than {TIMEOUT_SECONDS} seconds and were stopped.") from exc
    finally:
        _tidy(project_dir)
