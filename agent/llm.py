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
from google.genai import types

MAX_TRIES = 3  # how many times we try when the free tier says "slow down"
WAIT_SECONDS = 2  # wait this long after the first failure, twice as long after the second
MAX_PROMPT_CHARS = 20000  # refuse huge prompts instead of burning free quota

# Tests replace this with a fake so they do not really wait.
_sleep = time.sleep


class LLMError(Exception):
    """Something went wrong with the model. The message is safe to show to a user."""


class RateLimited(LLMError):
    """The provider said we are sending too many requests (HTTP 429)."""


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
        if error.code == 429:
            raise RateLimited("The model is busy (free-tier limit). Try again shortly.") from error
        # Only the code is shown: the original message could echo request details.
        raise LLMError(f"The model returned an error (code {error.code}).") from error
    except Exception as error:
        raise LLMError("Could not reach the model. Check the internet connection.") from error

    return response.text or ""


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
