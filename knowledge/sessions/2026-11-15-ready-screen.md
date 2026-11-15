# 2026-11-15: Ready screen (F-14)

**Goal:** Show a finished project's live link, its Swagger page and a "Wake it up" button (Nana asked for F-14 once F-13 was on `main`).

**What we found:**
- F-13 gives `api_url`, `live_status` and `POST /projects/{id}/wake`, so the page only needs to read and call them.
- The download test I wrote earlier broke: the Ready screen now also asks for the project's details, so with the server down there are two failure sentences, not one.
- A lint rule rejected setting state inside an effect; `loading` is now worked out from the data instead.

**What we decided:**
- A view that only draws its props, and one hook that loads and wakes. No new decision record (no change of approach).
- A longer time limit (45 s) for waking, because the server may take 30 s.
- The wake test runs only against a really ready project (`VITE_LIVE_READY_ID`).

**What changed:** `src/api/client.ts`, `src/hooks/useReadyProject.ts`, `src/screens/ReadyDetails.tsx`, `src/build/readyFacts.ts`, `BuildScreen.tsx`, `components.css`, regenerated types, 11 new tests, README and PLAN rows, `learnings/frontend.md`, evidence.

**Later:** Perfect clicked it through in a real browser (everything worked; screenshot in `evidence/live/`). It showed "0 of 0 tests passed" for the seeded project, so the facts line now leaves tests out when the total is 0.

**Open questions / next steps:** The keyboard-only walkthrough, then flip F-14 and F-7 to done. Not tried on Render.
