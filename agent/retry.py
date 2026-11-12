"""The retry / self-reflection loop (task F-4): try the build again, learning from what went wrong.

One build (backend/builder.py, W-3) lets the AI write files and run the tests up to 3 times.
Sometimes that is not enough. This loop looks at WHY a build stopped and starts a new try:

- tests still fail      -> the AI gets the test output and its own files back, and must first say
                           what went wrong before it fixes anything (self-reflection);
- no files were written -> the AI gets a firm reminder that its first reply must be write_file;
- AI service is busy    -> we wait a little, then send the same message again;
- too slow / too many steps -> treated like failing tests: keep the files, explain, try again.

The prompts for these new tries are Markdown files in agent/prompts/, so the team can review them.
"""

import asyncio
from collections.abc import Callable

from google.adk.models import BaseLlm

from agent.prompts import load_prompt
from backend.builder import MAX_KEPT_OUTPUT, BuildResult, Report, build_project
from backend.runner import run_tests

MAX_ATTEMPTS = 3  # whole builds, each with up to 3 test runs: at most 9 test runs per project
BUSY_WAIT_SECONDS = 30  # how long to wait after "503 busy" or "429 too many requests" before trying again

# The reasons that can be fixed by asking the AI again with what went wrong.
REFLECT_ON = {"tests_failed", "too_slow", "too_many_steps"}


async def build_with_retries(
    plan_message: str,  # the first message to the AI: the approved plan (agent/prompts builder_message)
    instruction: str | Callable[..., str],  # the AI's standing instructions (agent/prompts builder_instruction)
    model: str | BaseLlm,  # a Gemini model name, or a FakeModel in tests
    report: Report,  # where each step goes; the server passes add_event (W-5)
    start_files: dict[str, str] | None = None,  # an existing project to fix instead of starting empty
) -> BuildResult:
    message = plan_message
    files = start_files
    result = BuildResult(status="failed", reason="No try was made.", files={}, kind="no_files")

    for attempt in range(1, MAX_ATTEMPTS + 1):
        # Tell the timeline which try this is. The contract (docs/api-contract.md) uses "retrying" from try 2.
        status = "working" if attempt == 1 else "retrying"
        report({"status": status, "attempt": attempt, "max_attempts": MAX_ATTEMPTS})

        result = await build_project(message, instruction, model, hold_back_failure(report, status), start_files=files)
        if result.status == "ready":
            return result  # build_project already sent the final "ready" event, which ends the live stream

        # The AI service can fail AFTER the AI has already fixed everything (seen live: tests passed,
        # then "503 busy" on its last reply). So check the files ourselves before starting a whole new try.
        if result.kind == "service_busy" and result.files:
            check = run_tests(result.files)
            if check.passed:
                reason = "All tests pass."
                report({"status": "ready", "step": {"kind": "Result", "text": reason, "state": "done"}})
                output = check.output[-MAX_KEPT_OUTPUT:]
                return BuildResult(status="ready", reason=reason, files=result.files, test_output=output)

        if attempt == MAX_ATTEMPTS:
            break  # no tries left: don't wait or build a new message for nothing

        # Decide what the next try gets, based on why this one stopped.
        if result.kind in REFLECT_ON:
            message = reflection_message(plan_message, result)
            files = result.files  # keep the AI's work, so it fixes it instead of starting over
        elif result.kind == "no_files":
            message = load_prompt("no_files").replace("<<PLAN>>", plan_message)
            files = start_files
        elif result.kind == "service_busy":
            await asyncio.sleep(BUSY_WAIT_SECONDS)  # "await" lets the server serve others while we wait
            files = result.files or start_files  # same message as before; keep any files already written

        report({"status": "retrying", "step": {"kind": "Thinking", "text": retry_text(result), "state": "done"}})

    # Every try failed: now, and only now, send the final "failed" event, which ends the live stream (W-5).
    reason = f"Still not working after {MAX_ATTEMPTS} tries. Last problem: {result.reason}"
    report({"status": "failed", "step": {"kind": "Result", "text": reason, "state": "failed"}})
    return BuildResult(status="failed", reason=reason, files=result.files, kind=result.kind, test_output=result.test_output)


def hold_back_failure(report: Report, status: str) -> Report:
    """Pass every step on with this try's status, except a try's own final "failed", which would end the stream.

    build_project calls every step "working" and ends with "ready" or "failed". From try 2 on, the timeline
    should keep saying "retrying" (the status badge in the UI), so "working" becomes `status`.
    A "failed" try is not the end while we still have tries left, so it is sent on as `status` too
    (the step itself is kept). "ready" is passed on as it is: it really is the end.
    """

    def report_step(event: dict[str, object]) -> None:
        if event.get("status") in ("working", "failed"):
            event = {**event, "status": status}  # a copy with a new status; the original is left alone
        report(event)

    return report_step


def reflection_message(plan_message: str, result: BuildResult) -> str:
    """Build the message for a new try: what went wrong, the files, the test output, and the plan again."""
    file_names = ", ".join(sorted(result.files)) or "none"
    test_output = result.test_output.strip() or "(the tests did not run)"
    return (
        load_prompt("reflection")
        .replace("<<REASON>>", result.reason)
        .replace("<<FILES>>", file_names)
        .replace("<<TEST_OUTPUT>>", test_output)
        .replace("<<PLAN>>", plan_message)
    )


def retry_text(result: BuildResult) -> str:
    """One plain sentence for the timeline: why we are trying again."""
    if result.kind == "no_files":
        return "The AI wrote no files. Trying again with a firmer reminder."
    if result.kind == "service_busy":
        return f"The AI service was busy. Waited {BUSY_WAIT_SECONDS} seconds; trying again."
    return f"{result.reason} Asking the AI to explain what went wrong and fix it."
