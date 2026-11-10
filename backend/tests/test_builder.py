"""Tests for the agent loop (W-3).

These tests never call the real Gemini. They use a FakeModel: a pretend AI that gives
replies we wrote in advance. That makes the tests free (no quota), fast, and the same every time.
"""

import asyncio
from collections.abc import AsyncGenerator

from google.adk.models import BaseLlm, LlmRequest, LlmResponse
from google.genai import types

from backend.builder import build_project


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
