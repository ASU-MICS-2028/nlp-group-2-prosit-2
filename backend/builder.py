"""The agent loop (W-3): let the AI build a project, then check the result ourselves.

Google ADK does the back-and-forth with the AI (D-010): it sends our message, runs the
tools the AI asks for (write_file, run_tests, ...), sends back the results, and repeats
until the AI says it is done. Our job is everything around that: set it up, report each
step, stop it when it goes wrong, and decide "ready" or "failed" with a plain reason.
"""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass

from google.adk.agents import Agent
from google.adk.agents.invocation_context import LlmCallsLimitExceededError
from google.adk.agents.run_config import RunConfig
from google.adk.models import BaseLlm
from google.adk.runners import InMemoryRunner
from google.genai import errors, types

from agent.llm import builder_model
from agent.tools import Workspace, make_tools
from backend.runner import run_tests

# The builder reports each step by calling this function. The server will pass add_event (W-5);
# tests pass a list's append, so they can look at the steps afterwards.
Report = Callable[[dict[str, object]], None]

# Stop the AI after this many test runs. The instructions tell it the same (agent/prompts/builder.md),
# but we enforce it ourselves: each try uses free-tier quota and makes the person wait.
MAX_TEST_RUNS = 3

# Stop the AI after this many moves in total (every reply it gives is one call to the AI service).
# A real build takes about 10 to 15; 40 is Opei's limit from the W-4 trial, with room to spare.
MAX_AI_CALLS = 40

# Stop the whole build after this many seconds, in case the AI service is very slow or hangs.
# A real build took 44 seconds in Opei's W-4 trial; 5 minutes leaves plenty of room.
TIME_LIMIT_SECONDS = 300

# How much of our own final test run's output we keep in the result (its end, where pytest's summary is).
# The same size the tools send the AI (agent/tools.py MAX_RESULT_CHARACTERS), to save free-tier quota.
MAX_KEPT_OUTPUT = 4_000


@dataclass
class BuildResult:
    status: str  # "ready" or "failed"
    reason: str  # one plain sentence: why the build stopped
    files: dict[str, str]  # the project the AI wrote: {file name: file text}
    # Why it stopped, as one fixed word, so the retry loop (F-4, agent/retry.py) can decide what to do
    # without comparing sentences: "passed", "tests_failed", "no_files", "service_busy", "too_slow", "too_many_steps".
    kind: str = "passed"
    test_output: str = ""  # the end of pytest's output from our own final test run (empty if it never ran)


async def build_project(
    message: str,  # the first message to the AI: the approved plan (agent/prompts builder_message)
    instruction: str | Callable[..., str],  # the AI's standing instructions (agent/prompts builder_instruction)
    model: str | BaseLlm,  # a Gemini model name, or a FakeModel in tests
    report: Report,
    start_files: dict[str, str] | None = None,  # files from an earlier try (F-4), so the AI fixes them, not starts over
) -> BuildResult:
    # This project's files, kept in memory (agent/tools.py). dict(...) makes a copy, so the caller's files stay as they were.
    workspace = Workspace(files=dict(start_files or {}))
    if isinstance(model, str):
        # A model name: wrap it so each busy reply is retried inside this build (agent/llm.py builder_model).
        model = builder_model(model)
    agent = Agent(name="builder", model=model, instruction=instruction, tools=make_tools(workspace))

    # InMemoryRunner is ADK's engine: it keeps the conversation in memory and runs the loop.
    adk_runner = InMemoryRunner(agent=agent, app_name="builder")
    session = await adk_runner.session_service.create_session(app_name="builder", user_id="builder")
    first_message = types.Content(role="user", parts=[types.Part(text=message)])

    # The reason we give if the tests fail at the end. It changes if WE had to stop the AI.
    failed_reason = "The tests still fail."

    try:
        # Stop rule 5: a stopwatch around the whole build. If it runs out, Python stops whatever
        # is waiting (usually the AI service) and raises TimeoutError, which we catch below.
        async with asyncio.timeout(TIME_LIMIT_SECONDS):
            # Each "event" is one thing that happened: the AI wrote text, asked for a tool, or got a tool's result.
            async for event in adk_runner.run_async(
                user_id="builder",
                session_id=session.id,
                new_message=first_message,
                run_config=RunConfig(max_llm_calls=MAX_AI_CALLS),  # stop rule 4: ADK raises an error past this
            ):
                parts = event.content.parts if event.content and event.content.parts else []  # some events are empty
                for part in parts:
                    step = step_from_part(part)
                    if step is not None:
                        report({"status": "working", "step": step})  # one line on the live timeline

                # Stop rule 1: enough test runs. `break` leaves the loop, so ADK never asks the AI for another move.
                if workspace.test_runs >= MAX_TEST_RUNS:
                    failed_reason = f"The tests still fail after {MAX_TEST_RUNS} tries."
                    break
    except TimeoutError:
        # Stop rule 5: the stopwatch ran out.
        reason = "The build took too long and was stopped."
        result = BuildResult(status="failed", reason=reason, files=workspace.files, kind="too_slow")
    except LlmCallsLimitExceededError:
        # Stop rule 4: the AI used up its moves without finishing (for example, going round in circles).
        reason = "The AI took too many steps without finishing."
        result = BuildResult(status="failed", reason=reason, files=workspace.files, kind="too_many_steps")
    except errors.APIError:
        # Stop rule 3: the AI service said no (503 busy, 429 too many requests, a wrong key, ...).
        # Without this, the error would crash the build and no final status would ever reach the live stream.
        reason = "The AI service is busy or unavailable. Please try again in a few minutes."
        result = BuildResult(status="failed", reason=reason, files=workspace.files, kind="service_busy")
    else:
        # "else" runs only when the try block finished WITHOUT an error: then we check the work ourselves.
        result = check_result(workspace, failed_reason)

    # The last event carries the final status; it is also what makes the live stream hang up (W-5).
    state = "done" if result.status == "ready" else "failed"
    report({"status": result.status, "step": {"kind": "Result", "text": result.reason, "state": state}})
    return result


def step_from_part(part: types.Part) -> dict[str, object] | None:
    # Turn one piece of an ADK event into a timeline step (shapes from docs/api-contract.md).
    if part.function_call:  # the AI asks for a tool
        arguments = part.function_call.args or {}
        return {"kind": "Doing", "text": doing_text(part.function_call.name or "", arguments), "state": "done"}
    if part.function_response:  # a tool's answer comes back
        return result_step(part.function_response.name or "", part.function_response.response or {})
    if part.text and part.text.strip():  # the AI writes some text
        return {"kind": "Thinking", "text": part.text.strip(), "state": "done"}
    return None  # anything else isn't worth showing


def doing_text(tool: str, arguments: dict[str, object]) -> str:
    # Plain words for a non-developer, instead of "write_file(path=...)".
    if tool == "write_file":
        return f"Writing {arguments.get('path', 'a file')}"
    if tool == "read_file":
        return f"Reading {arguments.get('path', 'a file')}"
    if tool == "run_tests":
        return "Running the tests"
    if tool == "list_files":
        return "Listing the files"
    return f"Using {tool}"


def result_step(tool: str, response: dict[str, object]) -> dict[str, object]:
    # Every tool answers {"status": "ok", ...} or {"status": "error", "message": ...} (agent/tools.py).
    if response.get("status") == "error":
        return {"kind": "Result", "text": str(response.get("message", "Something went wrong.")), "state": "failed"}
    if tool == "run_tests":
        if response.get("passed"):
            return {"kind": "Result", "text": "Tests passed", "state": "done"}
        # Keep pytest's output so the person (and the timeline) can see what failed.
        return {"kind": "Result", "text": "Tests failed", "output": str(response.get("output", "")), "state": "failed"}
    if tool == "write_file":
        return {"kind": "Result", "text": f"Wrote {response.get('path', 'a file')}", "state": "done"}
    return {"kind": "Result", "text": "Done", "state": "done"}


def check_result(workspace: Workspace, failed_reason: str) -> BuildResult:
    # Stop rule 2: nothing was written (Opei's D-4 check saw a smaller model do this).
    # Say so plainly, instead of the misleading "the tests still fail" when there are no tests at all.
    if not workspace.files:
        return BuildResult(status="failed", reason="The AI stopped without writing any files.", files={}, kind="no_files")

    # Don't trust the AI saying "done": run the tests ourselves on the files it wrote.
    result = run_tests(workspace.files)
    # Keep the end of pytest's output: the retry loop (F-4) shows it to the AI so it can see what failed.
    output = result.output[-MAX_KEPT_OUTPUT:]
    if result.passed:
        return BuildResult(status="ready", reason="All tests pass.", files=workspace.files, test_output=output)
    return BuildResult(
        status="failed", reason=failed_reason, files=workspace.files, kind="tests_failed", test_output=output
    )
