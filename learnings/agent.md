# Agent (LLM wrapper and tools)

Owner: Opei (S-4 picked up by Perfect, see Handovers in PLAN.md and D-009) · Last updated: 2026-11-02 · Status: partly working (wrapper run live once on 2026-11-04; ADK spike works; tools built 2026-11-07; prompts and agent loop not built yet)

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
- The real Gemini call has been run **once** (2026-11-04, model `gemini-3.5-flash`, evidence in `evidence/agent/outputs_s4_llm_hello.txt`). Behaviour under load, rate limits and the retry waits have not been tried against the real service.
- The Claude provider is a placeholder that says "not set up yet". The provider-switch proof (task D-4) needs credits.
- The system prompt (W-4) and the retry/reflection loop (F-4) do not exist yet. The tools (W-1) are done, see below.

## ADK spike result (task W-10, 2026-11-04)
Question: can Google's Agent Development Kit (D-010) run a tiny agent with a tool on our free Gemini key?
**Yes.** Script: `evidence/agent/adk_spike.py`; output: `evidence/agent/outputs_w10_adk_spike.txt`.
- **What I ran:** an agent with one tool, `write_file`, asked to create two files. ADK made the model call, ran the tool, fed the result back, called the tool a second time and then gave a final answer. We wrote no loop code. It took 10 to 15 seconds.
- **Setup facts:** `pip install google-adk` (version 2.13.0) installed without clashing with the versions we already pin (`google-genai`, `fastapi`). The key must be available as `GOOGLE_API_KEY` (our `.env` calls it `GEMINI_API_KEY`, so our code copies it across). A tool is a plain Python function; its docstring and type hints tell the model how to use it.
- **Events** (what the UI timeline needs): each step arrives as an event with an author and parts: a tool call (name and arguments), a tool result, or text. A final-response flag marks the end. That maps onto our Thinking / Doing / Result steps: tool call = Doing, tool result = Result. The model gave no "thinking" text before calling the tools; if we want those steps we have to ask for them in the instructions.
- **What to keep of `agent/llm.py`:** the settings (`LLM_MODEL`, the key) and one-off calls. ADK makes the model calls inside the agent.
- **Not checked yet:** what happens when the free tier says "slow down" inside an ADK run, running many projects at once, and how to cap steps and time per build. Check these when W-3 is built.
- **Dependencies:** `google-adk` is not in `backend/requirements.txt` yet. Add it (pinned) in the PR that builds W-3, so CI does not install it before it is used.

## Tools for the agent (task W-1, 2026-11-07)
**In one sentence:** `agent/tools.py` gives the ADK agent four "hands" (write a file, read a file, list the files, run the tests), because the model itself can only write text.

**How it works, step by step**
1. Each project gets a `Workspace`: a dictionary `{file name: file text}` plus a counter `test_runs`. Nothing is written to our disk.
2. `make_tools(workspace)` returns the four functions. They are made inside `make_tools` so each one already knows its project's workspace. The ADK agent gets them with `Agent(..., tools=make_tools(workspace))`.
3. ADK reads each function's name, type hints and docstring and tells the model how to call it. Checked: ADK turns `write_file` into a description with `path` and `content` as required text fields.
4. `run_tests` passes the dictionary to `backend/runner.run_tests`, which copies it into a throwaway folder and runs pytest with a 30-second limit.

**Why this way**
- **Tools never raise.** A bad call returns `{"status": "error", "message": ...}`. The model reads the message and tries again, instead of the whole build crashing.
- **Safe file names.** Absolute paths (`/etc/passwd`), climbing out (`../x`), `./`, `a//b` and Windows `\` paths are refused.
- **Limits:** at most 30 files and 50,000 characters per file, so a looping model cannot fill memory. Text sent back to the model is cut to its last 4,000 characters (the pytest summary is at the end), which saves free-tier quota.
- **`test_runs` counter:** the agent loop (W-3, F-4) can stop after a set number of test runs.
- **Runner crashes are hidden from the model:** it gets "the test runner itself failed", never our internal error text.

**How to check it**
```
pytest -q agent/tests/test_tools.py    # 26 passed
```
24 tests use a fake runner; 2 use the real sandbox runner (one passing and one failing project). Output: `evidence/agent/outputs_w1_tools_tests.txt`.

**Not done or not tested**
- Not yet run inside a real ADK agent with Gemini; that happens in W-3.
- The runner on `main` still passes our environment (including `GEMINI_API_KEY`) to generated code. The fix is on Elise's `backend/sandbox-runner` branch (F-11) and must be merged before real builds.

**Terms**
| Term | One-line meaning |
|---|---|
| Tool | A plain Python function the agent may ask to run; the model only sends its name and arguments |
| Workspace | One project's files, kept in a dictionary in memory |
| Closure | A function made inside another function that remembers the outer function's variables (here: the workspace) |

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
