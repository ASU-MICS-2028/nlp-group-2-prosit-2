from pathlib import Path

from app.llm import parse_markdown_text
from app.models import Analysis, FieldSpec
from app.openapi_builder import build_openapi
from app.packager import write_project
from app.scaffold import render_project, render_readme
from app.validators import openapi_mismatches, readme_problems, validate_openapi_yaml, validate_python_files


def test_todo_scaffold_is_valid(tmp_path: Path) -> None:
    """Generated project has valid OpenAPI, valid Python syntax, and its key files."""
    analysis = Analysis(
        title="Todo API",
        description="Tasks with title, description, and completed status.",
        resource_name="todo",
        resource_plural="todos",
        fields=[
            FieldSpec(name="title", type="str", required=True, description="Task title"),
            FieldSpec(name="description", type="str", required=False, description="Details"),
            FieldSpec(name="completed", type="bool", required=False, default="false", description="Done"),
        ],
    )
    openapi = build_openapi(analysis)
    validate_openapi_yaml(openapi)
    files = render_project(analysis, openapi)
    assert not validate_python_files(files)
    write_project(tmp_path / "project", files)
    assert (tmp_path / "project" / "docker-compose.yml").exists()
    assert (tmp_path / "project" / "openapi.yaml").exists()


def _todo_analysis() -> Analysis:
    return Analysis(
        title="Todo API",
        description="Tasks.",
        resource_name="todo",
        resource_plural="todos",
        fields=[
            FieldSpec(name="title", type="str", required=True),
            FieldSpec(name="completed", type="bool", required=False, default="false"),
        ],
    )


def test_builder_openapi_matches_scaffold() -> None:
    """The fallback OpenAPI builder matches the routes and schemas the code serves."""
    analysis = _todo_analysis()
    assert openapi_mismatches(build_openapi(analysis), analysis) == []


def test_openapi_drift_is_detected() -> None:
    """Renamed paths or schemas in an LLM-written spec are flagged."""
    analysis = _todo_analysis()
    drifted = build_openapi(analysis).replace("{item_id}", "{todo_id}").replace("TodoCreate", "NewTodo")
    errors = openapi_mismatches(drifted, analysis)
    assert any("/todos/{item_id}" in e for e in errors)
    assert any("Unexpected path /todos/{todo_id}" in e for e in errors)
    assert any("TodoCreate" in e for e in errors)


def test_template_readme_passes_check() -> None:
    """The built-in README template passes the README checks."""
    analysis = _todo_analysis()
    assert readme_problems(render_readme(analysis), analysis) == []


def test_readme_hallucinations_are_detected() -> None:
    """README checks catch unknown fields, fake paths, and missing API key headers."""
    analysis = _todo_analysis()
    readme = render_readme(analysis)
    bad = (
        readme.replace('"title": "Sample title"', '"name": "Sample title"')
        .replace("curl http://localhost:8000/todos/1 -H", "curl http://localhost:8000/tasks/1 -H")
        .replace('curl http://localhost:8000/todos -H "X-API-Key: YOUR_READER_KEY"', "curl http://localhost:8000/todos")
    )
    problems = readme_problems(bad, analysis)
    assert any("unknown fields: ['name']" in p for p in problems)
    assert any("does not exist: /tasks/1" in p for p in problems)
    assert any("GET /todos is missing the X-API-Key header" in p for p in problems)
    assert any("no curl example for GET /todos/{item_id}" in p for p in problems)


def test_fenced_markdown_readme_keeps_inner_code_blocks() -> None:
    """Unwrapping an outer markdown code fence keeps the README's own code blocks."""
    analysis = _todo_analysis()
    readme = render_readme(analysis)
    unwrapped = parse_markdown_text(f"```markdown\n{readme}\n```")
    assert unwrapped == readme.strip()
    assert readme_problems(unwrapped, analysis) == []
    assert parse_markdown_text(readme) == readme.strip()


def test_markdown_links_are_not_flagged() -> None:
    """Markdown and angle-bracket links to /docs and /health are not flagged."""
    analysis = _todo_analysis()
    readme = render_readme(analysis) + (
        "\nDocs: [http://localhost:8000/docs](http://localhost:8000/docs) "
        "and <http://localhost:8000/health>\n"
    )
    assert readme_problems(readme, analysis) == []
