# Backend

Owner: Elise (S-5 picked up by Perfect, see Handovers in PLAN.md and D-009) · Last updated: 2026-11-03 · Status: partly working (skeleton + sandbox runner)

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

## 5. What is NOT done or is faked
- Only `/health` exists. The real endpoints (projects, answers, approve, events, download) are task W-5 and are described in `docs/api-contract.md`, which Elise has not reviewed yet.
- No agent loop (W-3), no storage. The sandbox runner (W-2) is done: see the W-2 section below.
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
9. After review: we keep only the last 20,000 characters of pytest's output.

## 3. Why we did it this way
- **Separate program + time limit**: AI-written code can't be trusted. If it crashes or loops forever, our server keeps working (D-007).
- **Only PATH is passed on**: a "keep only these" list is safer than a "remove these" list. A new secret added later is left out automatically.
- **Keep the last part of the output**: pytest's summary (what failed and why) is at the end, and the AI will read this to fix its code.
- **Problems are reported, not raised as errors**: the agent loop (W-3) can show the message to the AI so it can fix its files.

## 4. How to check it works
From the repo root, with the venv active:
```
python -m pytest -v backend/tests/test_runner.py    # 8 passed
```
Saved output: `evidence/backend/outputs_w2_runner_tests_run2.txt` (local folder path replaced with `<repo>`).

## 5. What is NOT done or is faked
- This is a **demo sandbox**, not real isolation. AI-written code can still read other files on the computer and use the network (D-007). The report must say so.
- No automated test checks that the throwaway folder is really deleted. We rely on Python's `TemporaryDirectory`.
- Nothing calls the runner yet except tests. The agent loop (W-3) will.

## 6. What will bite us
- If generated code needs another environment variable to work (for example `HOME`), it won't have it. Add only what is needed, never keys.
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
| Temporary folder is deleted | not tested automatically (Python's `TemporaryDirectory` does it) | ⚠️ not tested |
| No secrets in the server's logs | the server has no logging yet | ⬜ not done |
| AI code can't read other files | not possible without containers (D-007) | ⚠️ known limit |

## 9. Lines ready for the report
- Generated code runs in a temporary folder as a separate process, with a time limit, input and output size limits, and no access to our API keys.
- It is a demo sandbox, not production isolation: generated code can still read other files and use the network.
