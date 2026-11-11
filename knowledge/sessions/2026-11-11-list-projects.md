# 2026-11-11: List projects (W-8)

**Goal:** Give Perfect's sidebar a list of all projects, newest first.

**What we found:** Projects had no time and no name. A real name only comes with F-2's plan.

**What we decided:**
- Store `updated_at` (UTC) on create and on every event; sort latest first.
- Until F-2, `name` is the start of the request, cut at a word to about 40 characters with "…".
- W-8 moved from Perfect to Elise (Handovers in PLAN.md); Perfect reviews.

**What changed:** `backend/projects.py`, 3 tests in `backend/tests/test_projects.py`, contract note, W-8 section in `learnings/backend.md`, PLAN (W-8 ✅, handover row), README table.

**Open questions / next steps:** F-2 sets the real `name`. Pagination is future work. The F-1 PR also records the W-8 handover: whichever merges second may need a one-line PLAN conflict fix.
