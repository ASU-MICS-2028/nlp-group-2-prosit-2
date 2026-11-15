# 2026-11-15: Download button (F-7) and clean-up

**Goal:** Use Nana's zip endpoint (F-5) so a person can take their finished project home, and clear what was left from the last days.

**What we found:**
- The live tests that W-9 broke were still failing, and two more were fragile: since W-9 a build starts at once, so "Waiting to start" can disappear before a test looks for it, and repeated runs leave several projects with the same name.
- The generated API types were stale (2 fields instead of 7 on the project answer).

**What we decided:**
- Use `fetch` for the download (not a link), so failures show a plain sentence.
- Live tests no longer depend on the project's status or on a name being unique.
- The success path runs only against a project that is really ready (`VITE_LIVE_READY_ID`).

**What changed:** `src/api/client.ts` (`send`, `downloadProject`), `src/build/saveFile.ts`, `src/hooks/useDownload.ts`, `BuildScreen.tsx`, `App.tsx`, regenerated `schema.ts` and `openapi.json`, 9 new tests, the 3 live tests, deadline moved to 15 Nov in README, PLAN, AGENTS and knowledge, README stage text, PLAN F-16 and F-7, `learnings/frontend.md`, evidence.

**Open questions / next steps:** Click the button in a real browser and do the keyboard walkthrough, then flip F-7 to done. F-3 and F-14 are still waiting on F-2 and F-13.
