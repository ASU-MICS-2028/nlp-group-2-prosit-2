# 2026-11-14: Plain build timeline (F-17)

**Goal:** Make the build timeline readable for non-developers, as Nana suggested ("Thinking… Testing your API… Finalizing your API…").

**What we found:**
- The timeline showed file names ("Writing app/database.py") and the AI's raw final JSON, which mean nothing to the product's users.
- The only thing saying "this step is about files" was the wording of a sentence. If the backend rewords it, the page would break silently, and the live stream is not in the OpenAPI schema, so TypeScript cannot warn us.
- A first version showed "Finalizing your API…" between two tries of a retried build. Running a real event sequence from the backend through the mapping found it; the rule is now that a "finishing" step only counts when nothing follows it.

**What we decided:**
- The backend sends a fixed `phase` with every step; the page reads only that (D-019). A backend test fails if a step has none.
- The page falls back to "Working on your API…" for a step without a phase, and keeps all exact steps under "Show details".
- Perfect took the small backend change from Elise (Handovers row in PLAN.md); Opei, as backup owner, is asked to review.

**What changed:** `backend/builder.py`, `agent/retry.py`, `backend/projects.py`, `frontend/src/build/phases.ts`, `plainSteps.ts`, `realBuildEvents.json`, `BuildTimeline.tsx`, `BuildScreen.tsx`, `events.ts`, `buildState.ts`, tests (8 backend, 21 frontend), contract, D-019, learnings, PLAN (F-17 and a handover row), evidence.

**Open questions / next steps:** Elise to confirm D-019 and the words. One real Gemini build needs a look and a screenshot. Nana should read the wording. The two live tests that W-9 broke are fixed on a separate branch (`chore/sync-status-and-types`, still stashed locally), so they still fail on this one.
