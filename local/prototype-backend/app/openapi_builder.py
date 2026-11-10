"""Builds the OpenAPI description from the design, without the LLM (also the fallback when the LLM fails).
One set of paths and schemas per record type; links are integer ids that point at another record type."""

from __future__ import annotations

from typing import Any

import yaml

from app.models import Analysis, FieldSpec, Resource

JSON_TYPES = {
    "str": ("string", None),
    "int": ("integer", None),
    "float": ("number", None),
    "bool": ("boolean", None),
    "datetime": ("string", "date-time"),
    "link": ("integer", None),
}

UNAUTHORIZED = {"description": "Invalid or missing API key"}
READ_ONLY_KEY = {"description": "This key can only look (use the editor key to change records)"}


def _prop(field: FieldSpec) -> dict[str, Any]:
    json_type, fmt = JSON_TYPES[field.type]
    description = field.description or field.name
    if field.type == "link":
        description = f"{description} (the id of a {field.links_to})"
    schema: dict[str, Any] = {"type": json_type, "description": description}
    if fmt:
        schema["format"] = fmt
    return schema


def _ref(name: str) -> dict[str, Any]:
    return {"$ref": f"#/components/schemas/{name}"}


def _json(schema: dict[str, Any]) -> dict[str, Any]:
    return {"application/json": {"schema": schema}}


ITEM_ID = {"name": "item_id", "in": "path", "required": True, "schema": {"type": "integer"}}


def _paths(resource: Resource, has_children: bool) -> dict[str, Any]:
    name, plural, cls = resource.name, resource.plural, resource.class_name
    # Optional filters on the list: /students?classroom_id=3
    filters = [
        {"name": f.name, "in": "query", "required": False, "schema": {"type": "integer"},
         "description": f"Only {plural.replace('_', ' ')} linked to this {f.links_to}"}
        for f in resource.link_fields
    ]
    bad_link = {"422": {"description": "Invalid details, or a linked record that does not exist"}}
    delete_responses: dict[str, Any] = {"204": {"description": "Deleted"}, "401": UNAUTHORIZED,
                                        "403": READ_ONLY_KEY, "404": {"description": "Not found"}}
    if has_children:
        delete_responses["409"] = {"description": "Still used by linked records; remove those first"}
    return {
        f"/{plural}": {
            "get": {
                "operationId": f"list_{plural}",
                "summary": f"List {plural}",
                **({"parameters": filters} if filters else {}),
                "responses": {
                    "200": {"description": "List of items", "content": _json({"type": "array", "items": _ref(cls)})},
                    "401": UNAUTHORIZED,
                },
            },
            "post": {
                "operationId": f"create_{name}",
                "summary": f"Create {name}",
                "requestBody": {"required": True, "content": _json(_ref(f"{cls}Create"))},
                "responses": {
                    "201": {"description": "Created", "content": _json(_ref(cls))},
                    "401": UNAUTHORIZED,
                    "403": READ_ONLY_KEY,
                    **bad_link,
                },
            },
        },
        f"/{plural}/{{item_id}}": {
            "get": {
                "operationId": f"get_{name}",
                "summary": f"Get {name} by id",
                "parameters": [ITEM_ID],
                "responses": {
                    "200": {"description": "Item", "content": _json(_ref(cls))},
                    "401": UNAUTHORIZED,
                    "404": {"description": "Not found"},
                },
            },
            "put": {
                "operationId": f"update_{name}",
                "summary": f"Update {name}",
                "parameters": [ITEM_ID],
                "requestBody": {"required": True, "content": _json(_ref(f"{cls}Update"))},
                "responses": {
                    "200": {"description": "Updated", "content": _json(_ref(cls))},
                    "401": UNAUTHORIZED,
                    "403": READ_ONLY_KEY,
                    "404": {"description": "Not found"},
                    **bad_link,
                },
            },
            "delete": {
                "operationId": f"delete_{name}",
                "summary": f"Delete {name}",
                "parameters": [ITEM_ID],
                "responses": delete_responses,
            },
        },
    }


def _schemas(resource: Resource) -> dict[str, Any]:
    cls = resource.class_name
    return {
        cls: {
            "type": "object",
            "properties": {"id": {"type": "integer", "description": "Auto-generated identifier"},
                           **{f.name: _prop(f) for f in resource.fields}},
            "required": ["id", *[f.name for f in resource.fields]],
        },
        f"{cls}Create": {
            "type": "object",
            "properties": {f.name: _prop(f) for f in resource.user_fields},
            "required": [f.name for f in resource.user_fields if f.required],
        },
        f"{cls}Update": {
            "type": "object",
            "properties": {f.name: _prop(f) for f in resource.user_fields},
        },
    }


def build_openapi(analysis: Analysis) -> str:
    paths: dict[str, Any] = {
        "/health": {
            "get": {
                "operationId": "health",
                "summary": "Health check",
                "security": [],
                "responses": {
                    "200": {
                        "description": "Service is running",
                        "content": _json({"type": "object", "properties": {"status": {"type": "string"}},
                                          "required": ["status"]}),
                    }
                },
            }
        }
    }
    schemas: dict[str, Any] = {}
    for resource in analysis.in_creation_order():
        paths.update(_paths(resource, has_children=bool(analysis.children_of(resource.name))))
        schemas.update(_schemas(resource))

    spec: dict[str, Any] = {
        "openapi": "3.1.0",
        "info": {"title": analysis.title, "version": "1.0.0", "description": analysis.description},
        "servers": [{"url": "http://localhost:8000"}],
        "security": [{"ApiKeyAuth": []}],
        "paths": paths,
        "components": {
            "securitySchemes": {
                "ApiKeyAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-API-Key",
                    "description": "EDITOR_KEY (look and change) or READER_KEY (look only), from the .env file",
                }
            },
            "schemas": schemas,
        },
    }
    return yaml.safe_dump(spec, sort_keys=False, allow_unicode=True)
