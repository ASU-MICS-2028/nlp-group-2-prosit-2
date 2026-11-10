"""Writes the Python code of a generated project, for one or more linked record types.

Built from plain lists of lines (not one big template), so each record type and each link is easy to follow.
Generated layout:
  app/models.py              one database table per record type; a link is a column like classroom_id
  app/schemas.py             what can be sent and what comes back, per record type
  app/routers/<plural>.py    add / list / open / edit / delete, plus link checks and filters
  app/main.py                puts the routers together
  tests/support.py           test client, keys, and new_<record>() / create_<record>() helpers
  tests/test_access.py       keys and roles (6 checks)
  tests/test_<plural>.py     5 checks per record type, plus 3 per link
"""

from __future__ import annotations

from app.models import Analysis, FieldSpec, Resource

TYPE_HINTS = {"str": "str", "int": "int", "float": "float", "bool": "bool", "datetime": "datetime", "link": "int"}

# Sample values used in tests and README examples, as Python source and as JSON text
_PY_SAMPLES = {"int": "1", "float": "9.99", "bool": "True", "datetime": '"2026-01-15T10:00:00Z"'}
_JSON_SAMPLES = {"int": "1", "float": "9.99", "bool": "true", "datetime": '"2026-01-15T10:00:00Z"'}

TESTS_FOR_ACCESS = 6
TESTS_PER_RECORD_TYPE = 5
TESTS_PER_LINK = 3


def count_checks(analysis: Analysis) -> int:
    """How many checks a generated project has (the frontend shows the same number on the plan)."""
    links = sum(len(r.link_fields) for r in analysis.resources)
    return TESTS_FOR_ACCESS + TESTS_PER_RECORD_TYPE * len(analysis.resources) + TESTS_PER_LINK * links


def words(name: str) -> str:
    return name.replace("_", " ")


def _target(analysis: Analysis, field: FieldSpec) -> Resource:
    target = analysis.resource(field.links_to or "")
    if target is None:  # the validator stops this before any code is written
        raise ValueError(f"{field.name} links to a record type that does not exist")
    return target


# --------------------------------------------------------------------------- sample values


def sample_py(field: FieldSpec) -> str:
    if field.type == "str":
        return f'"Sample {words(field.name)}"'
    return _PY_SAMPLES[field.type]


def sample_json(resource: Resource) -> str:
    """A JSON body for README examples (value details only; links are shown separately)."""
    parts = []
    for field in resource.value_fields:
        value = f'"Sample {words(field.name)}"' if field.type == "str" else _JSON_SAMPLES[field.type]
        parts.append(f'"{field.name}": {value}')
    return "{ " + ", ".join(parts) + " }"


def update_py(resource: Resource) -> tuple[str, str | None]:
    """A one-detail edit for tests, and the name of the detail checked afterwards (text only)."""
    field = resource.value_fields[0]
    edits = {"str": f'"Updated {words(field.name)}"', "int": "2", "float": "19.99", "bool": "False",
             "datetime": '"2026-02-01T09:00:00Z"'}
    return "{" + f'"{field.name}": {edits[field.type]}' + "}", field.name if field.type == "str" else None


# --------------------------------------------------------------------------- models and schemas


def _needs_datetime(analysis: Analysis) -> bool:
    return any(f.type == "datetime" for r in analysis.resources for f in r.fields)


def _value_line(field: FieldSpec, optional: bool) -> str:
    """One detail line for a schema or a table (links are handled separately)."""
    hint = TYPE_HINTS[field.type] + (" | None" if optional else "")
    if field.type == "datetime" and field.auto:
        return f"    {field.name}: {hint} = Field(default_factory=lambda: datetime.now(timezone.utc))"
    if field.type == "bool" and (optional or field.default is not None):
        default = "False" if (field.default or "false").lower() == "false" else "True"
        return f"    {field.name}: {hint} = {default}"
    if optional:
        return f"    {field.name}: {hint} = None"
    return f"    {field.name}: {hint}"


def _table_line(analysis: Analysis, field: FieldSpec) -> str:
    if field.type != "link":
        return _value_line(field, optional=(not field.required) or field.auto)
    # A link is the id of a row in the other table. index=True makes "all students of classroom 3" fast.
    target = _target(analysis, field).plural
    if field.required:
        return f'    {field.name}: int = Field(foreign_key="{target}.id", index=True)'
    return f'    {field.name}: int | None = Field(default=None, foreign_key="{target}.id", index=True)'


def models_py(analysis: Analysis) -> str:
    lines = []
    if _needs_datetime(analysis):
        lines.append("from datetime import datetime, timezone")
    lines += ["from sqlmodel import Field, SQLModel", ""]
    for resource in analysis.in_creation_order():
        lines += [
            "",
            f"class {resource.class_name}(SQLModel, table=True):",
            f'    __tablename__ = "{resource.plural}"',
            "    id: int | None = Field(default=None, primary_key=True)",
        ]
        lines += [_table_line(analysis, field) for field in resource.fields]
    return "\n".join(lines) + "\n"


def schemas_py(analysis: Analysis) -> str:
    lines = []
    if _needs_datetime(analysis):
        lines.append("from datetime import datetime")
    lines += ["from sqlmodel import SQLModel", ""]
    for resource in analysis.in_creation_order():
        cls = resource.class_name
        lines += ["", f"class {cls}Create(SQLModel):"]
        lines += [_value_line(f, optional=not f.required) for f in resource.user_fields]
        lines += ["", "", f"class {cls}Update(SQLModel):"]
        lines += [_value_line(f, optional=True) for f in resource.user_fields]
        lines += ["", "", f"class {cls}Read(SQLModel):", "    id: int"]
        for field in resource.fields:
            hint = TYPE_HINTS[field.type] + (" | None" if not field.required and not field.auto else "")
            lines.append(f"    {field.name}: {hint}")
        lines.append("")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- routers


def _link_check_lines(analysis: Analysis, resource: Resource) -> list[str]:
    lines = [
        "",
        "",
        "def _check_links(db: Session, values: dict) -> None:",
        '    """Every link must point at a record that exists (SQLite does not check this by itself)."""',
    ]
    for field in resource.link_fields:
        target = _target(analysis, field)
        lines += [
            f'    if values.get("{field.name}") is not None and db.get({target.class_name}, values["{field.name}"]) is None:',
            "        raise HTTPException(",
            "            status_code=422,",
            f'            detail=f"There is no {words(target.name)} with id {{values[\'{field.name}\']}}.",',
            "        )",
        ]
    return lines


def _delete_guard_lines(analysis: Analysis, resource: Resource) -> list[str]:
    """Refuse to delete a record that other records still link to (409), instead of leaving them broken."""
    lines = []
    for child, field in analysis.children_of(resource.name):
        lines += [
            f"    in_use = db.exec(select(func.count()).select_from({child.class_name}).where({child.class_name}.{field.name} == item_id)).one()",
            "    if in_use:",
            "        raise HTTPException(",
            "            status_code=409,",
            f'            detail=f"This {words(resource.name)} is still used by {{in_use}} {words(child.plural)}. '
            f'Delete or change those first.",',
            "        )",
        ]
    return lines


def router_py(analysis: Analysis, resource: Resource) -> str:
    cls, plural = resource.class_name, resource.plural
    links = resource.link_fields
    needed = {cls} | {_target(analysis, f).class_name for f in links}
    needed |= {child.class_name for child, _ in analysis.children_of(resource.name)}
    sqlmodel_names = "Session, func, select" if analysis.children_of(resource.name) else "Session, select"

    lines = [
        "from __future__ import annotations",
        "",
        "from fastapi import APIRouter, Depends, HTTPException, status",
        f"from sqlmodel import {sqlmodel_names}",
        "",
        "from app.auth import require_editor, require_reader",
        "from app.db import get_session",
        f"from app.models import {', '.join(sorted(needed))}",
        f"from app.schemas import {cls}Create, {cls}Read, {cls}Update",
        "",
        f'router = APIRouter(prefix="/{plural}", tags=["{plural}"])',
        "",
        "# Looking needs the reader key (or the editor key). Adding, editing and deleting need the editor key.",
        "CAN_LOOK = [Depends(require_reader)]",
        "CAN_CHANGE = [Depends(require_editor)]",
    ]
    if links:
        lines += _link_check_lines(analysis, resource)

    # List, with an optional filter per link: /students?classroom_id=3
    filters = "".join(f"{f.name}: int | None = None, " for f in links)
    lines += [
        "",
        "",
        f'@router.get("", response_model=list[{cls}Read], dependencies=CAN_LOOK)',
        f"def list_items({filters}db: Session = Depends(get_session)) -> list[{cls}]:",
        f"    query = select({cls})",
    ]
    for field in links:
        lines += [f"    if {field.name} is not None:", f"        query = query.where({cls}.{field.name} == {field.name})"]
    lines.append("    return db.exec(query).all()")

    lines += [
        "",
        "",
        f'@router.post("", response_model={cls}Read, status_code=status.HTTP_201_CREATED, dependencies=CAN_CHANGE)',
        f"def create_item(body: {cls}Create, db: Session = Depends(get_session)) -> {cls}:",
        "    payload = body.model_dump()",
    ]
    if any(f.type == "datetime" and f.auto for f in resource.fields):
        lines.append("    from datetime import datetime, timezone")
        lines += [f'    payload["{f.name}"] = datetime.now(timezone.utc)' for f in resource.auto_fields if f.type == "datetime"]
    if links:
        lines.append("    _check_links(db, payload)")
    lines += [
        f"    item = {cls}(**payload)",
        "    db.add(item)",
        "    db.commit()",
        "    db.refresh(item)",
        "    return item",
        "",
        "",
        f'@router.get("/{{item_id}}", response_model={cls}Read, dependencies=CAN_LOOK)',
        f"def get_item(item_id: int, db: Session = Depends(get_session)) -> {cls}:",
        f"    item = db.get({cls}, item_id)",
        "    if not item:",
        f'        raise HTTPException(status_code=404, detail="{cls} not found")',
        "    return item",
        "",
        "",
        f'@router.put("/{{item_id}}", response_model={cls}Read, dependencies=CAN_CHANGE)',
        f"def update_item(item_id: int, body: {cls}Update, db: Session = Depends(get_session)) -> {cls}:",
        f"    item = db.get({cls}, item_id)",
        "    if not item:",
        f'        raise HTTPException(status_code=404, detail="{cls} not found")',
        "    updates = body.model_dump(exclude_unset=True)",
    ]
    if links:
        lines.append("    _check_links(db, updates)")
    lines += [
        "    for key, value in updates.items():",
        "        setattr(item, key, value)",
        "    db.add(item)",
        "    db.commit()",
        "    db.refresh(item)",
        "    return item",
        "",
        "",
        f'@router.delete("/{{item_id}}", status_code=status.HTTP_204_NO_CONTENT, dependencies=CAN_CHANGE)',
        "def delete_item(item_id: int, db: Session = Depends(get_session)) -> None:",
        f"    item = db.get({cls}, item_id)",
        "    if not item:",
        f'        raise HTTPException(status_code=404, detail="{cls} not found")',
    ]
    lines += _delete_guard_lines(analysis, resource)
    lines += ["    db.delete(item)", "    db.commit()", ""]
    return "\n".join(lines)


def main_py(analysis: Analysis) -> str:
    ordered = analysis.in_creation_order()
    lines = [
        "from __future__ import annotations",
        "",
        "from contextlib import asynccontextmanager",
        "",
        "from fastapi import FastAPI",
        "",
        "from app.db import init_db",
    ]
    lines += [f"from app.routers.{r.plural} import router as {r.plural}_router" for r in ordered]
    lines += [
        "",
        "",
        "@asynccontextmanager",
        "async def lifespan(_app: FastAPI):",
        "    init_db()",
        "    yield",
        "",
        "",
        "app = FastAPI(",
        f"    title={analysis.title!r},",
        f"    description={analysis.description!r},",
        '    version="1.0.0",',
        "    lifespan=lifespan,",
        ")",
    ]
    lines += [f"app.include_router({r.plural}_router)" for r in ordered]
    lines += [
        "",
        "",
        '@app.get("/health")',
        "def health() -> dict[str, str]:",
        '    return {"status": "ok"}',
        "",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------- tests


def support_py(analysis: Analysis) -> str:
    lines = [
        '"""Shared test helpers: the client, the two keys, and for each record type:',
        "new_<record>()    a valid body to send (it first adds anything the record links to)",
        'create_<record>() adds one and returns it."""',
        "",
        "from fastapi.testclient import TestClient",
        "",
        "from app.db import init_db",
        "from app.main import app",
        "",
        "init_db()",
        "client = TestClient(app)",
        "# The editor key can do everything; the reader key can only look (keys are set in conftest.py)",
        'HEADERS = {"X-API-Key": "test-editor-key-0123456789"}',
        'READER = {"X-API-Key": "test-reader-key-0123456789"}',
    ]
    for resource in analysis.in_creation_order():
        name, plural = resource.name, resource.plural
        lines += ["", "", f"def new_{name}(**changes) -> dict:", "    payload = {"]
        lines += [f'        "{f.name}": {sample_py(f)},' for f in resource.value_fields]
        lines.append("    }")
        for field in resource.link_fields:
            lines.append(f'    payload["{field.name}"] = create_{field.links_to}()["id"]')
        lines += [
            "    payload.update(changes)",
            "    return payload",
            "",
            "",
            f"def create_{name}(**changes) -> dict:",
            f"    created = client.post(\"/{plural}\", json=new_{name}(**changes), headers=HEADERS)",
            "    assert created.status_code == 201, (",
            f'        f"Adding a {words(name)} answered {{created.status_code}} instead of 201 (Created): {{created.text}}"',
            "    )",
            "    return created.json()",
        ]
    return "\n".join(lines) + "\n"


_RUN_DIRECTLY = [
    "import sys",
    "",
    'if __name__ == "__main__":',
    "    # Run via pytest when started directly (`python tests/test_x.py` or an editor's Run button),",
    "    # so pytest.ini puts the project root on sys.path and conftest.py sets up the test database.",
    "    import pytest",
    "",
    "    sys.exit(pytest.main([__file__, \"-q\"]))",
    "",
]


def access_tests_py(analysis: Analysis) -> str:
    """Keys and roles, checked on the first record type (one that links to nothing)."""
    first = analysis.in_creation_order()[0]
    plural, name, nouns = first.plural, first.name, words(first.plural)
    edit, _ = update_py(first)
    lines = _RUN_DIRECTLY + [
        f"from tests.support import HEADERS, READER, client, create_{name}, new_{name}",
        "",
        "# Each docstring reads \"Check name: what it means for you\"; conftest.py turns them into TEST_RESULTS.md.",
        "",
        "",
        "def test_health() -> None:",
        '    """API is running: The API starts and answers its health check."""',
        '    response = client.get("/health")',
        '    assert response.status_code == 200, f"Health check answered {response.status_code} instead of 200 (OK)"',
        '    assert response.json()["status"] == "ok", "Health check did not report status ok"',
        "",
        "",
        "def test_missing_api_key() -> None:",
        '    """Data is protected: Requests without the API key are refused."""',
        f'    response = client.get("/{plural}")',
        "    assert response.status_code == 401, (",
        '        f"A request without the API key answered {response.status_code} instead of 401 (Unauthorized)"',
        "    )",
        "",
        "",
        "def test_wrong_api_key() -> None:",
        '    """Wrong keys are refused: A made-up key cannot see your data."""',
        f'    response = client.get("/{plural}", headers={{"X-API-Key": "made-up-key-0123456789"}})',
        '    assert response.status_code == 401, f"A made-up key answered {response.status_code} instead of 401 (Unauthorized)"',
        "",
        "",
        "def test_reader_can_look() -> None:",
        f'    """Read-only key can look: The READER_KEY can see all {nouns} and open one."""',
        f'    item_id = create_{name}()["id"]',
        f'    listed = client.get("/{plural}", headers=READER)',
        f'    assert listed.status_code == 200, f"The reader key could not list {nouns}: {{listed.status_code}}"',
        f'    opened = client.get(f"/{plural}/{{item_id}}", headers=READER)',
        f'    assert opened.status_code == 200, f"The reader key could not open a {words(name)}: {{opened.status_code}}"',
        "",
        "",
        "def test_reader_cannot_change() -> None:",
        f'    """Read-only key cannot change: The READER_KEY cannot add, edit or delete {nouns}."""',
        f'    item_id = create_{name}()["id"]',
        "    attempts = {",
        f'        "add": client.post("/{plural}", json=new_{name}(), headers=READER),',
        f'        "edit": client.put(f"/{plural}/{{item_id}}", json={edit}, headers=READER),',
        f'        "delete": client.delete(f"/{plural}/{{item_id}}", headers=READER),',
        "    }",
        "    for action, response in attempts.items():",
        "        assert response.status_code == 403, (",
        '            f"The reader key tried to {action} and got {response.status_code} instead of 403 (Forbidden)"',
        "        )",
        f'    still_there = client.get(f"/{plural}/{{item_id}}", headers=HEADERS)',
        f'    assert still_there.status_code == 200, "A reader key managed to delete a {words(name)}"',
        "",
        "",
        "def test_no_keys_set_up(monkeypatch) -> None:",
        '    """No default key: If no keys are set up, the API refuses everything instead of letting anyone in."""',
        '    monkeypatch.delenv("EDITOR_KEY")',
        f'    response = client.get("/{plural}", headers=HEADERS)',
        "    assert response.status_code == 503, (",
        '        f"With no keys set up the API answered {response.status_code} instead of 503 (refusing everything)"',
        "    )",
        "",
    ]
    return "\n".join(lines)


def _crud_test_lines(resource: Resource) -> list[str]:
    name, plural, noun, nouns = resource.name, resource.plural, words(resource.name), words(resource.plural)
    edit, checked = update_py(resource)
    edit_check = (
        [f'    assert updated.json()["{checked}"] == {edit}["{checked}"], "The edit was not saved"'] if checked else []
    )
    return [
        "",
        "",
        f"def test_add_{name}() -> None:",
        f'    """Add a {noun}: You can add a new {noun} and it gets an id."""',
        f'    assert "id" in create_{name}(), "The new {noun} came back without an id"',
        "",
        "",
        f"def test_list_{plural}() -> None:",
        f'    """See all {nouns}: A newly added {noun} appears in the list."""',
        f'    item_id = create_{name}()["id"]',
        f'    listed = client.get("/{plural}", headers=HEADERS)',
        f'    assert listed.status_code == 200, f"Listing {nouns} answered {{listed.status_code}} instead of 200 (OK)"',
        f'    assert any(row["id"] == item_id for row in listed.json()), "The new {noun} is missing from the list"',
        "",
        "",
        f"def test_open_{name}() -> None:",
        f'    """Open one {noun}: You can open a single {noun} by its id."""',
        f'    item_id = create_{name}()["id"]',
        f'    fetched = client.get(f"/{plural}/{{item_id}}", headers=HEADERS)',
        f'    assert fetched.status_code == 200, f"Opening a {noun} answered {{fetched.status_code}} instead of 200 (OK)"',
        f'    assert fetched.json()["id"] == item_id, "Opening a {noun} returned a different {noun}"',
        "",
        "",
        f"def test_edit_{name}() -> None:",
        f'    """Edit a {noun}: Changes to a {noun} are saved."""',
        f'    item_id = create_{name}()["id"]',
        f'    updated = client.put(f"/{plural}/{{item_id}}", json={edit}, headers=HEADERS)',
        "    assert updated.status_code == 200, (",
        f'        f"Editing a {noun} answered {{updated.status_code}} instead of 200 (OK): {{updated.text}}"',
        "    )",
        *edit_check,
        "",
        "",
        f"def test_delete_{name}() -> None:",
        f'    """Delete a {noun}: A deleted {noun} is really gone."""',
        f'    item_id = create_{name}()["id"]',
        f'    deleted = client.delete(f"/{plural}/{{item_id}}", headers=HEADERS)',
        f'    assert deleted.status_code == 204, f"Deleting a {noun} answered {{deleted.status_code}} instead of 204"',
        f'    missing = client.get(f"/{plural}/{{item_id}}", headers=HEADERS)',
        f'    assert missing.status_code == 404, "The {noun} could still be opened after it was deleted"',
    ]


def _link_test_lines(analysis: Analysis, resource: Resource, field: FieldSpec) -> list[str]:
    name, plural, noun, nouns = resource.name, resource.plural, words(resource.name), words(resource.plural)
    target = _target(analysis, field)
    link = field.name.removesuffix("_id")  # e.g. classroom (or home_team for home_team_id)
    other = words(target.name)
    return [
        "",
        "",
        f"def test_{name}_needs_a_real_{link}() -> None:",
        f'    """{nouns.capitalize()} need a real {words(link)}: A {noun} cannot point at a {other} that does not exist."""',
        f'    response = client.post("/{plural}", json=new_{name}({field.name}=999999), headers=HEADERS)',
        "    assert response.status_code == 422, (",
        f'        f"A {noun} with a {other} that does not exist answered {{response.status_code}} instead of 422"',
        "    )",
        "",
        "",
        f"def test_find_{plural}_by_{link}() -> None:",
        f'    """Find {nouns} by {words(link)}: Listing {nouns} for one {other} shows only theirs."""',
        f"    mine, other = create_{name}(), create_{name}()",
        f'    listed = client.get("/{plural}", params={{"{field.name}": mine["{field.name}"]}}, headers=HEADERS)',
        '    ids = [row["id"] for row in listed.json()]',
        f'    assert mine["id"] in ids and other["id"] not in ids, "The {other} filter returned the wrong {nouns}"',
        "",
        "",
        f"def test_{link}_in_use_by_{plural}_cannot_be_deleted() -> None:",
        f'    """{other.capitalize()} in use is kept: A {other} that {nouns} still point at cannot be deleted."""',
        f"    item = create_{name}()",
        f'    response = client.delete(f"/{target.plural}/{{item[\'{field.name}\']}}", headers=HEADERS)',
        "    assert response.status_code == 409, (",
        f'        f"Deleting a {other} still used by a {noun} answered {{response.status_code}} instead of 409"',
        "    )",
        f'    assert client.get(f"/{plural}/{{item[\'id\']}}", headers=HEADERS).status_code == 200',
    ]


def resource_tests_py(analysis: Analysis, resource: Resource) -> str:
    imports = {"HEADERS", "client", f"create_{resource.name}"}
    if resource.link_fields:
        imports.add(f"new_{resource.name}")
    lines = _RUN_DIRECTLY + [f"from tests.support import {', '.join(sorted(imports))}"]
    lines += _crud_test_lines(resource)
    for field in resource.link_fields:
        lines += _link_test_lines(analysis, resource, field)
    return "\n".join(lines) + "\n"
