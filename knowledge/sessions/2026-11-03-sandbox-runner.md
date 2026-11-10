# 2026-11-03: Sandbox runner (W-2)

**Goal:** Build the sandbox runner: run an AI-written project's tests safely and report pass or fail.

**What we found:**
- Without limits, AI-written code could loop forever, write files outside its folder (`../`), or read our API key from the environment. Each one was shown by a failing test before it was fixed.
- Plain `pytest` on a Mac with Anaconda can run the wrong Python. `python -m pytest` avoids this.

**What we decided:**
- Problems (unsafe name, too big, timeout) are returned as a result with a message, not raised as errors, so the AI can read the message and fix its files.
- pytest gets only `PATH` from our environment (a "keep only these" list), so new secrets are left out automatically.
- Limits: 200,000 characters of input, last 20,000 characters of output, 30-second default timeout.
- No new ADR; this follows D-007.

**What changed:** `backend/runner.py`, `backend/tests/test_runner.py` (8 tests), `evidence/backend/outputs_w2_runner_tests_run2.txt`,
a W-2 section and F-11 checklist in `learnings/backend.md`, PLAN.md (W-2 ✅, F-11 🔄), README table.

**Open questions / next steps:**
- Elise to reply to Perfect: take W-5 (endpoints, ready now) and/or W-3 (agent loop, waits on W-1).
- F-11 still open: no test that the temp folder is deleted; no server logging yet to check for secrets.
- CI uses Python 3.12 (marked ❓ confirm with Elise); Elise uses 3.14 locally. The runner works on both.
