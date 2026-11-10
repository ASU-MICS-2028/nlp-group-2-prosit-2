# 2026-11-06 to 2026-11-09: Project endpoints (W-5)

**Goal:** Build the first real endpoints so the web page can start a project, check it, and watch it live.

**What we found:**
- PR #3 (runner) was merged before its review fixes; the fixes went to a second PR (F-11), still waiting for review.
- FastAPI 0.162 has Server-Sent Events built in (`fastapi.sse`), with automatic `: ping` keep-alive lines.
- Raising a 404 inside a streaming function is too late: the client gets an empty `200`. A dependency (`Depends`) runs the check first.
- FastAPI's default 422 body is a technical list, which broke the contract's "one plain sentence" rule.
- Swagger's "Try it out" can't show a stream; curl with `-N` can.

**What we decided:**
- D-013 (Proposed): projects in server memory for now; database (hosted Postgres, Firestore, or Postgres in Docker) is an open team question.
- 422 errors are converted to one plain sentence in `backend/main.py`.
- Contract questions 2 and 3 answered in `docs/api-contract.md` (memory for now; SSE at `/events`).

**What changed:** `backend/projects.py` (new), `backend/main.py` (router + 422 handler), `backend/tests/test_projects.py` (8 tests),
`evidence/backend/outputs_w5_*.txt`, W-5 section in `learnings/backend.md`, D-013, PLAN (W-5 ✅, W-6 🟢), README table, API contract answers.

**Open questions / next steps:**
- Team to decide D-013 (database); Elise wants a short Docker lesson if Postgres is chosen.
- Someone to review and merge the F-11 runner PR.
- Next for Elise: W-3 agent loop (unblocked); then F-12 live runner.
- When the F-11 PR and this PR both merge, `learnings/backend.md` will likely conflict (both add a section at the end): keep both sections.
