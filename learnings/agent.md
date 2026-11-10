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
- The Claude provider is a placeholder that says "not set up yet". Switching the provider needs paid credits, so D-4 switched only the model name.
- The retry/reflection loop (F-4) does not exist yet. The tools (W-1) and the builder prompt (W-4) are done, see below.

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
- **Safe file names.** Absolute paths (`/etc/passwd`), climbing out (`../x`), `./`, `a//b`, Windows `\` and drive (`C:`) paths are refused.
- **Limits:** at most 30 files and 50,000 characters per file, so a looping model cannot fill memory. Test output sent back to the model is cut to its last 4,000 characters (the pytest summary is at the end), which saves free-tier quota. Files are never cut: `read_file` returns a whole file up to 20,000 characters, or an error, because a model shown half a file rewrites it without the other half.
- **`test_runs` counter:** the agent loop (W-3, F-4) can stop after a set number of test runs.
- **Runner crashes are hidden from the model:** it gets "the test runner itself failed", never our internal error text.

**How to check it**
```
pytest -q agent/tests/test_tools.py    # 28 passed
```
26 tests use a fake runner; 2 use the real sandbox runner (one passing and one failing project). Output: `evidence/agent/outputs_w1_tools_tests_run2.txt` (run 1, before the read_file fix: `outputs_w1_tools_tests.txt`).

**Not done or not tested**
- Not yet run inside a real ADK agent with Gemini; that happens in W-3.
- The runner on `main` still passes our environment (including `GEMINI_API_KEY`) to generated code. The fix is on Elise's `backend/sandbox-runner` branch (F-11) and must be merged before real builds.

**Terms**
| Term | One-line meaning |
|---|---|
| Tool | A plain Python function the agent may ask to run; the model only sends its name and arguments |
| Workspace | One project's files, kept in a dictionary in memory |
| Closure | A function made inside another function that remembers the outer function's variables (here: the workspace) |

## Builder prompt (task W-4, 2026-11-08)
**In one sentence:** `agent/prompts/builder.md` is the standing instruction the ADK agent gets: what to build, in which fixed layout, with which rules, and how to finish.

**What is in it**
1. **Role:** turn the approved plan into a small FastAPI project with tests, for a person who cannot code.
2. **Tools and steps:** say in one sentence what you will build (so the UI has a "Thinking" step), write the files, call `run_tests`, fix failures, stop after 3 failing test runs.
3. **Fixed layout (D-005):** `requirements.txt`, `conftest.py`, `app/__init__.py`, `app/database.py`, `app/main.py`, `tests/test_<table>.py`.
4. **Rules:** only `fastapi`, `pydantic`, `sqlite3` and the standard library (nothing else is installed in the sandbox); `?` placeholders in SQL; plan types mapped to SQLite types; exactly the planned endpoints; 201 / 404 / 204 / 422; plain-English Swagger text; no environment variables, network or outside files.
5. **Test rules:** a normal case and a failure case for every endpoint; never delete or weaken a test to get green.
6. **A complete worked example** (a Notes API, 5 endpoints, 9 tests). Showing one full example is "few-shot prompting": models copy a shown pattern far more reliably than they follow a description.
7. **Final reply:** only JSON, `{"status": "done" | "gave_up", "summary", "tests_passed", "tests_total"}`, so W-3 can read the result without guessing.

**The loader** (`agent/prompts/__init__.py`): `load_prompt("builder")` reads the file; `builder_message(plan)` turns the approved plan into the agent's first message (as JSON), and refuses a plan with no name, endpoints or tables, or one over 10,000 characters.

**ADK trap: curly braces.** When ADK gets instructions as text, it fills in any `{word}` from its session and fails if there is none. Our prompt needs `{note_id}` in its FastAPI example, so W-3 must pass `instruction=builder_instruction()`: a function, which ADK uses as-is (checked in ADK 2.13's source).

**How to check it**
```
pytest -q agent/tests/test_prompts.py    # 18 passed
```
One test cuts the example project out of the prompt and runs it through the real sandbox runner (9 passed). If someone breaks the example, that test fails, because a broken example teaches the model the mistake.

**Live check (2026-11-08, Windows laptop, `gemini-3.5-flash`):** script `evidence/agent/w4_live_check.py`, output `evidence/agent/outputs_w4_live_check.txt`. Given the prompt, the tools from PR #9 and a Bookshop plan (5 fields, 4 endpoints), the agent said one planning sentence, wrote the 6 files of the fixed layout, ran the tests once and they passed. We then ran its files through the sandbox ourselves: **8 passed**. 44 seconds of agent time.
- For the run, the runner was given only `PATH` and `SYSTEMROOT` (the PR #8 fix plus the Windows setting), so the generated code could not see the key.
- The first try failed with Gemini `503` ("high demand"); a retry two minutes later worked. W-3 should treat 503 like a rate limit: wait and retry.
- The final reply was the JSON we asked for, but wrapped in a ```json fence. W-3 must strip a fence before parsing (the check script does this).

## Model switch (task D-4, 2026-11-08 and 2026-11-10)
**In one sentence:** changing only `LLM_MODEL` in `.env` moves every call to another model with no code change, but no second free-tier model finished the Bookshop build.

| Model | What happened |
|---|---|
| `gemini-3.5-flash` (our default) | Built the project, 8 passed (W-4) |
| `gemini-3.5-flash-lite` | Hello worked; in the build it wrote one sentence and stopped without calling a tool |
| `gemini-2.5-flash` | 404: "no longer available to new users" |
| `gemini-3.8-flash`, `gemini-3.7-flash` | 503 "high demand" on every try over two days |

**What it teaches us**
- Tool use depends on the model: a smaller model can ignore the tool instructions and just reply. W-3's loop should notice "finished without writing a file" and re-prompt once (part of F-4).
- What the free tier offers changes without warning, so keep `gemini-3.5-flash` as the default and treat 404/503 as "pick another model or wait", not as a bug.
- Evidence: `evidence/agent/outputs_d4_model_switch.txt`.

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
- The model is a setting: changing one line in `.env` switched every call to another model with no code change. Whether the agent still succeeds depends on the model: a smaller model stopped without using its tools.
