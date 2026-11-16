# Backend

Owner: Elise (S-5 picked up by Perfect, see Handovers in PLAN.md and D-009) · Last updated: 2026-11-14 · Status: partly working (skeleton, sandbox runner, project endpoints, agent loop, project list, end-to-end build)

## 1. In one sentence
A small Python server (FastAPI) that the web UI will call; today it only answers "are you awake?" and publishes its own API description.

## 2. What I did, step by step
1. Created `backend/main.py` with a FastAPI `app` and one endpoint, `GET /health`, that returns `{"status": "ok"}`.
2. Added CORS settings so the browser lets the frontend (on another address) call the server. Allowed addresses come from the `ALLOWED_ORIGINS` environment variable, in `backend/config.py`.
3. Wrote tests for the normal case and for failure cases (unknown path, wrong method, allowed and disallowed origins, settings parsing).
4. Pinned the library versions in `backend/requirements.txt`; added `pytest.ini` so tests run from the repo root.
5. Wrote the API contract the frontend needs: `docs/api-contract.md` (D-008).

## 3. Why we did it this way
- **FastAPI**: small, readable, and it builds the OpenAPI description by itself, which the frontend client is generated from (D-001).
- **One config file**: environment settings are read in one place, so nobody hunts for them.
- **CORS limited to named addresses**: a random website cannot call our server from a user's browser.
- **Pinned versions**: the same code behaves the same on every laptop and in CI.

## 4. How to check it works
From the repo root:
```
python3 -m venv backend/.venv
source backend/.venv/bin/activate
pip install -r backend/requirements.txt
pytest -q                                   # 9 passed
uvicorn backend.main:app --reload           # then in another terminal:
curl -i http://localhost:8000/health        # 200 and {"status":"ok"}
```
Open http://localhost:8000/docs to see the interactive API page.

Two things people trip over:
- Run every command from the **repo root** (`nlp-group-2-prosit-2`), not from `backend/`.
- The virtual environment is switched on **per terminal window**. In a new terminal, run `source backend/.venv/bin/activate` again, or you get `command not found: uvicorn`. The prompt starts with `(.venv)` when it is on.

## 5. What is NOT done or is faked
- Only `/health` exists. The real endpoints (projects, answers, approve, events, download) are task W-5 and are described in `docs/api-contract.md`, which Elise has not reviewed yet.
- No sandbox runner (W-2), no agent loop (W-3), no storage.
- CORS and tests were checked locally; the first CI run has not been confirmed.

## 6. What will bite us
- `pytest` prints a warning that `httpx` is deprecated in Starlette's test client and suggests `httpx2`. It is only a warning today; if a future upgrade breaks the tests, switch the package.
- Run commands from the **repo root**, not from `backend/`, or imports like `backend.main` fail.
- Free-tier hosts sleep when idle, so the first call can take half a minute.
- `ALLOWED_ORIGINS` must be set to the real Vercel address in production, or the browser will block every call.

## 7. Terms used
| Term | One-line meaning |
|---|---|
| FastAPI | A Python library for building web APIs |
| Endpoint | One address the server answers, like `/health` |
| OpenAPI | A machine-readable description of every endpoint; FastAPI makes it for us |
| CORS | The browser rule that decides which web pages may call a server |
| Virtual environment (venv) | A private folder of Python libraries for this project |
| pytest | The Python test runner |
| Pinned version | A library listed with an exact version so it never changes under us |

## 8. Lines ready for the report
- The backend is a FastAPI server whose published OpenAPI schema is the single contract with the frontend.
- Settings come from environment variables; secrets never live in the repository.
- Tests cover both normal and failure paths (unknown path, wrong method, disallowed browser origin).

---

# W-2 Sandbox runner (Elise, 2026-11-03)

## 1. In one sentence
`run_tests(files)` in `backend/runner.py` takes the files the AI wrote, runs their tests safely in a throwaway folder, and says whether they passed.

## 2. What I did, step by step
I wrote each test first, watched it fail, then wrote the code to make it pass.
1. A passing project gives `passed=True`; a failing project gives `passed=False` (pytest's exit code 0 means "all passed").
2. The files go into a throwaway folder (`tempfile.TemporaryDirectory`) that is deleted at the end, even if something goes wrong.
3. pytest runs as a separate program (`subprocess.run`) inside that folder.
4. Time limit: an endless loop is stopped after `timeout_seconds` (default 30) and we report `timed_out=True`.
5. File names that try to leave the folder (`../x.py`, `/tmp/x.py`) are refused with "Unsafe file name".
6. Files in sub-folders (`app/main.py`) work: missing folders are made first.
7. A project over 200,000 characters is refused before anything is written.
8. After review (PR #3): pytest gets only `PATH` from our environment, so it can't read our API key.
   After review (PR #8): also `SYSTEMROOT` (Windows needs it to start Python's networking parts; not a secret), and error messages (stderr) are kept, so a crash's reason reaches the AI.
9. After review: we keep only the last 20,000 characters of pytest's output.

## 3. Why we did it this way
- **Separate program + time limit**: AI-written code can't be trusted. If it crashes or loops forever, our server keeps working (D-007).
- **Only PATH (and SYSTEMROOT) are passed on**: a "keep only these" list is safer than a "remove these" list. A new secret added later is left out automatically.
- **Keep the last part of the output**: pytest's summary (what failed and why) is at the end, and the AI will read this to fix its code.
- **Problems are reported, not raised as errors**: the agent loop (W-3) can show the message to the AI so it can fix its files.

## 4. How to check it works
From the repo root, with the venv active:
```
python -m pytest -v backend/tests/test_runner.py    # 9 passed
```
Saved output: `evidence/backend/outputs_w2_runner_tests_run2.txt` (local folder path replaced with `<repo>`).

## 5. What is NOT done or is faked
- This is a **demo sandbox**, not real isolation. AI-written code can still read other files on the computer and use the network (D-007). The report must say so.
- No automated test checks that the throwaway folder is really deleted. We rely on Python's `TemporaryDirectory`.
- Nothing calls the runner yet except tests. The agent loop (W-3) will.

## 6. What will bite us
- If generated code needs another environment variable to work (for example `HOME`), it won't have it. Add only what is needed, never keys.
- Windows needs `SYSTEMROOT`; without it, pytest can't start there (`WinError 10106`). CI runs on Linux, so it would not notice.
- `pytest` must be installed in the same Python that runs the server, because we start it with `sys.executable`.
- Locally, run tests with `python -m pytest`, not plain `pytest`. Plain `pytest` can pick up a different Python (like Anaconda's).

## 7. Terms used
| Term | One-line meaning |
|---|---|
| Sandbox | A closed-off place to run code we don't trust |
| Subprocess | A separate program our code starts and waits for |
| Exit code | The number a program gives back when it ends; 0 means success |
| Timeout | A time limit; the program is stopped if it goes over |
| Temporary folder | A throwaway folder the system makes for us |
| Environment variable | A named value a program gets when it starts, like our API key |
| Path traversal | Using `../` in a file name to reach files outside the allowed folder |
| `monkeypatch` | A pytest helper that changes something (like an env variable) for one test only |

## 8. F-11 security checklist (results so far)
| Check | How it was checked | Result |
|---|---|---|
| Input size limit | `test_too_big_project_is_refused` | ✅ passes |
| Output size limit | `test_long_output_is_trimmed` | ✅ passes |
| Sandbox timeout | `test_endless_project_is_stopped_by_the_timeout` | ✅ passes |
| No files written outside the folder | `test_file_name_that_leaves_the_folder_is_refused` | ✅ passes |
| Our API key is hidden from AI code | `test_secret_keys_are_hidden_from_ai_code` | ✅ passes |
| A crash's reason reaches the AI (stderr kept) | `test_crash_message_is_kept` | ✅ passes |
| Temporary folder is deleted | not tested automatically (Python's `TemporaryDirectory` does it) | ⚠️ not tested |
| No secrets in the server's logs | the server has no logging yet | ⬜ not done |
| AI code can't read other files | not possible without containers (D-007) | ⚠️ known limit |

## 9. Lines ready for the report
- Generated code runs in a temporary folder as a separate process, with a time limit, input and output size limits, and no access to our API keys.
- It is a demo sandbox, not production isolation: generated code can still read other files and use the network.

# W-5 Project endpoints (Elise, 2026-11-09)

## 1. In one sentence
Three endpoints in `backend/projects.py` let the web page start a project, check its status, and watch its progress live; there is no AI behind them yet.

## 2. What I did, step by step
Each endpoint: test first, watch it fail, then the code.
1. `POST /projects` takes `{"request": "..."}` and answers `201` with `{"id": "p_1", "status": "waiting", "questions": []}`.
2. `GET /projects/{id}` answers `{"id", "status"}`, or `404` with `{"detail": "Project not found."}`.
3. The request must be 1 to 2000 characters (`Field(min_length=1, max_length=2000)`); otherwise `422`. Spaces at the start and end are trimmed first, so a request of only spaces is refused.
4. A handler in `backend/main.py` turns FastAPI's technical 422 list into one plain sentence, as the contract promises. Broken JSON gets "The request body is not valid JSON."
5. `GET /projects/{id}/events` is a live stream (SSE). It sends the project's whole diary of events, then any new ones, and hangs up at `ready`, `failed` or `stopped`.
6. `add_event(project_id, event)` writes to the diary. The agent (W-3) will call it; tests call it to pretend to be the agent.

## 3. Why we did it this way
- **Memory, not a database (D-013)**: nothing to install; all storing code is in one file, so a database can replace it later.
- **`questions` is always `[]`**: the AI that writes questions doesn't exist yet, and fake questions would be pretend data. The field is still sent so the page always gets the same shape.
- **Check input on the server**: never trust the browser; anyone can call the API directly.
- **SSE, not WebSockets**: only the server has news to tell during a build. SSE is a normal web request and browsers reconnect by themselves.
- **`Depends(find_project)` for the 404**: once a stream starts, `200` is already sent. The check must run before. It also keeps the "not found" rule in one place.
- **FastAPI's built-in SSE** (`fastapi.sse.EventSourceResponse`): no extra library, and it sends `: ping` keep-alive lines by itself.

## 4. How to check it works
```
python -m pytest -v backend/tests/test_projects.py      # 10 passed
uvicorn backend.main:app --reload                       # then, in another tab:
curl -X POST http://localhost:8000/projects -H "Content-Type: application/json" -d '{"request": "A to-do list API"}'
curl -N http://localhost:8000/projects/p_1/events       # data: {"status":"waiting"}, then ": ping" lines; Ctrl+C to stop
```
Or open http://localhost:8000/docs and use "Try it out" (not for the stream: the docs page waits for it to finish, and it never does while the project is waiting).
Saved output: `evidence/backend/outputs_w5_endpoint_tests.txt`, `evidence/backend/outputs_w5_curl_stream.txt`.

## 5. What is NOT done or is faked
- No AI behind the endpoints: projects stay `waiting` forever, and `questions` is always `[]`.
- Projects are lost when the server restarts (memory only).
- `GET /projects/{id}` returns only `id` and `status`; the contract's other fields come later.
- Not built: `GET /projects` (W-8, Perfect), answers, approve, download, wake (later tasks).
- No automated test pushes a *new* event into an already-open stream; only the history and the hang-up are tested. Checked by hand with curl: the stream stays open and pings.
- No automated test for a browser hanging up on `/events` (listed in `backend/AGENTS.md`). Checked by hand: after Ctrl+C in curl, the server log showed no errors and kept serving. FastAPI stops the stream when the connection closes.
- Ids are `p_` + a counter. Fine for one server in memory; a database would give ids instead.

## 6. What will bite us
- A stream for a `waiting` project never ends. Fine for the browser (it closes the tab), but a test that opens one without a final event hangs forever.
- The `/docs` page can't show a stream. Use curl with `-N`.
- `!` before a command only works in Claude Code; in a normal terminal, `cd` into the repo first.

## 7. Terms used
| Term | One-line meaning |
|---|---|
| Endpoint | One address the server answers, like `POST /projects` |
| GET / POST | GET reads something; POST sends data to create something |
| Status codes | 200 OK · 201 Created · 404 Not found · 422 Input breaks a rule · 500 Server broke |
| Router | A group of endpoints in their own file, plugged into the app |
| Pydantic model (`BaseModel`) | A description of the shape of data in or out; FastAPI checks input against it |
| `TestClient` | A pretend browser that calls the app in tests without starting a server |
| SSE | Server-Sent Events: an open line where the server pushes messages as things happen |
| `yield` | Like `return`, but the function pauses and can send more later |
| `async` / `await` | Lets a function pause (e.g. wait half a second) without blocking other users |
| `Depends` | "Run this function first and give me its answer" |
| curl | A terminal command that calls a web address |

## 8. Lines ready for the report
- The backend exposes a small REST API (start, status) plus a Server-Sent Events stream, so the UI shows the agent's progress live instead of polling.
- Every error, including invalid input, is one plain-English sentence, so a non-developer sees a readable message.
- Projects are held in memory for now (D-013); the storage code is isolated so a database can replace it.

---

# W-3 Agent loop (Elise, 2026-11-10)

## 1. In one sentence
`build_project(...)` in `backend/builder.py` lets the AI build a project with its tools, reports each step live, stops it with a plain reason when things go wrong, and checks the result itself.

## 2. What I did, step by step
Each part: test first (with a fake AI), watch it fail, then the code.
1. A `FakeModel` in `backend/tests/test_builder.py`: a pretend AI that reads a script of replies, so tests are free, quick and the same every time.
2. Happy path: the AI writes a file, runs the tests, says it's done; we re-run the tests ourselves and answer `ready`.
3. Live steps: each ADK event becomes a timeline step (`Thinking`, `Doing`, `Result`, as in the contract) sent to `report(...)`. The last event carries the final status, which also ends the W-5 stream.
4. Five stop rules, each ending `failed` with a plain reason (table below).
5. One real build with Gemini (`evidence/backend/w3_live_check.py`).

| # | When | Reason the person sees |
|---|---|---|
| 1 | 3 test runs and still failing (`MAX_TEST_RUNS`) | "The tests still fail after 3 tries." |
| 2 | The AI wrote no files | "The AI stopped without writing any files." |
| 3 | The AI service errors (503 busy, 429, bad key) | "The AI service is busy or unavailable. Please try again in a few minutes." |
| 4 | 40 AI moves in total (`MAX_AI_CALLS`, ADK's `max_llm_calls`) | "The AI took too many steps without finishing." |
| 5 | 5 minutes in total (`TIME_LIMIT_SECONDS`) | "The build took too long and was stopped." |

## 3. Why we did it this way
- **Google ADK runs the back-and-forth (D-010)**; we own setup, reporting, stop rules and the verdict.
- **Inputs, not imports**: `message`, `instruction`, `model` and `report` are passed in, so tests can pass fakes and W-3 didn't depend on unmerged work. W-9 connects the real pieces (`add_event`, the server).
- **Fake AI in tests**: only the AI's replies are pretend. ADK, the tools, the runner and our rules are real. We test our manager code, not Gemini.
- **Limits enforced in code, not only in the instructions**: instructions are a request, code is a rule.
- **We re-run the tests ourselves**: the AI could claim success, change a file after its last run, or skip the tools.
- **Always report a final status**: otherwise the live stream never ends and the Building screen spins forever.

## 4. How to check it works
```
python -m pytest -v backend/tests/test_builder.py      # 7 passed, no key needed
python -m evidence.backend.w3_live_check               # real Gemini build; needs GEMINI_API_KEY and LLM_MODEL in .env
```
Saved: `evidence/backend/outputs_w3_builder_tests.txt`, `evidence/backend/outputs_w3_live_check.txt` (model `gemini-3.5-flash`, `ready`, 5 of 5 tests, 106 s).

## 5. What is NOT done or is faked
- Not connected to the server yet: nothing calls `build_project` from an endpoint. That is W-9 (with `add_event` as `report`).
- No retry: a busy AI service or a model that writes nothing ends the build. Waiting and retrying, and asking the AI again, is F-4.
- The AI's final reply is JSON in a ```json fence and shows as a raw "Thinking" step. Hide or parse it in W-9.
- The time limit can't interrupt a test run already in progress (that code doesn't pause), but the runner has its own 30-second limit.
- One real build was tried, with one model. Larger plans and busy hours are untested.

## 6. What will bite us
- `LLM_MODEL` must be set in `.env`. If it's empty, ADK quietly uses its own default model. The live check refuses to run without it.
- ADK reads the key as `GOOGLE_API_KEY`; our `.env` calls it `GEMINI_API_KEY`, so the live check copies it across.
- Tests print yellow "missing token usage metadata" warnings: harmless, the fake AI doesn't report tokens.
- Run the live check only on a branch with the F-11 runner fix, so AI-written code can't see the key.

## 7. Terms used
| Term | One-line meaning |
|---|---|
| Agent | An AI that can use tools in a loop, not just reply once |
| Google ADK | Google's Agent Development Kit: runs the AI ↔ tools back-and-forth for us |
| Event | One thing that happened in ADK: the AI wrote text, asked for a tool, or got a tool's result |
| Fake model | A pretend AI that reads a script, used in tests |
| Stop rule | A condition where we stop the AI ourselves and say why |
| Token | A small piece of a word; AI services count usage in tokens |
| `asyncio.timeout` | A stopwatch around async code; raises `TimeoutError` when it runs out |
| `try / except / else` | Run this; if error X happens do that instead of crashing; `else` runs only if there was no error |

## 8. Lines ready for the report
- The agent loop uses Google ADK for the model ↔ tool cycle; our code adds live progress, five stop rules with plain reasons, and an independent re-run of the tests.
- It was tested with a scripted fake model (free, deterministic) and confirmed with one real Gemini build that passed 5 of 5 tests in 106 seconds.

---

# W-8 List projects (Elise, taken from Perfect, 2026-11-11)

## 1. In one sentence
`GET /projects` in `backend/projects.py` returns every project, newest first, for the sidebar.

## 2. What I did, step by step
1. Each project now stores `updated_at`, set when it is created and again on every `add_event`, so an active project moves to the top.
2. `ProjectSummary` has the contract's four fields: `id`, `name`, `status`, `updated_at`.
3. `name` is a stand-in until F-2's plan names the project: the start of the request, cut at a word to about 40 characters, with "…".
4. `list_projects` sorts by `updated_at`, latest first.
5. Three tests: newest first, exactly the contract fields, and the long-name cut.

## 3. Why we did it this way
- **UTC times** mean the same on every computer and server.
- **Sorting the time as text works** because ISO 8601 writes the biggest part first (year, month, day, hour…).
- **A stand-in name, not an empty one**: an empty line in the sidebar is useless to the person.
- **Cut at a word**: "list…" reads better than "list t…".

## 4. How to check it works
```
python -m pytest -v backend/tests/test_projects.py     # 13 passed
curl http://localhost:8000/projects                    # with the server running
```
Saved: `evidence/backend/outputs_w8_list_projects_tests.txt`.

## 5. What is NOT done or is faked
- `name` is not a real name yet (F-2).
- No pagination: every project comes back at once. Fine for a demo; future work for many projects.
- The list is lost when the server restarts (memory only, D-013).

## 6. What will bite us
- The tests share one in-memory list, so they check only the top of the list (the projects they just made), never the whole list.

## 7. Terms used
| Term | One-line meaning |
|---|---|
| UTC | World time, the same everywhere |
| ISO 8601 | A standard way to write dates and times, biggest part first: `2026-11-11T09:30:00+00:00` |
| `sorted(..., key=..., reverse=True)` | Put items in order by one part of each item, biggest first |
| Pagination | Sending a long list a page at a time |

## 8. Lines ready for the report
- The sidebar list is sorted by last change, so a project the agent is working on rises to the top.

---

# W-9 End-to-end (Elise, 2026-11-14)

## 1. In one sentence
Sending a request on the chat screen now starts a real build: `POST /projects` starts `run_build` in the background, which runs Opei's retry loop around our builder and writes every step into the project's diary, so the screen shows it live.

## 2. What I did, step by step
1. A test fixture swaps the build job for a fake in every project test, so no test ever calls the real AI.
2. `POST /projects` adds `run_build` to FastAPI's `BackgroundTasks`: it answers first, then builds.
3. `run_build` gives the AI the request as written (until F-2's plan), calls `build_with_retries` with `add_event` as the reporter, and keeps the result.
4. Two safety stops: no `LLM_MODEL` → `failed` with a reason; any unexpected error → `failed` with "Something went wrong on our side", so the screen never spins forever.
5. `GET /projects/{id}` now returns `name`, `file_count`, `size_kb`, `tests_passed`, `tests_total` (null until the build ends).
6. Live runs from the chat screen (evidence below).

## 3. Why we did it this way
- **Background, not waiting**: a build takes minutes. The page needs the id at once to open the live stream.
- **`BackgroundTasks`, not threads or a job queue**: built into FastAPI, no new library, enough for a demo.
- **Call the retry loop, not the builder directly**: Opei's loop already retries and sends `attempt` and `max_attempts`, which Perfect's screen shows.
- **The server reads `.env` with `uvicorn --env-file .env`**: no new code; the key stays out of the repo. Google's library reads `GEMINI_API_KEY` by itself.
- **Test counts from our own test run**, not from what the AI says.
- **null, not 0, before the end**: "not known yet" is different from "zero".

## 4. How to check it works
```
python -m pytest -q                                    # 130 passed, no key needed
uvicorn backend.main:app --reload --env-file .env      # terminal 1
cd frontend && npm run dev                             # terminal 2, then open http://localhost:5173
```
Saved:
- `evidence/backend/outputs_w9_run1_too_slow.txt`: run 1. Gemini was busy, then too slow; all 3 tries stopped with plain reasons and the stream ended.
- `evidence/backend/outputs_w9_run2_ready.txt` and the screenshots `evidence/backend/w9_run2_ready_end.png` and `w9_run2_ready_scroll_fix.png` (the same end, after the timeline was made to scroll inside its panel): run 2, "an api for note book". Ready on try 1: 6 files, 7 KB, 10 of 10 tests. Gemini said "busy" after the last file, and the retry loop ran the tests itself instead of starting again.

## 5. What is NOT done or is faked
- No questions or plan yet: the AI builds from the raw request. F-2 adds them.
- No link to the finished API yet (F-12, F-13, F-14).
- `tests` (one pass/fail per test) is not sent yet; the page hides it.
- Results are in memory and lost on restart (D-013).

## 6. What will bite us
- (Fixed 2026-11-14 on the F-16 branch) The AI's closing JSON report no longer shows as a raw "Thinking" line: `is_json_report` in `builder.py` skips it.
- Saving a backend file while a build runs restarts the server (`--reload`) and the build is lost.
- `run_tests` uses `subprocess.run`, which blocks: while the generated tests run (up to 30 s), the server answers nobody and the live stream pauses.
- On a busy free tier one AI reply can take a minute, so a build hits the 5-minute limit. Run again later or try another Gemini model.
- The request goes to the builder as written; a person could try to give it other instructions (prompt injection). The sandbox (F-11) limits the damage.

## 7. Terms used
| Term | One-line meaning |
|---|---|
| End-to-end | The whole path works: from the screen, through the server and AI, back to the screen |
| `BackgroundTasks` | FastAPI's "do this after you have replied" list |
| `lambda` | A tiny one-line function without a name |
| Fixture (`autouse=True`) | Set-up code pytest runs before every test in the file, without being asked |
| `--env-file` | Tells uvicorn to read settings from a file such as `.env` |
| `re.findall` | Find every piece of text that matches a pattern, e.g. a number before "passed" |

## 8. Lines ready for the report
- The platform answers a request at once and builds in the background; every agent step is pushed to the browser as it happens.
- The first live run met a busy free tier: the system retried, stopped each try with a plain reason, and ended cleanly instead of hanging.
- The second live run built a Notebook API from one sentence: 6 files and 10 passing tests, shown live in the browser.

---

# F-17 A fixed `phase` on every step (Perfect took this from Elise, 2026-11-14)

**In one sentence:** every timeline step the backend sends now has a `phase` (`planning`, `writing`, `testing`, `fixing` or `finishing`), so the page can show plain lines without reading the sentences. Elise: please read this before the teach-back.

**What changed**
- `backend/builder.py`: `PHASES` and `TOOL_PHASES` (which tool belongs to which phase), `phase_of(tool)`, and a `phase` in every step made by `step_from_part` and `result_step`. The AI's own words get `planning` before it has used a tool, `fixing` after, and `finishing` when it is the AI's closing reply (`event.is_final_response()`). The build's final verdict is `finishing`.
- `agent/retry.py` and `backend/projects.py`: their steps carry a phase too (`fixing` for "trying again", `finishing` for the final result).
- The sentences in `text` did not change.

**How to check it:** `python -m pytest -q` (142 passed). The 8 new tests: every step of a good, a failing and a no-files build has a known phase; each tool has its phase; a tool error keeps its phase; the AI's words get the phase the loop gives them; a retried build and a failed start also carry one. Output: `evidence/backend/outputs_f17_phase_tests.txt`. I also removed one phase on purpose and checked a test failed (`KeyError: 'phase'`), then put it back.

**Not done / limits:** an unknown tool counts as `writing`. `fixing` is a guess from position (the AI's words after it used a tool), which matches what `builder.md` asks it to write. Real Gemini output has not been looked at with the new field.

---

# F-5 Take-home zip (Nana took this from Elise, 2026-11-15)

**In one sentence:** `GET /projects/{id}/download` hands back a ready project's files as a `.zip`, so a person can keep their API and run it on their own computer. Elise: please read this before the teach-back.

**What changed**
- `backend/projects.py`: `zip_files(files)` packs the files into a zip in memory (`io.BytesIO`, no temp file), and the endpoint `download_project` sends it with `Content-Disposition: attachment; filename="p_1.zip"`, so the browser saves it.
- Only a **ready** project can be downloaded; anything else is `409` with "The API is not ready yet, so there is nothing to download." (as `docs/api-contract.md` says). A failed build's files are not offered: their tests fail. An unknown id is `404` (the same `find_project` as the other endpoints).
- File names go into the zip as they are. They are safe already: the agent's `write_file` tool (`clean_path` in `agent/tools.py`) refuses `../`, absolute paths and drive letters, so unzipping cannot write outside the folder.

**How to check it:** `python -m pytest backend/tests/test_download.py -v` (5 passed; all 5 failed before the endpoint existed). The PLAN's "done when" is the last test: it downloads the builder prompt's example project (a Notes API), unzips it into a temporary folder, checks nothing changed, and runs its tests with our sandbox runner: they pass. A real local server answered `409` for a failed build and `404` for an unknown id. Output: `evidence/backend/outputs_f5_download.txt`.

**Not done / limits**
- Not tried with a real Gemini-built project: today's free quota was used up. The example project has the same layout the builder writes.
- No Dockerfile or README in the zip. The contract's `run_command` ("docker compose up") is not sent yet; the person needs Python and `pip install -r requirements.txt`.
- Projects live in memory (D-013): after Render restarts or sleeps, an old project's download is `404`.
- The page has no download button yet (F-14, Perfect).

**Terms**
| Term | One-line meaning |
|---|---|
| `io.BytesIO` | A pretend file kept in memory; we write the zip into it and then read the bytes out |
| `ZIP_DEFLATED` | The zip setting that compresses the files (the default only stores them) |
| `Content-Disposition: attachment` | A header that tells the browser to save the reply as a file, under the name given |
| `409 Conflict` | "Not at this step yet": the request is fine, but the project isn't ready |

---

# F-12 Live runner (Nana took this from Elise, 2026-11-15)

**In one sentence:** `backend/live.py` starts a finished project as its own small server on this computer, so people can really call it; F-13 will pass calls from `/apis/{id}/...` through to it. Elise: please read this before the teach-back.

**How it works**
1. `start(project_id, files)` writes the files into a new throwaway folder (`live_...`), with the same `../` check as the test runner.
2. It asks the system for a free port and starts `python -m uvicorn app.main:app --host 127.0.0.1 --port <port>` in that folder. `127.0.0.1` means only our own backend can reach it, not the internet.
3. It waits until the API answers `/openapi.json` (every FastAPI app has it). If the process ends by itself, it was broken: "The API could not start. Its code has a problem." If it takes longer than 30 seconds, it is stopped with a plain message.
4. The API's environment is `minimal_environment()`, now shared with `run_tests` in `backend/runner.py`: only `PATH` and `SYSTEMROOT`, never our key.
5. Its log goes to `DEVNULL` (thrown away). A pipe that nobody reads fills up and freezes the program.

**The limits** (top of `backend/live.py`)
| Rule | Value | Why |
|---|---|---|
| `MAX_RUNNING` | 3 | D-011. Starting one more stops the API nobody has used for the longest time (smallest `last_used`) |
| `IDLE_SECONDS` | 10 minutes | An unused API is stopped (`stop_idle`), to save memory. Its data (`app.db` in its folder) is lost |
| `START_TIMEOUT_SECONDS` | 30 | An API that never answers can't hang the server |
| a lock | one start or stop at a time | Two starts at the same moment could otherwise both see "2 running" and go over the limit |

Stopping: `terminate()`, wait up to 5 seconds, then `kill()`. The folder is deleted only after the process has ended, because on Windows a running process keeps its files locked. Starting an API that crashed deletes its old folder first.

**How to check it:** `python -m pytest backend/tests/test_live.py -v` (13 passed; real servers, about 20 seconds, no AI). They cover: the example Notes API answers a real call (PLAN's "done when"), its data lasts while it runs, one more than the limit stops the least recently used (PLAN's "done when"), a second start reuses the running one, stop ends it and deletes its folder, idle ones are stopped, a broken project and a slow one give plain errors and leave nothing behind, our key is hidden, an unsafe file name is refused, two starts at once stay within the limit, and a crashed API is started again. I broke the code on purpose three times (no limit, key passed through, folder not deleted) and a test failed each time. After a run, no live API process and no `live_` folder were left. Output: `evidence/backend/outputs_f12_live_runner.txt`.

**Not done / limits**
- Nothing calls it yet: F-13 adds `/apis/{id}/...`, `POST /projects/{id}/wake`, `api_url` and `live_status`, and calls `touch` and `stop_idle`.
- **Memory on Render is not measured yet.** On the laptop each live Notes API used **about 50 MB** (3 at once: 50, 50, 50 MB, measured 2026-11-15; on Windows a venv's `python.exe` is a 5 MB launcher that starts the real Python as a child, and `stop` ends both). With the backend's own ~51 MB at rest (D-2 dry run), 3 live APIs should fit in Render's 512 MB, but a build (Gemini calls plus pytest runs) comes on top. Check Render's Metrics tab after F-13 and lower `MAX_RUNNING` if needed.
- `start` holds the lock while it waits for the API to answer (up to 30 s), so a second start waits too. Fine for a demo.
- The generated `requirements.txt` is not installed: the API uses our backend's packages (FastAPI, uvicorn, pydantic), like the test runner. A project needing anything else will not start.
- The free-port trick has a tiny gap: another program could take the port between our check and uvicorn starting.
- It is the same demo sandbox as the test runner (D-007): the code can still read other files on the server and use the network.

**Terms**
| Term | One-line meaning |
|---|---|
| Port | A numbered door on a computer; each server listens on its own one |
| `127.0.0.1` | "This computer": a server listening there can't be reached from outside |
| `subprocess.Popen` | Start a program and carry on, without waiting for it to end (unlike `subprocess.run`) |
| `terminate()` / `kill()` | Ask a program to stop / force it to stop |
| `DEVNULL` | A bin for output nobody needs |
| Lock | Lets only one piece of code at a time do something, so two at once can't get in each other's way |
| Least recently used | The one whose last use was longest ago |

---

# F-13 Live link (Nana took this from Elise, 2026-11-15)

**In one sentence:** a ready project now goes live by itself, and `/apis/{id}/...` passes every call through to it, so a person can open `/apis/p_1/docs` and really use their API with "Try it out". Elise: please read this before the teach-back.

**What changed**
- `run_build` (`backend/projects.py`): when the build is ready, `start_live_api` starts it with the live runner (F-12). `asyncio.to_thread` runs the up-to-30-second wait on the side, so the server keeps answering others. If it can't start, the build is still ready and downloadable; it just shows `sleeping`.
- `GET /projects/{id}`: `api_url` (`/apis/p_1`) and `live_status` (`running` or `sleeping`), only for a ready project.
- `POST /projects/{id}/wake`: start it again from the stored files. `202 {"live_status": "running"}`, `503` with the runner's plain sentence if it can't start, `409` if not ready.
- `ANY /apis/{id}/{path}` (`pass_through`): passes the method, the path, the query, the body and its content type to the live API's port with `httpx`, and sends its status and body back unchanged (its own `404` stays a `404`). Nothing else is passed on: no cookies or other headers of ours. Asleep → `503` "This API is asleep. Wake it up and try again." Over 1 MB → `413` (request) or `502` (answer). No answer in 30 s → `502`. Each call counts as use (`touch`) and puts unused APIs to sleep (`stop_idle`).
- `backend/live.py`: `start(..., root_path="/apis/p_1")` adds `--root-path /apis/p_1`. Without it the API's Swagger page would load **our** `/openapi.json`. With it the page loads `/apis/p_1/openapi.json`, and its `servers` says `/apis/p_1`, so "Try it out" calls go through our link. We pass on the path **without** `/apis/p_1` (tried on a real server first: `/notes` works, `/apis/p_1/notes` is a 404).
- `backend/main.py`: a `lifespan` that stops every live API when our server stops, so none is left running on its own (every `--reload` on a laptop is a stop).
- `docs/api-contract.md`: `wake` stops the least-used API instead of refusing with "too many" (F-12's rule), plus the new `409`, `413` and `502` answers.

**How to check it:** `python -m pytest backend/tests/test_live_link.py -v` (11 passed, real live servers, about 12 s, no AI). They check:
- a finished build starts its live API, under its link;
- calls go through and their data lasts;
- the API's own errors come back unchanged;
- the Swagger page works behind our link (PLAN's "done when");
- a sleeping API says so;
- `wake` starts it, and does nothing new on a running one;
- a broken project gives a plain `503`;
- not ready gives `409`, unknown gives `404`, too big gives `413`;
- stopping our server stops every live API.

I broke the code on purpose twice (full path forwarded; no root path after a build) and tests failed each time. The second one first passed, which showed a gap, so I added a check to the build test. Full suite: 191 passed, with no process or `live_` folder left. Output: `evidence/backend/outputs_f13_live_link.txt`.

**Change, 2026-11-15 (after the first live test on Render):** opening a sleeping API's link now **starts it first** (`start_or_explain`, shared with `wake`), instead of answering 503 "This API is asleep". On Render, a page still showed the link of an API that had gone to sleep after 10 idle minutes, and the person got that message instead of the Swagger page. Tests: `test_opening_a_sleeping_api_wakes_it_by_itself`, `test_a_sleeping_api_that_cannot_start_says_why_plainly` (both failed before the change).

**Not done / limits**
- "Try it out" was checked through the schema's `servers` and real calls, **not clicked in a browser**, and not tried on Render or with a Gemini-built project (no quota today).
- The frontend's Ready screen (F-14, Perfect) must put the **backend's address** in front of `api_url`, because the page is on Vercel.
- Memory with 3 live APIs plus a build on Render is still to be measured (Metrics tab).
- Anyone with the link can call the API and change its data; there are no logins (same as the rest of the demo).
- Everything is in memory: after Render restarts, projects (and so their links) are gone (D-013).

**Terms**
| Term | One-line meaning |
|---|---|
| Pass-through (proxy) | Our server takes a call and sends it on to another server, then hands back the answer |
| Root path | The address prefix a server is shown under (`/apis/p_1`), so its own pages link to the right place |
| `httpx` | The library our server uses to call another server; it was already installed for the tests |
| `asyncio.to_thread` | Run a slow, blocking function on the side, so the server keeps serving others |
| `lifespan` | FastAPI's start-up and shut-down steps |
| `413` / `502` | "Your request is too big" / "the server behind us didn't answer properly" |

---

# Project names (Nana, 2026-11-16)

**In one sentence:** the sidebar and the Build screen now show a short API name, like "Reading Club Library API", instead of the first 40 characters of what the person typed.

**How:** the builder prompt already asks the agent to start with one sentence such as "Building a Reading Club Library API with a books table and 5 endpoints." `api_name()` in `backend/projects.py` reads the name from that sentence: capitalised words ending in "API", after "build" or "building". `add_event` keeps the **first** name it finds, so later sentences can't rename the project. `display_name()` uses it, or falls back to the old cut request, for example for a refusal. There's no extra AI call, so no extra cost or quota.

**How to check it:** `python -m pytest backend/tests/test_project_names.py` (11 tests, written first): 5 real-style sentences give the right names, 3 sentences without a name give none, the first name sticks, and a refusal keeps the typed request. I also ran it on the real first sentences saved in `evidence/` ("Books API", "To-Do List API").

**Limits:** the frontend fetches the list again when the first Thinking step arrives (`listRefreshKey`, see `learnings/frontend.md`), so the name shows within seconds of the build starting. If the AI ever leaves out the name, the old stand-in shows.
