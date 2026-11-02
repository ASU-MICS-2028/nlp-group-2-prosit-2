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
| Ready | `GET /projects/{id}/download` |

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
  "run_command": "docker compose up" }
```

## Errors
- Every error is `{ "detail": "plain-English sentence" }` (FastAPI's default shape), so the UI can show `detail` straight in a notice.
- `400`/`422` bad or too-long input · `404` unknown project · `409` wrong step (for example approving before answers) · `429` the free LLM is rate-limited, try again shortly · `503` the LLM is down.
- Anything unexpected is `500` with a plain `detail`. No stack traces, no secrets.

## Open questions for Elise
1. Is `POST /projects` allowed to return the plan directly when no questions are needed (as written), or should it always return questions?
2. Server memory or SQLite for projects between requests? (The sidebar needs them to survive a page reload.)
3. Do you prefer the stream at `/events` (SSE) or a polling endpoint? SSE is written here because it is simpler for the UI and shows live progress.
4. Is `max_attempts` fixed at 3?
