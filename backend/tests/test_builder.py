"""Tests for the agent loop (W-3).

These tests never call the real Gemini. They use a FakeModel: a pretend AI that gives
replies we wrote in advance. That makes the tests free (no quota), fast, and the same every time.
"""

import asyncio
from collections.abc import AsyncGenerator

from google.adk.models import BaseLlm, LlmRequest, LlmResponse
from google.genai import types

from backend.builder import PHASES, build_project, phase_of, result_step, step_from_part
from google.genai import errors
import pytest

from backend import builder

class FakeModel(BaseLlm):
    """A pretend AI. Each time ADK asks it for a reply, it gives the next one from `replies`."""

    replies: list[types.Part]  # the script: what the "AI" says, in order
    calls: int = 0  # how many replies it has given so far

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        # ADK calls this whenever it wants the AI's next move. We ignore the request
        # (what ADK sends the AI) and just give the next scripted reply.
        reply = self.replies[self.calls]
        self.calls += 1
        yield LlmResponse(content=types.Content(role="model", parts=[reply]))


def call(tool_name: str, **arguments: str) -> types.Part:
    """A scripted reply where the AI asks to use a tool, e.g. call("write_file", path="a.py", content="...")."""
    return types.Part(function_call=types.FunctionCall(name=tool_name, args=arguments))


def say(text: str) -> types.Part:
    """A scripted reply where the AI just writes text."""
    return types.Part(text=text)


# A tiny project whose test passes.
PASSING_TEST = "def test_add():\n    assert 1 + 1 == 2\n"


def test_build_ends_ready_when_the_tests_pass() -> None:
    # The script: write one file, run the tests, then say it's done.
    model = FakeModel(
        model="fake",
        replies=[
            call("write_file", path="test_math.py", content=PASSING_TEST),
            call("run_tests"),
            say("All tests pass."),
        ],
    )
    steps: list[dict[str, object]] = []  # every step the builder reports lands here

    # build_project is "async", so we use asyncio.run to run it from a normal test.
    result = asyncio.run(build_project("Build it.", "You are a builder.", model, report=steps.append))

    assert result.status == "ready"
    assert result.files == {"test_math.py": PASSING_TEST}


def test_each_step_is_reported_for_the_timeline() -> None:
    model = FakeModel(
        model="fake",
        replies=[
            call("write_file", path="test_math.py", content=PASSING_TEST),
            call("run_tests"),
            say("All tests pass."),
        ],
    )
    steps: list[dict[str, object]] = []

    asyncio.run(build_project("Build it.", "You are a builder.", model, report=steps.append))

    # Doing/Result for write_file, Doing/Result for run_tests, the AI's last words, then our final verdict.
    kinds = [event["step"]["kind"] for event in steps]
    assert kinds == ["Doing", "Result", "Doing", "Result", "Thinking", "Result"]
    assert steps[0]["step"]["text"] == "Writing test_math.py"
    assert steps[-1]["status"] == "ready"  # the last event carries the final status

# A tiny project whose test always fails.
FAILING_TEST = "def test_add():\n    assert 1 + 1 == 3\n"

def test_build_stops_after_three_failed_test_runs() -> None:
    # A stubborn AI: it would run the failing tests 5 times if we let it.
    model = FakeModel(
        model="fake",
        replies=[
            call("write_file", path="test_math.py", content=FAILING_TEST),
            call("run_tests"),
            call("run_tests"),
            call("run_tests"),
            call("run_tests"),
            call("run_tests"),
            say("I give up."),
        ],
    )
    steps: list[dict[str, object]] = []

    result = asyncio.run(build_project("Build it.", "You are a builder.", model, report=steps.append))

    assert result.status == "failed"
    assert result.reason == "The tests still fail after 3 tries."
    assert model.calls == 4  # the write, then 3 test runs; we stopped it before the 4th run

def test_build_fails_clearly_when_the_ai_writes_no_files() -> None:
    # Like gemini-3.5-flash-lite in Opei's D-4 check: one sentence, then it stops without using a tool.
    model = FakeModel(model="fake", replies=[say("Building a Bookshop API.")])
    steps: list[dict[str, object]] = []

    result = asyncio.run(build_project("Build it.", "You are a builder.", model, report=steps.append))

    assert result.status == "failed"
    assert result.reason == "The AI stopped without writing any files."


class BusyModel(BaseLlm):
    """A pretend AI service that is overloaded: every call fails with "503 high demand"."""

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        raise errors.ServerError(503, {"error": {"code": 503, "message": "high demand", "status": "UNAVAILABLE"}})
        yield  # never reached; it only tells Python this is the same kind of function as FakeModel's


def test_build_fails_clearly_when_the_ai_service_is_down() -> None:
    steps: list[dict[str, object]] = []

    result = asyncio.run(
        build_project("Build it.", "You are a builder.", BusyModel(model="fake"), report=steps.append)
    )

    assert result.status == "failed"
    assert result.reason == "The AI service is busy or unavailable. Please try again in a few minutes."
    assert steps[-1]["status"] == "failed"  # a final status still reaches the live stream, so it hangs up

def test_build_stops_after_too_many_ai_moves() -> None:
    # A confused AI: it lists the files again and again and never runs the tests.
    model = FakeModel(model="fake", replies=[call("list_files")] * 50)
    steps: list[dict[str, object]] = []

    result = asyncio.run(build_project("Build it.", "You are a builder.", model, report=steps.append))

    assert result.status == "failed"
    assert result.reason == "The AI took too many steps without finishing."
    assert model.calls == 40  # ADK stopped it at our limit, not at the end of its 50-line script

class SlowModel(BaseLlm):
    """A pretend AI service that takes a whole minute to answer."""

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        await asyncio.sleep(60)  # wait 60 seconds, like a service that hangs
        yield LlmResponse(content=types.Content(role="model", parts=[types.Part(text="Finally.")]))


def test_build_stops_when_it_takes_too_long(monkeypatch: pytest.MonkeyPatch) -> None:
    # Use a 1-second limit for this test only, so the test is quick.
    monkeypatch.setattr(builder, "TIME_LIMIT_SECONDS", 1)
    steps: list[dict[str, object]] = []

    result = asyncio.run(
        build_project("Build it.", "You are a builder.", SlowModel(model="fake"), report=steps.append)
    )

    assert result.status == "failed"
    assert result.reason == "The build took too long and was stopped."


# --- Phases (D-019): every timeline step says what it is about, so the page never has to read the sentence.

def phases_of(steps: list[dict[str, object]]) -> list[str]:
    # The phase of every event that carries a step. (Some events only change the status.)
    return [event["step"]["phase"] for event in steps if "step" in event]


def test_every_step_of_a_good_build_has_the_expected_phase() -> None:
    model = FakeModel(
        model="fake",
        replies=[
            call("write_file", path="test_math.py", content=PASSING_TEST),
            call("run_tests"),
            say("All tests pass."),
        ],
    )
    steps: list[dict[str, object]] = []

    asyncio.run(build_project("Build it.", "You are a builder.", model, report=steps.append))

    # Writing (Doing, Result), testing (Doing, Result), the AI's closing words, our final verdict.
    assert phases_of(steps) == ["writing", "writing", "testing", "testing", "finishing", "finishing"]


def test_every_step_of_a_failing_build_has_a_known_phase() -> None:
    model = FakeModel(
        model="fake",
        replies=[
            call("write_file", path="test_math.py", content=FAILING_TEST),
            call("run_tests"),
            call("run_tests"),
            call("run_tests"),
            say("I give up."),
        ],
    )
    steps: list[dict[str, object]] = []

    asyncio.run(build_project("Build it.", "You are a builder.", model, report=steps.append))

    assert phases_of(steps)  # there are steps to check
    assert all(phase in PHASES for phase in phases_of(steps))
    assert phases_of(steps)[-1] == "finishing"  # the final verdict


def test_the_final_verdict_of_a_build_with_no_files_has_a_phase() -> None:
    model = FakeModel(model="fake", replies=[say("Building a Bookshop API.")])
    steps: list[dict[str, object]] = []

    asyncio.run(build_project("Build it.", "You are a builder.", model, report=steps.append))

    assert all(phase in PHASES for phase in phases_of(steps))
    assert phases_of(steps)[-1] == "finishing"


def test_each_tool_belongs_to_one_phase() -> None:
    for tool in ("write_file", "read_file", "list_files"):
        assert phase_of(tool) == "writing"
    assert phase_of("run_tests") == "testing"
    assert phase_of("some_new_tool") == "writing"  # an unknown tool still gets a known phase


def test_a_tool_step_keeps_the_tools_phase_even_when_it_failed() -> None:
    step = result_step("write_file", {"status": "error", "message": "That file name is not allowed."})

    assert step["state"] == "failed"
    assert step["phase"] == "writing"


def test_the_ais_own_words_get_the_phase_the_loop_gives_them() -> None:
    words = types.Part(text="I will change the price field.")

    assert step_from_part(words)["phase"] == "planning"  # the default: nothing was used yet
    assert step_from_part(words, "fixing")["phase"] == "fixing"
    assert step_from_part(words, "finishing")["phase"] == "finishing"

