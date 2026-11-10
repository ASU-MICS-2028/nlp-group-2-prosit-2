from pathlib import Path
import subprocess
import sys

import pytest

from app.models import Analysis, FieldSpec
from app.openapi_builder import build_openapi
from app.packager import write_project
from app.scaffold import render_project
from app.validators import validate_openapi_yaml, validate_python_files

CASES = [
    Analysis(
        title="Todo API",
        description="Tasks with title, description, and completed status.",
        resource_name="todo",
        resource_plural="todos",
        fields=[
            FieldSpec(name="title", type="str", required=True),
            FieldSpec(name="description", type="str", required=False),
            FieldSpec(name="completed", type="bool", required=False, default="false"),
        ],
    ),
    Analysis(
        title="Notes API",
        description="Notes with title, body, and created_at.",
        resource_name="note",
        resource_plural="notes",
        fields=[
            FieldSpec(name="title", type="str", required=True),
            FieldSpec(name="body", type="str", required=True),
            FieldSpec(name="created_at", type="datetime", required=False, auto=True),
        ],
    ),
    Analysis(
        title="Inventory API",
        description="Products with name, sku, quantity, and price.",
        resource_name="product",
        resource_plural="products",
        fields=[
            FieldSpec(name="name", type="str", required=True),
            FieldSpec(name="sku", type="str", required=True),
            FieldSpec(name="quantity", type="int", required=True),
            FieldSpec(name="price", type="float", required=True),
        ],
    ),
]


# The ways a user might run the generated tests. -P keeps the cwd off sys.path, matching
# what a bare `pytest` command or `python tests/test_x.py` sees.
RUN_MODES = {
    "pytest-from-root": ("", ["-m", "pytest"]),
    "pytest-from-tests-dir": ("tests", ["-m", "pytest"]),
    "python-test-file": ("", ["tests/test_{plural}.py"]),
}


@pytest.mark.parametrize("mode", RUN_MODES)
@pytest.mark.parametrize("analysis", CASES, ids=lambda item: item.resources[0].name)
def test_generated_project_pytest(analysis: Analysis, mode: str, tmp_path: Path) -> None:
    """A generated project's own tests pass however the user starts them."""
    openapi = build_openapi(analysis)
    validate_openapi_yaml(openapi)
    files = render_project(analysis, openapi)
    assert not validate_python_files(files)
    project = tmp_path / "project"
    write_project(project, files)
    subdir, args = RUN_MODES[mode]
    proc = subprocess.run(
        [sys.executable, "-P", *(a.format(plural=analysis.resources[0].plural) for a in args), "-p", "no:cacheprovider"],
        cwd=project / subdir,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    # Running the whole suite: 6 key/role checks + 5 for the one record type. Running one record
    # type's test file on its own: just its 5 checks.
    expected = 5 if mode == "python-test-file" else 11
    assert f"{expected} passed" in proc.stdout, proc.stdout
    report = (project / "TEST_RESULTS.md").read_text(encoding="utf-8")
    assert f"All {expected} checks passed" in report, report
    # Test artifacts land in the project root no matter where pytest was started.
    assert not (project / "tests" / "test.db").exists()
    assert not (project / "tests" / "data").exists()
    assert not (project / "tests" / "TEST_RESULTS.md").exists()


def _run_generated(project: Path) -> str:
    subprocess.run(
        [sys.executable, "-P", "-m", "pytest", "-q", "-p", "no:cacheprovider"],
        cwd=project,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return (project / "TEST_RESULTS.md").read_text(encoding="utf-8")


def test_report_explains_failed_checks(tmp_path: Path) -> None:
    """A broken generated API gets a report naming the failed check and why."""
    analysis = CASES[0]
    files = render_project(analysis, build_openapi(analysis))
    router = f"app/routers/{analysis.resources[0].plural}.py"
    files[router] = files[router].replace("status.HTTP_204_NO_CONTENT", "status.HTTP_200_OK")
    project = tmp_path / "project"
    write_project(project, files)
    report = _run_generated(project)
    assert "1 of 11 checks failed" in report, report
    assert "**Delete a todo**: Deleting a todo answered 200 instead of 204" in report, report


def test_report_explains_tests_that_cannot_start(tmp_path: Path) -> None:
    """If the tests cannot even start, the report says so and how to fix it."""
    analysis = CASES[0]
    files = render_project(analysis, build_openapi(analysis))
    del files["app/main.py"]
    project = tmp_path / "project"
    write_project(project, files)
    report = _run_generated(project)
    assert "The tests could not start" in report, report
    assert "pip install -r requirements.txt" in report, report
    assert "app.main" in report, report
