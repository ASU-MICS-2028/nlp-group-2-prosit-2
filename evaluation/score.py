"""The scoring script (E-1): run requests from requests.json through the builder and score each one.

For every request it records: pass or not, how many extra tries the builder needed, and how many seconds it took.
Pass rule (requests.json, "how_to_read"):
  build / ask_first: the build ends "ready" (its own tests pass), every expected endpoint exists,
                     and there are at least `min_tables` tables;
  refuse:            nothing is built.
A failure caused by Gemini's free-tier limit is counted as "limit", not "fail": it says nothing about our code.

It calls the builder in this Python process (the same call the server makes in backend/projects.py run_build),
because the server does not hand out the generated files yet, and the endpoint check needs them.

Run from the repo root, with the backend's venv:
    python -m evaluation.score --only r01,r02 --out evidence/evaluation/outputs_e1_two_requests.txt
It reads GEMINI_API_KEY and LLM_MODEL from .env. Each build uses about 10-20 of the day's 20 free requests per model.
"""

import argparse
import asyncio
import io
import json
import os
import re
import time
import zipfile
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path

import httpx
from dotenv import load_dotenv

from agent.prompts import builder_instruction
from agent.retry import build_with_retries
from backend.builder import BuildResult, Report

REQUESTS_FILE = Path(__file__).resolve().parent / "requests.json"
TIME_LIMIT_SECONDS = 900  # 15 minutes per request; the builder has its own stopwatch, this is a last safety net
PAUSE_SECONDS = 60  # wait between requests, so we don't hit the free tier's per-minute limit

# A route in the generated app/main.py, e.g.  @app.get("/books/{book_id}", ...)  ->  ("get", "/books/{book_id}")
ROUTE = re.compile(r"""@app\.(get|post|put|delete)\(\s*["']([^"']+)["']""")
# Any path parameter, e.g. {book_id}. requests.json writes them all as {id}.
PATH_PARAMETER = re.compile(r"\{[^}]+\}")
# One table in the generated app/database.py
TABLE = re.compile(r"CREATE TABLE IF NOT EXISTS\s+(\w+)", re.IGNORECASE)
# Other names a table may fairly get (from the notes in requests.json), mapped to the name we wrote there.
OTHER_NAMES = {"classrooms": "classes", "products": "produce", "crops": "produce"}

# Stop reasons that come from Gemini saying no (busy, or the free daily allowance used up, #35), not from our code.
LIMIT_KINDS = {"service_busy", "daily_limit"}

# What one build looks like to this script: (request text, where to report steps) -> the build's result.
# The real one calls Gemini; the tests pass a pretend one.
Build = Callable[[str, Report], Awaitable[BuildResult]]


@dataclass
class Score:
    id: str
    kind: str
    expect: str
    outcome: str  # "pass", "fail", "limit" (free-tier limit), "timeout" or "error"
    seconds: float
    retries: int  # extra whole tries the builder needed (0 = it worked, or stopped, on the first try)
    reason: str  # one plain sentence: why it passed or failed
    missing_endpoints: list[str] = field(default_factory=list)
    tables: int = 0


def same_name(word: str) -> str:
    # "books" and "book" count as the same table, and so do the other names listed in OTHER_NAMES.
    word = OTHER_NAMES.get(word.lower(), word.lower())
    return word[:-1] if word.endswith("s") else word


def endpoint_key(method: str, path: str) -> str:
    # One way of writing an endpoint, so the generated one and the expected one can be compared:
    # "GET /books/{book_id}" and "GET /book/{id}" both become "GET /book/{id}".
    path = PATH_PARAMETER.sub("{id}", path.strip().rstrip("/"))
    parts = path.strip("/").split("/")
    parts[0] = same_name(parts[0])
    return f"{method.upper()} /" + "/".join(parts)


def endpoints_in(files: dict[str, str]) -> set[str]:
    code = files.get("app/main.py", "")  # the builder prompt puts every endpoint in app/main.py
    return {endpoint_key(method, path) for method, path in ROUTE.findall(code)}


def tables_in(files: dict[str, str]) -> int:
    return len(set(TABLE.findall(files.get("app/database.py", ""))))


def judge(spec: dict, result: BuildResult) -> tuple[str, str, list[str], int]:
    # Apply the pass rule to one finished build. Returns (outcome, reason, missing endpoints, tables).
    tables = tables_in(result.files)
    # First: did Gemini say no? Then the build tells us nothing, not even for a refusal
    # (live run 2026-11-15: r19 "built nothing" only because the day's quota was used up).
    if result.status != "ready" and result.kind in LIMIT_KINDS:
        return "limit", f"Gemini said no (busy or out of quota): {result.reason}", [], tables
    if spec["expect"] == "refuse":
        if result.files:
            return "fail", f"It should have built nothing, but it wrote {len(result.files)} files.", [], tables
        return "pass", "Nothing was built, as expected.", [], tables

    if result.status != "ready":
        return "fail", f"The build did not finish: {result.reason}", [], tables

    found = endpoints_in(result.files)
    expected = {endpoint_key(*e.split(" ", 1)): e for e in spec.get("expected_endpoints", [])}
    missing = sorted(text for key, text in expected.items() if key not in found)
    if missing:
        return "fail", f"{len(missing)} expected endpoints are missing.", missing, tables
    if tables < spec.get("min_tables", 0):
        return "fail", f"Only {tables} tables; at least {spec['min_tables']} expected.", [], tables
    return "pass", "Built, its tests pass, and every expected endpoint exists.", [], tables


async def score_one(spec: dict, build: Build, time_limit: float = TIME_LIMIT_SECONDS) -> Score:
    attempts: list[int] = []

    def report(event: dict[str, object]) -> None:
        # The builder reports {"attempt": 2, ...} at the start of each whole try; we only count those.
        attempt = event.get("attempt")
        if isinstance(attempt, int):
            attempts.append(attempt)

    start = time.monotonic()
    try:
        result = await asyncio.wait_for(build(spec["request"], report), timeout=time_limit)
        outcome, reason, missing, tables = judge(spec, result)
    except TimeoutError:
        outcome, reason, missing, tables = "timeout", f"No answer within {time_limit:.0f} seconds.", [], 0
    except Exception as error:  # a crash in one build must not stop the other 19
        outcome, reason, missing, tables = "error", f"The build crashed: {type(error).__name__}.", [], 0
    seconds = round(time.monotonic() - start, 1)
    retries = max(attempts) - 1 if attempts else 0
    return Score(spec["id"], spec["kind"], spec["expect"], outcome, seconds, retries, reason, missing, tables)


def summary(scores: list[Score]) -> str:
    if not scores:
        return "No requests were run."
    counted = [s for s in scores if s.outcome != "limit"]  # a limit failure is not a verdict on our code
    passed = sum(1 for s in counted if s.outcome == "pass")
    limits = len(scores) - len(counted)
    rate = f"{passed} of {len(counted)} passed ({100 * passed / len(counted):.0f}%)" if counted else "none could be judged"
    return f"{rate}; {limits} stopped by the free-tier limit; {len(scores)} run in total."


def line(score: Score) -> str:
    text = f"{score.id}  {score.outcome:<7} {score.seconds:>6.1f}s  retries={score.retries}  {score.reason}"
    if score.missing_endpoints:
        text += "  Missing: " + ", ".join(score.missing_endpoints)
    return text


async def real_build(request: str, report: Report) -> BuildResult:
    model = os.environ.get("LLM_MODEL", "")
    if not model:
        raise SystemExit("LLM_MODEL is not set. Put it in .env (the script reads it).")
    # The same first message the server sends (backend/projects.py run_build), so we score what users get.
    message = f"There is no plan yet. Build a small API for this request:\n\n{request}"
    return await build_with_retries(message, builder_instruction(), model, report=report)


async def run(specs: list[dict], build: Build, pause: float) -> list[Score]:
    scores = []
    for number, spec in enumerate(specs):
        if number > 0:
            await asyncio.sleep(pause)
        score = await score_one(spec, build)
        print(line(score), flush=True)
        scores.append(score)
    return scores


class ProjectGone(Exception):
    """The server no longer knows the project: it restarted (or slept) during the build, and lost it (D-013)."""


def kind_from_text(text: str) -> str:
    # The server only tells us the final sentence, so the stop reason is read from it (the sentences come from
    # agent/llm.py DAILY_LIMIT_MESSAGE and backend/builder.py's "busy" message).
    if "free AI limit" in text:
        return "daily_limit"
    if "busy" in text:
        return "service_busy"
    return "failed"


def live_build(base_url: str, transport: httpx.AsyncBaseTransport | None = None, poll_seconds: float = 5) -> Build:
    """A build that goes through a running server's API, exactly like a user's (E-2 on the live site).

    POST /projects, wait for "ready" or "failed", read the diary (/events) for the tries and the final sentence,
    and for a ready build download the zip (F-5) to check its endpoints. The server uses its own key, so no key is
    needed here. `transport` lets the tests use a pretend server.
    """

    async def build(request: str, report: Report) -> BuildResult:
        async with httpx.AsyncClient(base_url=base_url, transport=transport, timeout=60) as http:
            started = await http.post("/projects", json={"request": request})
            started.raise_for_status()
            project_id = started.json()["id"]

            while True:  # score_one's time limit stops this if the server never finishes
                answer = await http.get(f"/projects/{project_id}")
                if answer.status_code == 404:
                    raise ProjectGone()  # scored as "error", with this name in the reason, not a bare KeyError
                project = answer.json()
                if project["status"] in ("ready", "failed", "stopped"):
                    break
                await asyncio.sleep(poll_seconds)

            final_text = ""
            diary = await http.get(f"/projects/{project_id}/events")  # the build is over, so the stream replays and ends
            for line in diary.text.splitlines():
                if line.startswith("data:"):
                    event = json.loads(line[len("data:"):])
                    report(event)  # score_one counts the tries from the "attempt" events
                    step = event.get("step")
                    if isinstance(step, dict):
                        final_text = str(step.get("text", ""))

            if project["status"] == "ready":
                download = await http.get(f"/projects/{project_id}/download")
                download.raise_for_status()
                with zipfile.ZipFile(io.BytesIO(download.content)) as archive:
                    files = {name: archive.read(name).decode() for name in archive.namelist()}
                return BuildResult(status="ready", reason=final_text, files=files)

            # A failed build can't be downloaded, but the server says how many files it wrote. A refusal is judged
            # on "were any files written", so stand-in names are enough here.
            written = {f"(file {n})": "" for n in range(project.get("file_count") or 0)}
            return BuildResult(status="failed", reason=final_text, files=written, kind=kind_from_text(final_text))

    return build


def main() -> None:
    parser = argparse.ArgumentParser(description="Score requests from evaluation/requests.json (E-1).")
    parser.add_argument("--only", help="comma-separated ids, e.g. r01,r02 (default: all 20)")
    parser.add_argument("--out", help="also save the results to this file (never overwrite an old run)")
    parser.add_argument("--pause", type=float, default=PAUSE_SECONDS, help="seconds to wait between requests")
    parser.add_argument("--base-url", help="score through a running server's API instead (e.g. the live site); uses the server's key")
    args = parser.parse_args()

    load_dotenv()  # GEMINI_API_KEY and LLM_MODEL from the local .env file
    specs = json.loads(REQUESTS_FILE.read_text(encoding="utf-8"))["requests"]
    if args.only:
        wanted = args.only.split(",")
        specs = [s for s in specs if s["id"] in wanted]
    if args.out and Path(args.out).exists():
        raise SystemExit(f"{args.out} already exists. Keep every run: pick a new file name.")

    # Live mode: the server's own model and key are used, so name the server, not this laptop's settings.
    where = f"Live site: {args.base_url}" if args.base_url else f"Model: {os.environ.get('LLM_MODEL', '(not set)')}"
    print(f"{where}; {len(specs)} requests", flush=True)
    build = live_build(args.base_url) if args.base_url else real_build
    scores = asyncio.run(run(specs, build, args.pause))
    print(summary(scores))

    if args.out:
        lines = [where, *map(line, scores), summary(scores), ""]
        lines += [json.dumps(asdict(s)) for s in scores]  # the raw numbers, one line per request, for E-2/E-4
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
