"""The only door to the language model (decision D-002).

Everything else in the project calls `generate(...)`. To change the model
provider (Gemini now, Claude later) you change two environment variables,
not the code that uses it.

Settings (environment variables, see .env.example):
  LLM_PROVIDER   which provider to use: "gemini" (default) or "claude"
  LLM_MODEL      the model name for that provider (required)
  GEMINI_API_KEY the secret key for Gemini (never commit it)
  LLM_BACKUP_MODEL  optional: the model for the last try when LLM_MODEL is busy 3 times (D-018)

Try it:  python -m agent.llm
"""

import os
import asyncio
import time
from collections.abc import AsyncGenerator

from google import genai
from google.adk.models import Gemini, LlmRequest, LlmResponse
from google.genai import types

MAX_TRIES = 3  # how many times we try when the free tier says "slow down"
WAIT_SECONDS = 2  # wait this long after the first failure, twice as long after the second
MAX_PROMPT_CHARS = 20000  # refuse huge prompts instead of burning free quota

# HTTP codes that mean "busy, try again soon": 500/504 a server hiccup, 503 overloaded.
# 429 ("too many requests") is left out on purpose: the HTTP retry can only tell errors apart by number,
# and a per-DAY 429 must not be resent. BuilderGemini below retries 429 itself, but only a per-minute one.
BUSY_CODES = [500, 503, 504]

# Waits (seconds) before resending a per-MINUTE 429 inside a build. The free tier's per-minute window
# clears quickly, so about half a minute in total is enough; after that the retry loop (F-4) takes over.
MINUTE_LIMIT_WAITS = [5, 10, 20]

# How the builder agent retries ONE busy reply from Gemini, inside a build (see builder_model below).
# 5 attempts with waits of about 2, 4, 8 and 16 seconds (plus a little random "jitter"), so at most
# about 30 seconds of waiting before we give up on that reply and the retry loop (F-4) takes over.
BUILDER_RETRY = types.HttpRetryOptions(
    attempts=5,  # the first call plus 4 retries
    initial_delay=2,
    max_delay=16,
    exp_base=2,  # each wait is twice the one before
    http_status_codes=BUSY_CODES,
)

# Longest we wait for ONE answer from Gemini in a build. A call that hangs (seen live: no answer for the
# whole 5-minute try) is cut after this and sent again by BUILDER_RETRY, instead of eating the whole try.
# A normal answer, even writing a whole app/main.py, takes well under a minute.
CALL_TIMEOUT_SECONDS = 90

# Tests replace these with fakes so they do not really wait.
_sleep = time.sleep
_async_sleep = asyncio.sleep


class LLMError(Exception):
    """Something went wrong with the model. The message is safe to show to a user."""


class RateLimited(LLMError):
    """The provider is busy: too many requests (429) or overloaded (503). Worth trying again."""


# What the person sees when the free tier's daily allowance is used up. Waiting minutes cannot help.
DAILY_LIMIT_MESSAGE = "Today's free AI limit is used up. Please try again tomorrow."


class DailyLimitReached(LLMError):
    """The free tier's requests-per-day allowance is used up. Trying again cannot help until tomorrow.

    Not a RateLimited on purpose: generate() retries RateLimited, and must NOT retry this.
    """


def is_daily_limit(error: Exception) -> bool:
    """True for a "429 too many requests" whose details name a per-DAY quota.

    Seen on Render (#33): 429 RESOURCE_EXHAUSTED with quotaId "GenerateRequestsPerDayPerProjectPerModel-FreeTier"
    and "retry in 22h". A per-MINUTE 429 is different: it clears in seconds, so it is still worth retrying.
    We only look at `details` (Google's error body), never show it: it can echo request details.
    """
    if getattr(error, "code", None) != 429:
        return False
    return "PerDay" in str(getattr(error, "details", ""))


def _call_gemini(prompt: str, system: str | None, model: str) -> str:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise LLMError("GEMINI_API_KEY is not set. Put it in your local .env file.")

    client = genai.Client(api_key=key)
    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(system_instruction=system),
        )
    except genai.errors.APIError as error:
        if is_daily_limit(error):  # today's allowance is gone: stop now, don't make the person wait for nothing
            raise DailyLimitReached(DAILY_LIMIT_MESSAGE) from error
        if error.code in (429, 503):  # too many requests, or overloaded: worth waiting and trying again
            raise RateLimited("The model is busy (free-tier limit). Try again shortly.") from error
        # Only the code is shown: the original message could echo request details.
        raise LLMError(f"The model returned an error (code {error.code}).") from error
    except Exception as error:
        raise LLMError("Could not reach the model. Check the internet connection.") from error

    return response.text or ""


class BuilderGemini(Gemini):
    """ADK's Gemini model, plus our own retry for "429 too many requests" (#33).

    A per-MINUTE 429 is sent again after a short wait (MINUTE_LIMIT_WAITS). A per-DAY 429 is raised at once:
    the free allowance is gone until tomorrow, so waiting would only keep the person waiting for a sure failure.
    Every other error is passed on unchanged (503 and hangs are already retried by BUILDER_RETRY).
    """

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        # None at the end means "no more waits left: let this error through".
        for wait in [*MINUTE_LIMIT_WAITS, None]:
            try:
                # A fresh copy each time: ADK changes the request while sending it, so a resend must start clean.
                async for response in super().generate_content_async(llm_request.model_copy(deep=True), stream):
                    yield response
                return
            except genai.errors.APIError as error:
                if error.code != 429 or is_daily_limit(error) or wait is None:
                    raise
                await _async_sleep(wait)  # "await" lets the server serve others while we wait


def builder_model(name: str) -> Gemini:
    """The model for the builder agent (W-3): Gemini, with a retry for each busy reply.

    Without retry_options, ADK sends each request once, so ONE "503 busy" from the free tier
    ended a whole build try (W-9 run 1, and the online runs on Render). With it, the google-genai
    library waits and sends that same request again, and the build carries on where it was.
    A call that hangs is cut after CALL_TIMEOUT_SECONDS and sent again the same way.
    """
    # timeout is in milliseconds. A call cut by it counts as a retryable error, like a busy reply.
    # ADK fills in the rest (retry_options, its own headers) around these http_options.
    http_options = types.HttpOptions(timeout=int(CALL_TIMEOUT_SECONDS * 1000))
    return BuilderGemini(model=name, retry_options=BUILDER_RETRY, client_kwargs={"http_options": http_options})


def _call_claude(prompt: str, system: str | None, model: str) -> str:
    raise LLMError("The Claude provider is not set up yet (it needs credits). Use LLM_PROVIDER=gemini.")


# Name -> function. To add a provider, write a function like _call_gemini and list it here.
PROVIDERS = {
    "gemini": _call_gemini,
    "claude": _call_claude,
}


def backup_model() -> str | None:
    """The builder's backup model name (D-018), or None when LLM_BACKUP_MODEL is not set."""
    name = os.environ.get("LLM_BACKUP_MODEL", "").strip()
    return name or None  # an empty setting means "no backup", not a model called ""


def generate(prompt: str, system: str | None = None) -> str:
    """Ask the model and return its reply as text. Raises LLMError with a plain message on any problem."""
    if not prompt.strip():
        raise LLMError("The prompt is empty.")
    if len(prompt) > MAX_PROMPT_CHARS:
        raise LLMError(f"The prompt is too long ({len(prompt)} characters; the limit is {MAX_PROMPT_CHARS}).")

    provider_name = os.environ.get("LLM_PROVIDER", "gemini")
    call = PROVIDERS.get(provider_name)
    if call is None:
        raise LLMError(f"Unknown LLM_PROVIDER '{provider_name}'. Choose one of: {', '.join(PROVIDERS)}.")

    model = os.environ.get("LLM_MODEL")
    if not model:
        raise LLMError("LLM_MODEL is not set. Put a model name in your local .env file.")

    for attempt in range(1, MAX_TRIES + 1):
        try:
            reply = call(prompt, system, model)
            break
        except RateLimited:
            if attempt == MAX_TRIES:
                raise
            _sleep(WAIT_SECONDS * attempt)

    reply = reply.strip()
    if not reply:
        raise LLMError("The model sent an empty reply.")
    return reply


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()  # reads the local .env file
    try:
        print(generate("Say hello in one short sentence."))
    except LLMError as error:
        print(f"Problem: {error}")
        raise SystemExit(1)
