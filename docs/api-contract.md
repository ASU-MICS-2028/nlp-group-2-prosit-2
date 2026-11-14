# API contract (proposed)

Status: **Proposed**, written by Perfect (frontend) for Elise (backend) to review. Recorded as D-008.
This is what the frontend needs. Elise changes whatever does not fit, then we both build to the agreed version.
Once it is agreed, the FastAPI code must match it, and the TypeScript client is generated from the backend's OpenAPI schema (W-6).

## How the screens use it

| Screen | Needs |
|---|---|
| Sidebar | `GET /projects` |
| Start | `POST /projects` |
| Questions | answers sent with `POST /projects/{id}/answers` |
| Plan | plan comes back from the answers call; `POST /projects/{id}/approve` |
| Building | `GET /projects/{id}/events` (live stream) |
| Ready | `GET /projects/{id}` (live link), the live API at `/apis/{id}/docs`, `GET /projects/{id}/download` (take-home zip) |

## Words used
- **Project**: one API the user asked for. It has an `id` and a `status`.
- **Status**: `waiting` (needs the user) · `working` · `retrying` · `ready` · `failed` · `stopped`. Same words as the status pill in the UI.
- **SSE (Server-Sent Events)**: the server keeps one connection open and pushes lines to the browser as things happen.

## Endpoints

### `GET /health`
Is the server awake? Returns `{ "status": "ok" }`. The frontend calls it first, so it can show "The server is waking up" when it is slow.

### `GET /projects`
List projects, newest first, for the sidebar.
```json
[{ "id": "p_1", "name": "Bookshop API", "status": "ready", "updated_at": "2026-11-02T10:15:00Z" }]
```
Built (W-8, 2026-11-11). Until the plan names a project (F-2), `name` is the start of the request, cut at a word to about 40 characters with "…". `updated_at` is UTC with an offset, for example `2026-11-11T09:30:00.123456+00:00`; it changes when the project is created and on every new event.

### `POST /projects`
Start a project from the plain-English request.
Request: `{ "request": "A bookshop where I can add books..." }` (1 to 2000 characters; the UI enforces the same limit)
Response `201`:
```json
{
  "id": "p_1",
  "status": "waiting",
  "questions": [
    { "id": "q1", "text": "Should each book have a price?",
      "why": "This decides whether we store prices.", "options": ["Yes, with a price", "No, just titles"] }
  ]
}
```
At most 3 questions. If the request is already clear, `questions` is `[]` and the plan is available right away.
Today (W-9, 2026-11-14): there are no questions or approve step yet, so this call **starts the build at once** in the background, with the request as written. F-2 moves the build start behind `POST /projects/{id}/approve`. `GET /projects/{id}` now also returns `name`, `file_count`, `size_kb`, `tests_passed` and `tests_total` (the last four are `null` until the build ends).

### `POST /projects/{id}/answers`
Request: `{ "answers": [{ "question_id": "q1", "answer": "Yes, with a price" }] }`
Response `200`: the plan (below). The answer may be one of the options or free text.

### Plan
```json
{
  "name": "Bookshop API",
  "summary": "Add books, list them, and see which ones are in stock.",
  "endpoints": [{ "method": "GET", "path": "/books", "description": "See all books" }],
  "tables": [{ "name": "books", "fields": "id, title, author, price, in_stock" }],
  "test_count": 5
}
```
`method` is one of `GET POST PUT PATCH DELETE`. This matches the plan card in the UI.

### `POST /projects/{id}/approve`
The user approved the plan. **Nothing is built before this call.** Response `202`: `{ "status": "working" }`. Calling it twice does nothing new (same response).

### `GET /projects/{id}/events` (SSE stream)
One event per change. Each event's data is JSON:
```json
{
  "status": "retrying",
  "attempt": 2,
  "max_attempts": 3,
  "tests": ["pass", "pass", "pass", "pass", "fail"],
  "step": { "kind": "Result", "text": "Test failed: deleting a missing book should return 404.",
            "output": "FAILED test_delete_missing_book", "state": "failed" }
}
```
- `kind`: `Thinking`, `Doing` or `Result`. `state`: `done`, `current` or `failed`.
- `tests` has one entry per test: `pass`, `fail` or `pending`.
- `step` is optional on events that only change status or tests.
- The last event has `status` of `ready`, `failed` or `stopped`, and then the server closes the stream.
- If the browser reconnects, the server sends the history so far, so the timeline is complete.

### `GET /projects/{id}/download`
Returns the generated project as a `.zip` (`application/zip`). Only when the status is `ready`; otherwise `409`.
The ready screen also shows: `file_count`, `size_kb`, `tests_passed`, `tests_total`, `run_command`. These come from `GET /projects/{id}`:
```json
{ "id": "p_1", "name": "Bookshop API", "status": "ready",
  "file_count": 9, "size_kb": 14, "tests_passed": 5, "tests_total": 5,
  "run_command": "docker compose up",
  "api_url": "/apis/p_1", "live_status": "running" }
```
`live_status` is `running` or `sleeping` (see "The live API" below). `api_url` is only present once the status is `ready`.

## The live API (D-011)
After the tests pass, our backend runs the generated project as its own process and passes calls through, so a non-developer can call it from a link.

### `ANY /apis/{id}/{path}`
Everything under `/apis/{id}/` goes to the generated API. For example `/apis/p_1/docs` is that API's own Swagger page, where "Try it out" really calls it, and `/apis/p_1/books` is one of its endpoints. These calls are not part of our OpenAPI schema.
- If the API is `sleeping` (stopped to save memory, or the server restarted), the first call returns `503` with `{ "detail": "This API is asleep. Wake it up and try again." }`.
- Data inside the generated API lasts while it is running and is lost when it restarts.

### `POST /projects/{id}/wake`
Restart a sleeping API from its stored files. Response `202`: `{ "live_status": "running" }` once it answers, or `503` with a plain `detail` if too many APIs are already running. Calling it on a running API does nothing new.

### Optional: `POST /projects/{id}/followup` (D-012, F-15)
Request: `{ "request": "Also add search by title" }`. Starts a new build round on the existing files, then the same events stream applies.

## Errors
- Every error is `{ "detail": "plain-English sentence" }` (FastAPI's default shape), so the UI can show `detail` straight in a notice.
- `400`/`422` bad or too-long input · `404` unknown project · `409` wrong step (for example approving before answers) · `429` the free LLM is rate-limited, try again shortly · `503` the LLM is down.
- Anything unexpected is `500` with a plain `detail`. No stack traces, no secrets.

## Open questions for Elise
0. The live API (D-011) needs her runner to start a project as a long-running process and stop idle ones. Is a limit of 3 running at once about right for a free host?
1. Is `POST /projects` allowed to return the plan directly when no questions are needed (as written), or should it always return questions?
2. Server memory or SQLite for projects between requests? (The sidebar needs them to survive a page reload.)
3. Do you prefer the stream at `/events` (SSE) or a polling endpoint? SSE is written here because it is simpler for the UI and shows live progress.
4. Is `max_attempts` fixed at 3?

### Elise's answers so far (2026-11-09, W-5)
- **2:** Server memory for now (D-013), so projects are lost when the server restarts. A database is an open team question in D-013.
- **3:** SSE at `/events`, as written. It also sends a `: ping` comment every few seconds to keep the line open; the browser ignores it.
- Built so far: `POST /projects` (questions are always `[]` until the agent exists), `GET /projects/{id}` (only `id` and `status` for now; the other fields come when the agent can fill them), `GET /projects/{id}/events`.
- 422 errors are turned into one plain sentence in `detail` (a handler in `backend/main.py`), so every error matches the shape above.
- Questions 0, 1 and 4 are still open.
