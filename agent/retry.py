"""The retry / self-reflection loop (task F-4): try the build again, learning from what went wrong.

One build (backend/builder.py, W-3) lets the AI write files and run the tests up to 3 times.
Sometimes that is not enough. This loop looks at WHY a build stopped and starts a new try:

- tests still fail      -> the AI gets the test output and its own files back, and must first say
                           what went wrong before it fixes anything (self-reflection);
- no files were written -> the AI gets a firm reminder that its first reply must be write_file;
- AI service is busy    -> we wait a little, then send the same message again;
- today's free limit is used up (a per-day 429) -> stop at once: no try or wait can help until tomorrow;
- too slow / too many steps -> treated like failing tests: keep the files, explain, try again.

The prompts for these new tries are Markdown files in agent/prompts/, so the team can review them.
"""

import asyncio
from collections.abc import Callable

from google.adk.models import BaseLlm

from agent.prompts import load_prompt
from backend.builder import MAX_KEPT_OUTPUT, BuildResult, Report, build_project
from backend.runner import run_tests

# Whole builds, each with up to 3 test runs. 3 (F-4); D-018 made it 4, D-021 brings it back to 3:
# the person sees "Attempt 1 of 3", and a build that keeps failing stops sooner.
MAX_ATTEMPTS = 3
BUSY_WAIT_SECONDS = 30  # how long to wait after "503 busy" or "429 too many requests" before trying again
# After the main model has been busy this many times in one build, the last try uses the backup model (D-021).
SWITCH_AFTER_BUSY = 2

# The reasons that can be fixed by asking the AI again with what went wrong.
REFLECT_ON = {"tests_failed", "too_slow", "too_many_steps"}


async def build_with_retries(
    plan_message: str,  # the first message to the AI: the approved plan (agent/prompts builder_message)
    instruction: str | Callable[..., str],  # the AI's standing instructions (agent/prompts builder_instruction)
    model: str | BaseLlm,  # a Gemini model name, or a FakeModel in tests
    report: Report,  # where each step goes; the server passes add_event (W-5)
    start_files: dict[str, str] | None = None,  # an existing project to fix instead of starting empty
    backup_model: str | BaseLlm | None = None,  # used only when the main model is busy 3 times (D-018)
) -> BuildResult:
    message = plan_message
    files = start_files
    busy_tries = 0  # how many tries ended because the AI service was busy
    result = BuildResult(status="failed", reason="No try was made.", files={}, kind="no_files")

    for attempt in range(1, MAX_ATTEMPTS + 1):
        # Tell the timeline which try this is. The contract (docs/api-contract.md) uses "retrying" from try 2.
        status = "working" if attempt == 1 else "retrying"
        report({"status": status, "attempt": attempt, "max_attempts": MAX_ATTEMPTS})

        held: list[dict[str, object]] = []  # this try's own final "failed" event, kept back (see hold_back_failure)
        result = await build_project(message, instruction, model, hold_back_failure(report, status, held), start_files=files)
        if result.status == "ready":
            return result  # build_project already sent the final "ready" event, which ends the live stream

        # The AI service can fail AFTER the AI has already fixed everything (seen live: tests passed,
        # then "503 busy" on its last reply). So check the files ourselves before starting a whole new try.
        if result.kind in ("service_busy", "daily_limit") and result.files:
            check = run_tests(result.files)
            if check.passed:
                for event in held:
                    report(as_not_the_end(event, status))
                reason = "All tests pass."
                report({"status": "ready", "step": {"kind": "Result", "text": reason, "state": "done", "phase": "finishing"}})
                output = check.output[-MAX_KEPT_OUTPUT:]
                return BuildResult(status="ready", reason=reason, files=result.files, test_output=output)

        if result.kind in ("daily_limit", "refused"):
            # Today's free allowance is used up (#33): another try or a wait cannot help until tomorrow.
            # Or the AI refused a request it must not build (E-2): trying again, or the "write files first"
            # reminder, would only push it to build it anyway. Either way, stop now with the plain sentence.
            # The try's own last step already says it, so send that one as the end: once, not twice (#50).
            report(held[-1] if held else stop_event(result.reason))
            return result

        # Not the end: show the try's last step as being about fixing (see hold_back_failure).
        for event in held:
            report(as_not_the_end(event, status))

        if attempt == MAX_ATTEMPTS:
            break  # no tries left: don't wait or build a new message for nothing

        # Decide what the next try gets, based on why this one stopped.
        text = retry_text(result)  # the sentence the timeline shows for this retry
        if result.kind in REFLECT_ON:
            message = reflection_message(plan_message, result)
            files = result.files  # keep the AI's work, so it fixes it instead of starting over
        elif result.kind == "no_files":
            message = load_prompt("no_files").replace("<<PLAN>>", plan_message)
            files = start_files
        elif result.kind == "service_busy":
            busy_tries += 1
            if backup_model is not None and busy_tries == SWITCH_AFTER_BUSY:
                # Critical: the main model was busy on every try so far, so it is probably down for a while.
                # Switch to the backup for the tries left. No waiting: it is a different model.
                model = backup_model
                text = f"The AI service was busy {busy_tries} times. Switching to the backup model for one last try."
            else:
                await asyncio.sleep(BUSY_WAIT_SECONDS)  # "await" lets the server serve others while we wait
            files = result.files or start_files  # same message as before; keep any files already written

        report({"status": "retrying", "step": {"kind": "Thinking", "text": text, "state": "done", "phase": "fixing"}})

    # Every try failed: now, and only now, send the final "failed" event, which ends the live stream (W-5).
    reason = f"Still not working after {MAX_ATTEMPTS} tries. Last problem: {result.reason}"
    report(stop_event(reason))
    return BuildResult(status="failed", reason=reason, files=result.files, kind=result.kind, test_output=result.test_output)


def hold_back_failure(report: Report, status: str, held: list[dict[str, object]]) -> Report:
    """Pass every step on with this try's status, but keep back the try's own final "failed" in `held`.

    build_project calls every step "working" and ends with "ready" or "failed". From try 2 on, the timeline
    should keep saying "retrying" (the status badge in the UI), so "working" becomes `status`.
    A "failed" try is only the end if build_with_retries decides to stop, so that event goes into `held`
    and build_with_retries sends it: as it is when it stops, or via as_not_the_end before the next try.
    Sending it here AND a stop line later showed the same sentence twice on the timeline (#50).
    "ready" is passed on as it is: it really is the end.
    """

    def report_step(event: dict[str, object]) -> None:
        if event.get("status") == "failed":
            held.append(event)
            return
        if event.get("status") == "working":
            event = {**event, "status": status}  # a copy with a new status; the original is left alone
        report(event)

    return report_step


def as_not_the_end(event: dict[str, object], status: str) -> dict[str, object]:
    """A try's own "failed" event, when more tries follow: it keeps the try's status, and its step is about
    fixing, not finishing; otherwise the plain timeline (F-17) says "Finalizing your API…" while we wait."""
    if isinstance(event.get("step"), dict):
        event = {**event, "step": {**event["step"], "phase": "fixing"}}
    return {**event, "status": status}


def stop_event(reason: str) -> dict[str, object]:
    """The final "failed" event, which ends the live stream (W-5)."""
    return {"status": "failed", "step": {"kind": "Result", "text": reason, "state": "failed", "phase": "finishing"}}


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
