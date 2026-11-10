# Backend

Owner: Elise (S-5 picked up by Perfect, see Handovers in PLAN.md and D-009) · Last updated: 2026-11-09 · Status: partly working (skeleton, sandbox runner, project endpoints)

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
