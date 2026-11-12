# 2026-11-10: Agent loop (W-3), and review fixes for W-5 and F-11

**Goal:** Build the agent loop: run the AI with its tools, report each step, stop with a clear reason, and check the result ourselves.

**What we found:**
- ADK accepts any model object, so a scripted `FakeModel` lets us test the loop without Gemini.
- Without a catch, a Gemini 503 crashes the build and no final status reaches the live stream.
- ADK's `RunConfig(max_llm_calls=...)` raises `LlmCallsLimitExceededError` at the limit.
- With `LLM_MODEL` empty, ADK silently falls back to its own default model.
- Reviews: W-5 had two duplicated tests (8 of 10 ran), accepted spaces-only requests, and gave "Invalid 24" for broken JSON; F-11 failed on Windows without `SYSTEMROOT` and dropped stderr. All fixed, both PRs merged.

**What we decided:**
- Five stop rules: 3 test runs, no files written, AI service error, 40 AI calls, 5 minutes. Each ends `failed` with a plain reason.
- Retrying and re-prompting belong to F-4, built on `backend/builder.py` rather than a second loop.
- No new ADR; this follows D-010.

**What changed:** `backend/builder.py`, `backend/tests/test_builder.py` (7 tests), `google-adk==2.13.0` pinned,
`evidence/backend/w3_live_check.py` and outputs, W-3 section in `learnings/backend.md`, PLAN (W-3 ✅, F-1 🟢), README table.

**Open questions / next steps:**
- W-9 (end-to-end) waits on Perfect's W-7 chat screen; it connects `build_project` to the server with `add_event`.
- Hide or parse the AI's final ```json reply in the timeline (W-9).
- Elise next: F-1 clarifying-questions prompt, F-12 live runner.
