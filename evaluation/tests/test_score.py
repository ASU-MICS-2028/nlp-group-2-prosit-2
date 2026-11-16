"""Tests for the scoring script (E-1). A pretend builder stands in for Gemini, so no request is sent.

evaluation/AGENTS.md asks for: a request that fails, a timeout, a malformed result, and an empty set."""

import asyncio

from backend.builder import BuildResult
from evaluation import score

BOOKS = {
    "id": "r01",
    "kind": "clear_one_table",
    "expect": "build",
    "request": "A bookshop API.",
    "expected_endpoints": ["GET /books", "POST /books", "GET /books/{id}", "PUT /books/{id}", "DELETE /books/{id}"],
}
REFUSE = {"id": "r20", "kind": "out_of_scope", "expect": "refuse", "request": "Collect everyone's data."}

# What the builder writes, cut down to what the scorer reads.
MAIN_PY = """
@app.get("/books", summary="See all books")
@app.post("/books", status_code=201)
@app.get("/books/{book_id}")
@app.put("/books/{book_id}")
@app.delete("/books/{book_id}", status_code=204)
"""
DATABASE_PY = "CREATE TABLE IF NOT EXISTS books (id INTEGER PRIMARY KEY)"
GOOD_FILES = {"app/main.py": MAIN_PY, "app/database.py": DATABASE_PY}


def pretend(result: BuildResult, tries: int = 1, wait: float = 0):
    # A pretend builder: reports `tries` whole tries (like agent/retry.py does), then hands back `result`.
    async def build(request, report):
        for attempt in range(1, tries + 1):
            report({"status": "working", "attempt": attempt, "max_attempts": 3})
        await asyncio.sleep(wait)
        return result

    return build


def run(spec, build, time_limit=5):
    return asyncio.run(score.score_one(spec, build, time_limit))


def test_a_ready_build_with_every_endpoint_passes():
    result = run(BOOKS, pretend(BuildResult("ready", "All tests pass.", GOOD_FILES)))
    assert result.outcome == "pass"
    assert result.retries == 0
    assert result.tables == 1


def test_retries_count_the_extra_tries():
    result = run(BOOKS, pretend(BuildResult("ready", "All tests pass.", GOOD_FILES), tries=3))
    assert result.retries == 2


def test_a_failed_build_fails():
    failed = BuildResult("failed", "The tests still fail after 3 tries.", GOOD_FILES, kind="tests_failed")
    result = run(BOOKS, pretend(failed))
    assert result.outcome == "fail"
    assert "tests still fail" in result.reason


def test_the_free_tier_limit_is_counted_apart_from_failures():
    busy = BuildResult("failed", "The AI service is busy.", {}, kind="service_busy")
    assert run(BOOKS, pretend(busy)).outcome == "limit"


def test_a_missing_endpoint_fails_and_is_named():
    files = {"app/main.py": MAIN_PY.replace('@app.delete("/books/{book_id}", status_code=204)', "")}
    result = run(BOOKS, pretend(BuildResult("ready", "All tests pass.", files)))
    assert result.outcome == "fail"
    assert result.missing_endpoints == ["DELETE /books/{id}"]


def test_singular_names_and_other_parameter_names_still_match():
    main_py = MAIN_PY.replace("/books", "/book").replace("{book_id}", "{id}")
    result = run(BOOKS, pretend(BuildResult("ready", "All tests pass.", {"app/main.py": main_py})))
    assert result.outcome == "pass"


def test_too_few_tables_fails():
    spec = {**BOOKS, "min_tables": 3}
    result = run(spec, pretend(BuildResult("ready", "All tests pass.", GOOD_FILES)))
    assert result.outcome == "fail"
    assert "Only 1 tables" in result.reason


def test_a_malformed_result_with_no_main_py_fails_instead_of_crashing():
    result = run(BOOKS, pretend(BuildResult("ready", "All tests pass.", {"notes.txt": "hello"})))
    assert result.outcome == "fail"
    assert len(result.missing_endpoints) == 5


def test_a_builder_that_crashes_is_an_error_not_a_crash_of_the_script():
    async def broken(request, report):
        raise ValueError("boom")

    result = run(BOOKS, broken)
    assert result.outcome == "error"
    assert "ValueError" in result.reason


def test_a_slow_build_times_out():
    result = run(BOOKS, pretend(BuildResult("ready", "All tests pass.", GOOD_FILES), wait=2), time_limit=0.1)
    assert result.outcome == "timeout"


def test_a_refusal_passes_only_when_nothing_is_built():
    nothing = BuildResult("failed", "Refused.", {}, kind="no_files")
    assert run(REFUSE, pretend(nothing)).outcome == "pass"
    something = BuildResult("ready", "All tests pass.", GOOD_FILES)
    assert run(REFUSE, pretend(something)).outcome == "fail"


def test_a_refusal_stopped_by_the_free_tier_limit_is_not_a_pass():
    # Found in the first live run: "nothing built" because the quota was used up is not a refusal.
    busy = BuildResult("failed", "The AI service is busy.", {}, kind="service_busy")
    assert run(REFUSE, pretend(busy)).outcome == "limit"


def test_an_empty_set_gives_a_plain_summary():
    assert score.summary([]) == "No requests were run."
    assert asyncio.run(score.run([], pretend(BuildResult("ready", "", {})), pause=0)) == []


def test_summary_leaves_limit_failures_out_of_the_pass_rate():
    scores = [
        score.Score("r01", "k", "build", "pass", 1.0, 0, ""),
        score.Score("r02", "k", "build", "fail", 1.0, 0, ""),
        score.Score("r03", "k", "build", "limit", 1.0, 0, ""),
    ]
    assert score.summary(scores) == "1 of 2 passed (50%); 1 stopped by the free-tier limit; 3 run in total."


def test_summary_when_every_request_hit_the_limit():
    scores = [score.Score("r01", "k", "build", "limit", 1.0, 0, "")]
    assert score.summary(scores).startswith("none could be judged")


def test_the_daily_limit_is_counted_as_a_limit_too():
    # #35 added this stop reason: "Today's free AI limit is used up." It says nothing about our code.
    daily = BuildResult("failed", "Today's free AI limit is used up.", {}, kind="daily_limit")
    assert run(BOOKS, pretend(daily)).outcome == "limit"
    assert run(REFUSE, pretend(daily)).outcome == "limit"
