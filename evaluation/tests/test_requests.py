"""Checks that the evaluation set (evaluation/requests.json, S-7) is well-formed, so the scoring script (E-1)
can rely on it. It checks the file's shape, not the platform."""

import json
import re
from pathlib import Path

REQUESTS_FILE = Path(__file__).resolve().parents[1] / "requests.json"
KINDS = {"clear_one_table", "several_tables", "vague", "partly_supported", "out_of_scope"}
EXPECTS = {"build", "ask_first", "refuse"}
# "METHOD /path", the path made of lowercase words and {id} parts, e.g. "GET /books/{id}"
ENDPOINT = re.compile(r"^(GET|POST|PUT|DELETE) /[a-z_]+(/\{id\})?$")


def load() -> list[dict]:
    return json.loads(REQUESTS_FILE.read_text(encoding="utf-8"))["requests"]


def test_there_are_20_requests_with_unique_ids() -> None:
    requests = load()
    assert len(requests) == 20
    assert len({r["id"] for r in requests}) == 20
    assert len({r["request"] for r in requests}) == 20


def test_every_request_has_a_known_kind_and_expectation() -> None:
    for r in load():
        assert r["kind"] in KINDS, r["id"]
        assert r["expect"] in EXPECTS, r["id"]
        assert 10 <= len(r["request"]) <= 2000, r["id"]  # the platform's own input limits


def test_endpoints_are_written_the_same_way() -> None:
    for r in load():
        for endpoint in r.get("expected_endpoints", []):
            assert ENDPOINT.match(endpoint), (r["id"], endpoint)


def test_builds_say_what_they_must_produce_and_refusals_produce_nothing() -> None:
    for r in load():
        if r["expect"] == "build":
            assert r.get("expected_endpoints") or r.get("min_tables"), r["id"]
        if r["expect"] == "refuse":
            assert not r.get("expected_endpoints") and not r.get("min_tables"), r["id"]
        if r["kind"] == "partly_supported":
            assert r.get("not_included"), r["id"]


def test_each_table_has_its_five_standard_endpoints() -> None:
    for r in load():
        tables = {e.split("/")[1] for e in r.get("expected_endpoints", [])}
        for table in tables:
            for endpoint in [f"GET /{table}", f"POST /{table}", f"GET /{table}/{{id}}",
                             f"PUT /{table}/{{id}}", f"DELETE /{table}/{{id}}"]:
                assert endpoint in r["expected_endpoints"], (r["id"], endpoint)


def test_the_set_covers_every_kind() -> None:
    counts = {kind: sum(r["kind"] == kind for r in load()) for kind in KINDS}
    assert counts == {"clear_one_table": 8, "several_tables": 4, "vague": 4, "partly_supported": 2, "out_of_scope": 2}
