from __future__ import annotations

import ast
import json
import keyword
import re
from typing import Any

import yaml
from openapi_spec_validator import validate as validate_openapi_spec
from openapi_spec_validator.validation.exceptions import OpenAPIValidationError

from app.models import Analysis

MAX_WORDS = 200
HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}


def word_count(text: str) -> int:
    return len(text.split())


def validate_requirement(text: str) -> str | None:
    cleaned = text.strip()
    if len(cleaned) < 10:
        return "Please describe the API you need in a short paragraph."
    if word_count(cleaned) > MAX_WORDS:
        return f"Please keep the description under {MAX_WORDS} words."
    return None


MIN_FIELDS = 2
MAX_FIELDS = 10
MAX_RESOURCES = 8
_IDENT_RE = re.compile(r"^[a-z][a-z0-9_]*$")
# Names that would clash with the generated project's own routes, modules or columns.
RESERVED_NAMES = {
    "id", "health", "docs", "redoc", "openapi", "app", "tests", "routers",
    "models", "schemas", "auth", "db", "main", "support", "conftest",
}


def _bad_name(value: str) -> bool:
    return not _IDENT_RE.match(value) or keyword.iskeyword(value) or value in RESERVED_NAMES


def _resource_problems(resource, names: set[str]) -> list[str]:
    """Checks one record type. `names` holds every record type's singular name, for checking links."""
    problems: list[str] = []
    label = resource.plural.replace("_", " ")
    for kind, value in [("record type", resource.name), ("record type (plural)", resource.plural)]:
        if _bad_name(value):
            problems.append(f'"{value}" can\'t be used as a {kind} name. Please choose another name.')
    if resource.name == resource.plural:
        problems.append(f'The names for one and many "{label}" must be different (e.g. product / products).')
    if not MIN_FIELDS <= len(resource.fields) <= MAX_FIELDS:
        problems.append(
            f"Each record type needs between {MIN_FIELDS} and {MAX_FIELDS} details; {label} has {len(resource.fields)}."
        )
    seen: set[str] = set()
    for field in resource.fields:
        if _bad_name(field.name):
            problems.append(f'"{field.name}" can\'t be used as a detail name. Please choose another name.')
        if field.name in seen:
            problems.append(f'The detail "{field.name}" appears twice in {label}. Each detail needs its own name.')
        seen.add(field.name)
        if field.type == "link":
            if field.links_to not in names:
                problems.append(f'"{field.name}" in {label} links to a record type that does not exist.')
            elif field.links_to == resource.name:
                problems.append(f'"{field.name}" in {label} links {label} to itself, which is not supported yet.')
            if not field.name.endswith("_id"):
                problems.append(f'The link "{field.name}" in {label} must end with _id (e.g. classroom_id).')
    if not resource.value_fields:
        problems.append(f"{label.capitalize()} need at least one detail you fill in that is not a link.")
    return problems


def blueprint_problems(analysis: Analysis) -> list[str]:
    """Rule checks the LLM cannot override. Messages are shown to non-developers."""
    problems: list[str] = []
    if len(analysis.resources) > MAX_RESOURCES:
        problems.append(f"A design can have at most {MAX_RESOURCES} record types; this one has {len(analysis.resources)}.")
    names = [r.name for r in analysis.resources]
    plurals = [r.plural for r in analysis.resources]
    if len(set(names)) != len(names) or len(set(plurals)) != len(plurals) or set(names) & set(plurals):
        problems.append("Two record types have the same name. Each record type needs its own name.")
    for resource in analysis.resources:
        problems += _resource_problems(resource, set(names))
    # Links must not go round in a circle (A links to B, B links to A): there would be no record to add first.
    # Walk the creation order; a record type whose (real, non-self) link target is not placed yet is in a circle.
    placed: set[str] = set()
    for resource in analysis.in_creation_order():
        targets = {f.links_to for f in resource.link_fields if f.links_to in names and f.links_to != resource.name}
        if not targets <= placed:
            problems.append("The links between record types go round in a circle. Remove one of the links.")
            break
        placed.add(resource.name)
    return list(dict.fromkeys(problems))


def validate_openapi_yaml(text: str) -> None:
    try:
        spec = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ValueError(f"OpenAPI YAML could not be parsed: {exc}") from exc
    if not isinstance(spec, dict):
        raise ValueError("OpenAPI document must be a mapping.")
    try:
        validate_openapi_spec(spec)
    except OpenAPIValidationError as exc:
        raise ValueError(str(exc)) from exc
    except Exception as exc:  # validator versions differ slightly
        raise ValueError(str(exc)) from exc


def openapi_mismatches(text: str, analysis: Analysis) -> list[str]:
    """Compare an OpenAPI document against the routes and schemas the scaffold generates."""
    spec = yaml.safe_load(text) or {}
    errors: list[str] = []

    expected_paths: dict[str, set[str]] = {"/health": {"get"}}
    for resource in analysis.resources:
        expected_paths[f"/{resource.plural}"] = {"get", "post"}
        expected_paths[f"/{resource.plural}/{{item_id}}"] = {"get", "put", "delete"}
    paths = spec.get("paths") or {}
    for path, methods in expected_paths.items():
        if path not in paths:
            errors.append(f"Missing path {path}")
            continue
        actual = {m.lower() for m in (paths[path] or {}) if m.lower() in HTTP_METHODS}
        if actual != methods:
            errors.append(f"Path {path} must have methods {sorted(methods)}, found {sorted(actual)}")
    for path in paths:
        if path not in expected_paths:
            errors.append(f"Unexpected path {path}")

    schemas = (spec.get("components") or {}).get("schemas") or {}
    expected_schemas: dict[str, set[str]] = {}
    for resource in analysis.resources:
        user_names = {f.name for f in resource.user_fields}
        expected_schemas[resource.class_name] = {"id", *(f.name for f in resource.fields)}
        expected_schemas[f"{resource.class_name}Create"] = user_names
        expected_schemas[f"{resource.class_name}Update"] = user_names
    for schema_name, fields in expected_schemas.items():
        schema = schemas.get(schema_name)
        if not isinstance(schema, dict):
            errors.append(f"Missing schema components.schemas.{schema_name}")
            continue
        actual = set((schema.get("properties") or {}).keys())
        if actual != fields:
            errors.append(
                f"Schema {schema_name} must have properties {sorted(fields)}, found {sorted(actual)}"
            )

    security = (spec.get("components") or {}).get("securitySchemes") or {}
    key_scheme = security.get("ApiKeyAuth") or {}
    if key_scheme.get("in") != "header" or key_scheme.get("name") != "X-API-Key":
        errors.append("securitySchemes.ApiKeyAuth must be an X-API-Key header")
    return errors


_URL_RE = re.compile(r"http://localhost:8000(/[^\s'\"\\`()\[\]<>]*)?")
_METHOD_RE = re.compile(r"(?:-X|--request)\s+['\"]?([A-Za-z]+)")
_BODY_RE = re.compile(r"(?:-d|--data(?:-raw)?)\s+'([^']*)'")


def readme_problems(text: str, analysis: Analysis) -> list[str]:
    """Check a README against the generated API: required sections, real paths, real fields.
    Full curl examples are required for the first record type (in creation order); every other
    record type must at least be mentioned with its address."""
    first = analysis.in_creation_order()[0]
    plural = first.plural
    item_path = f"/{plural}/{{item_id}}"
    allowed_paths = {"", "/", "/health", "/docs", "/openapi.json"}
    fields_by_path: dict[str, set[str]] = {}
    for resource in analysis.resources:
        names = {f.name for f in resource.user_fields}
        for path in (f"/{resource.plural}", f"/{resource.plural}/{{item_id}}"):
            allowed_paths.add(path)
            fields_by_path[path] = names
    lowered = text.lower()
    problems: list[str] = []
    for resource in analysis.resources:
        if f"/{resource.plural}" not in lowered:
            problems.append(f"README never mentions /{resource.plural}")

    for needle, label in [
        ("start.bat", "how to start by double-clicking Start.bat"),
        ("start.command", "how to start by double-clicking Start.command"),
        ("docker compose up", "how to start with docker compose up"),
        ("x-api-key", "the X-API-Key header"),
        # Step 3: every project has its own two keys in .env
        ("editor_key", "the EDITOR_KEY (can change records)"),
        ("reader_key", "the READER_KEY (can only look)"),
        (".env", "where the keys are (the .env file)"),
        ("pytest", "how to run tests (pytest)"),
        ("pip install -r requirements.txt", "installing dependencies before running tests"),
        ("test_results.md", "where to read the plain-English test report (TEST_RESULTS.md)"),
        ("/docs", "a link to /docs"),
    ]:
        if needle not in lowered:
            problems.append(f"README is missing {label}")

    # The old shared default key no longer works; a README that mentions it would mislead people
    if "demo-api-key" in lowered:
        problems.append("README mentions demo-api-key, but there is no default key any more (keys are in .env)")

    plurals = "|".join(re.escape(r.plural) for r in analysis.resources)

    def normalize(path: str) -> str:
        path = path.split("?")[0]  # /students?classroom_id=1 is the list address with a filter
        path = path.rstrip("/.,:;") if path not in ("", "/") else path
        return re.sub(rf"^/({plurals})/[^/]+$", r"/\1/{item_id}", path)

    for match in _URL_RE.finditer(text):
        path = normalize(match.group(1) or "")
        if path not in allowed_paths:
            problems.append(f"README references a path that does not exist: {path}")

    seen: set[tuple[str, str]] = set()
    for segment in re.split(r"(?=\bcurl\s)", text)[1:]:
        segment = segment.split("```")[0]
        url = _URL_RE.search(segment)
        if not url:
            continue
        path = normalize(url.group(1) or "")
        method_match = _METHOD_RE.search(segment)
        method = method_match.group(1).upper() if method_match else "GET"
        seen.add((method, path))
        if path not in ("/health", "", "/") and "x-api-key" not in segment.lower():
            problems.append(f"curl {method} {path} is missing the X-API-Key header")
        for body in _BODY_RE.findall(segment):
            try:
                keys = set(json.loads(body))
            except (ValueError, TypeError):
                problems.append(f"curl {method} {path} has an invalid JSON body")
                continue
            unknown = keys - fields_by_path.get(path, set())
            if unknown:
                problems.append(f"curl {method} {path} uses unknown fields: {sorted(unknown)}")

    for method, path in [
        ("GET", "/health"),
        ("POST", f"/{plural}"),
        ("GET", f"/{plural}"),
        ("GET", item_path),
        ("PUT", item_path),
        ("DELETE", item_path),
    ]:
        if (method, path) not in seen:
            problems.append(f"README has no curl example for {method} {path}")
    return list(dict.fromkeys(problems))


def python_syntax_ok(source: str, filename: str) -> str | None:
    try:
        ast.parse(source, filename=filename)
    except SyntaxError as exc:
        return f"{filename}: {exc}"
    return None


def validate_python_files(files: dict[str, str]) -> list[str]:
    errors: list[str] = []
    for path, content in files.items():
        if path.endswith(".py"):
            err = python_syntax_ok(content, path)
            if err:
                errors.append(err)
    return errors


def analysis_to_dict(data: dict[str, Any]) -> dict[str, Any]:
    return data
