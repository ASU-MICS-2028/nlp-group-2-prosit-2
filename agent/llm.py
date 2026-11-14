"""The only door to the language model (decision D-002).

Everything else in the project calls `generate(...)`. To change the model
provider (Gemini now, Claude later) you change two environment variables,
not the code that uses it.

Settings (environment variables, see .env.example):
  LLM_PROVIDER   which provider to use: "gemini" (default) or "claude"
  LLM_MODEL      the model name for that provider (required)
  GEMINI_API_KEY the secret key for Gemini (never commit it)

Try it:  python -m agent.llm
"""

import os
import time

from google import genai
from google.adk.models import Gemini
from google.genai import types

MAX_TRIES = 3  # how many times we try when the free tier says "slow down"
WAIT_SECONDS = 2  # wait this long after the first failure, twice as long after the second
MAX_PROMPT_CHARS = 20000  # refuse huge prompts instead of burning free quota

# HTTP codes that mean "busy, try again soon": 429 too many requests, 500/504 a server hiccup, 503 overloaded.
BUSY_CODES = [429, 500, 503, 504]

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

# Tests replace this with a fake so they do not really wait.
_sleep = time.sleep


class LLMError(Exception):
    """Something went wrong with the model. The message is safe to show to a user."""


class RateLimited(LLMError):
    """The provider is busy: too many requests (429) or overloaded (503). Worth trying again."""


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
        if error.code in (429, 503):  # too many requests, or overloaded: worth waiting and trying again
            raise RateLimited("The model is busy (free-tier limit). Try again shortly.") from error
        # Only the code is shown: the original message could echo request details.
        raise LLMError(f"The model returned an error (code {error.code}).") from error
    except Exception as error:
        raise LLMError("Could not reach the model. Check the internet connection.") from error

    return response.text or ""


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
    return Gemini(model=name, retry_options=BUILDER_RETRY, client_kwargs={"http_options": http_options})


def _call_claude(prompt: str, system: str | None, model: str) -> str:
    raise LLMError("The Claude provider is not set up yet (it needs credits). Use LLM_PROVIDER=gemini.")


# Name -> function. To add a provider, write a function like _call_gemini and list it here.
PROVIDERS = {
    "gemini": _call_gemini,
    "claude": _call_claude,
}


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
