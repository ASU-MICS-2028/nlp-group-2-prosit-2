# Agent (LLM wrapper)

Owner: Opei (S-4 picked up by Perfect, see Handovers in PLAN.md and D-009) · Last updated: 2026-11-02 · Status: partly working (code and tests done; **never run against the real Gemini API yet**)

## 1. In one sentence
One small file, `agent/llm.py`, is the only place that talks to the language model, so changing from Gemini to Claude later means changing two settings and not the code.

## 2. What I did, step by step
1. Wrote `generate(prompt, system=None)`: send text to the model, get text back.
2. It reads settings from environment variables: `LLM_PROVIDER` (gemini or claude), `LLM_MODEL`, and `GEMINI_API_KEY`.
3. Added safety around the call: refuse empty or huge prompts, retry when the free tier says "slow down" (waiting 2 s, then 4 s, up to 3 tries), turn every failure into one plain `LLMError` message, and refuse empty replies.
4. Wrote 18 tests with a fake model and a fake Gemini client.
5. Added `python -m agent.llm`, a hello-world you run once you have a key.

## 3. Why we did it this way
- **One door (D-002):** no other file imports a model library, so switching provider touches one file.
- **Providers in a plain dictionary:** adding one means writing one function and one line.
- **Retry only on rate limits:** a wrong key will not get better by trying again, so other errors fail straight away.
- **Short, safe messages:** an unexpected provider error shows only its code, because its text could contain request details.
- **Free tier friendly:** huge prompts are refused before they use up quota.

## 4. How to check it works
From the repo root, with the virtual environment on (`source backend/.venv/bin/activate`):
```
pytest -q agent            # 18 passed
```
Live check, once you have a free key from Google AI Studio:
1. Copy `.env.example` to `.env` and fill in `GEMINI_API_KEY` and `LLM_MODEL` (a free model name from AI Studio). `.env` is ignored by git; never paste the key into chat.
2. `python -m agent.llm` should print a short greeting.
Common messages: "GEMINI_API_KEY is not set" (fill `.env`), "LLM_MODEL is not set", "The model is busy" (free-tier limit, wait a minute).

## 5. What is NOT done or is faked
- **The real Gemini call has never been run.** Only a fake client was tested, so a wrong model name or an SDK mismatch would show up only in the live check.
- The Claude provider is a placeholder that says "not set up yet". The provider-switch proof (task D-4) needs credits.
- Tool definitions (W-1), the system prompt (W-4) and the retry/reflection loop (F-4) do not exist yet.

## 6. What will bite us
- Free-tier limits change and can be low: the evaluation (20 requests, each several calls) may hit them. Pace requests.
- Model names change over time; `LLM_MODEL` is deliberately not hard-coded.
- The `google-genai` library is new and moves fast; it is pinned in `backend/requirements.txt`.
- Never print the full request or the key in logs.

## 7. Terms used
| Term | One-line meaning |
|---|---|
| LLM | Large language model: the AI that reads text and writes text |
| Provider | The company running the model (Google for Gemini, Anthropic for Claude) |
| API key | A secret password that lets our code use the provider's service |
| Rate limit (HTTP 429) | The provider telling us we sent too many requests too fast |
| System prompt | Standing instructions given to the model before the user's text |
| Environment variable | A setting kept outside the code, here in the `.env` file |
| Fake / mock | A stand-in used in tests so they do not call the real service |

## 8. Lines ready for the report
- All model calls go through one wrapper, so the provider can be swapped by configuration.
- The wrapper retries rate-limited calls with increasing waits and fails fast on other errors.
- Tests use a fake model so they are quick, free and repeatable.
