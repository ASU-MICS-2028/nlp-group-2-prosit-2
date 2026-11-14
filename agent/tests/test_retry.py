"""Tests for the retry / self-reflection loop (F-4). They use a pretend AI: no key, no quota."""

import asyncio
from collections.abc import AsyncGenerator

import pytest
from google.adk.models import BaseLlm, LlmRequest, LlmResponse
from google.genai import errors, types

from agent import retry
from agent.retry import build_with_retries

# A "seeded failing project": a small app with a bug, and a test that catches it.
BUGGY_APP = "def add(a, b):\n    return a - b\n"  # the bug: minus instead of plus
FIXED_APP = "def add(a, b):\n    return a + b\n"
TEST_FILE = "from calc import add\n\n\ndef test_add():\n    assert add(2, 3) == 5\n"
SEEDED_PROJECT = {"calc.py": BUGGY_APP, "test_calc.py": TEST_FILE}


class FakeModel(BaseLlm):
    """A pretend AI. It gives the next scripted reply each time, and remembers the messages it was sent."""

    replies: list[types.Part]
    calls: int = 0
    busy_first: int = 0  # how many calls fail with "503 busy" before the script starts
    seen: list[str] = []  # the text of every message the AI received, in order

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        for content in llm_request.contents:
            for part in content.parts or []:
                if part.text and part.text not in self.seen:
                    self.seen.append(part.text)
        if self.busy_first > 0:  # pretend the AI service is overloaded
            self.busy_first -= 1
            raise errors.ServerError(503, {"error": {"code": 503, "message": "high demand", "status": "UNAVAILABLE"}})
        reply = self.replies[self.calls]
        self.calls += 1
        yield LlmResponse(content=types.Content(role="model", parts=[reply]))


def call(tool_name: str, **arguments: str) -> types.Part:
    return types.Part(function_call=types.FunctionCall(name=tool_name, args=arguments))


def say(text: str) -> types.Part:
    return types.Part(text=text)


def run(model: FakeModel, start_files: dict[str, str] | None = None) -> tuple[retry.BuildResult, list[dict]]:
    steps: list[dict[str, object]] = []
    result = asyncio.run(
        build_with_retries("Build the calculator.", "You are a builder.", model, steps.append, start_files)
    )
    return result, steps


def statuses(steps: list[dict]) -> list[str]:
    return [step["status"] for step in steps]


def test_a_build_that_works_first_time_is_not_retried() -> None:
    model = FakeModel(
        model="fake",
        replies=[call("write_file", path="calc.py", content=FIXED_APP),
                 call("write_file", path="test_calc.py", content=TEST_FILE),
                 call("run_tests"), say("Done.")],
    )

    result, steps = run(model)

    assert result.status == "ready"
    assert "retrying" not in statuses(steps)
    assert steps[0] == {"status": "working", "attempt": 1, "max_attempts": retry.MAX_ATTEMPTS}
    assert steps[-1]["status"] == "ready"


def test_a_seeded_failing_project_is_fixed_on_the_second_try() -> None:
    # Try 1: the AI only runs the tests three times without fixing anything, so the build stops.
    # Try 2: it reads the failure, fixes calc.py and the tests pass.
    model = FakeModel(
        model="fake",
        replies=[call("run_tests"), call("run_tests"), call("run_tests"),
                 say("The add function subtracts. I will change - to +."),
                 call("write_file", path="calc.py", content=FIXED_APP),
                 call("run_tests"), say("Done.")],
    )

    result, steps = run(model, start_files=SEEDED_PROJECT)

    assert result.status == "ready"
    assert result.files["calc.py"] == FIXED_APP
    assert {"status": "retrying", "attempt": 2, "max_attempts": retry.MAX_ATTEMPTS} in steps
    # The second try's message is the reflection prompt: the reason, the files and pytest's output.
    reflection = model.seen[-1]
    assert "What happened: The tests still fail" in reflection
    assert "calc.py, test_calc.py" in reflection
    assert "assert" in reflection and "test_add" in reflection  # pytest's own words about the failure
    assert "Build the calculator." in reflection  # the plan is repeated


def test_every_step_of_a_later_try_says_retrying() -> None:
    # The UI's status badge follows each event's status, so try 2 must not flip back to "working".
    model = FakeModel(
        model="fake",
        replies=[call("run_tests"), call("run_tests"), call("run_tests"),
                 call("write_file", path="calc.py", content=FIXED_APP),
                 call("run_tests"), say("Done.")],
    )

    _, steps = run(model, start_files=SEEDED_PROJECT)

    second_try = steps[steps.index({"status": "retrying", "attempt": 2, "max_attempts": retry.MAX_ATTEMPTS}):]
    assert statuses(second_try)[:-1] == ["retrying"] * (len(second_try) - 1)  # every step until the end
    assert second_try[-1]["status"] == "ready"
    first_try = steps[: steps.index({"status": "retrying", "attempt": 2, "max_attempts": retry.MAX_ATTEMPTS})]
    assert "working" in statuses(first_try)  # try 1 still says "working"


def test_the_seeded_project_is_not_changed_for_the_caller() -> None:
    model = FakeModel(model="fake", replies=[call("write_file", path="calc.py", content=FIXED_APP),
                                             call("run_tests"), say("Done.")])
    seeded = dict(SEEDED_PROJECT)

    run(model, start_files=seeded)

    assert seeded == SEEDED_PROJECT  # the builder worked on a copy


def test_it_gives_up_after_four_tries_with_a_clear_reason() -> None:
    model = FakeModel(model="fake", replies=[call("run_tests")] * 12 + [say("I give up.")] * 4)

    result, steps = run(model, start_files=SEEDED_PROJECT)

    assert result.status == "failed"
    assert result.reason == "Still not working after 4 tries. Last problem: The tests still fail after 3 tries."
    # Only the very last event says "failed": earlier ones would end the live stream too early (W-5).
    assert statuses(steps).count("failed") == 1
    assert steps[-1]["status"] == "failed"
    assert [step.get("attempt") for step in steps if "attempt" in step] == [1, 2, 3, 4]


def test_no_files_gets_a_firm_reminder_then_works() -> None:
    # Like gemini-3.5-flash-lite in D-4: one sentence and no tool call.
    model = FakeModel(
        model="fake",
        replies=[say("Building a calculator."),
                 call("write_file", path="calc.py", content=FIXED_APP),
                 call("write_file", path="test_calc.py", content=TEST_FILE),
                 call("run_tests"), say("Done.")],
    )

    result, _ = run(model)

    assert result.status == "ready"
    assert "Your very first reply must be a call to the write_file tool." in model.seen[-1]


def test_a_busy_service_is_waited_for_and_tried_again(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(retry, "BUSY_WAIT_SECONDS", 0)  # don't really wait 30 seconds in a test
    model = FakeModel(
        model="fake",
        busy_first=1,
        replies=[call("write_file", path="calc.py", content=FIXED_APP),
                 call("write_file", path="test_calc.py", content=TEST_FILE),
                 call("run_tests"), say("Done.")],
    )

    result, steps = run(model)

    assert result.status == "ready"
    assert any("busy" in str(step.get("step", {}).get("text", "")) for step in steps)


class BusyAtTheEndModel(FakeModel):
    """Fixes everything, then the service fails on the AI's last reply (seen live in the F-4 check)."""

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        if self.calls == len(self.replies):  # the script is used up: now the service breaks
            raise errors.ServerError(503, {"error": {"code": 503, "message": "high demand", "status": "UNAVAILABLE"}})
        async for response in super().generate_content_async(llm_request, stream):
            yield response


def test_busy_after_a_fix_is_still_ready_without_a_new_try(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(retry, "BUSY_WAIT_SECONDS", 0)
    model = BusyAtTheEndModel(
        model="fake",
        replies=[call("write_file", path="calc.py", content=FIXED_APP), call("run_tests")],
    )

    result, steps = run(model, start_files=SEEDED_PROJECT)

    assert result.status == "ready"  # we checked the files ourselves instead of throwing the fix away
    assert "retrying" not in statuses(steps)
    assert steps[-1]["status"] == "ready"


def test_a_service_that_stays_busy_ends_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(retry, "BUSY_WAIT_SECONDS", 0)
    model = FakeModel(model="fake", busy_first=4, replies=[])  # busy on all 4 tries, and no backup

    result, steps = run(model)

    assert result.status == "failed"
    assert result.kind == "service_busy"
    assert "busy" in result.reason
    assert statuses(steps).count("failed") == 1


# D-018: the backup model, used for the 4th try only after the main model is busy 3 times in one build.
WORKING_SCRIPT = [
    call("write_file", path="calc.py", content=FIXED_APP),
    call("write_file", path="test_calc.py", content=TEST_FILE),
    call("run_tests"),
    say("Done."),
]


def build_with_backup(main: FakeModel, backup: FakeModel) -> tuple[retry.BuildResult, list[dict]]:
    steps: list[dict[str, object]] = []
    result = asyncio.run(
        build_with_retries("Build the calculator.", "You are a builder.", main, steps.append, backup_model=backup)
    )
    return result, steps


def test_main_model_busy_twice_switches_to_the_backup(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(retry, "BUSY_WAIT_SECONDS", 0)
    main = FakeModel(model="main", busy_first=3, replies=[])  # busy on tries 1, 2 and 3
    backup = FakeModel(model="backup", replies=WORKING_SCRIPT)

    result, steps = build_with_backup(main, backup)

    assert result.status == "ready"  # try 4, on the backup, built it
    assert backup.calls == len(WORKING_SCRIPT)
    assert any("backup" in str(step.get("step", {}).get("text", "")) for step in steps)


def test_main_model_busy_twice_does_not_switch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(retry, "BUSY_WAIT_SECONDS", 0)
    main = FakeModel(model="main", busy_first=2, replies=WORKING_SCRIPT)  # busy twice, then fine on try 3
    backup = FakeModel(model="backup", replies=[])

    result, _ = build_with_backup(main, backup)

    assert result.status == "ready"
    assert backup.calls == 0  # two busy tries are not critical yet: the main model keeps its 3 tries
