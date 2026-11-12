# 2026-11-12: Chat screen (W-7)

**Goal:** Let a person type a request, see the project start, and watch its live progress, so W-9 (first end-to-end build) can start.

**What we found:**
- `EventSource` cannot be tested for real in jsdom or Node, so we read the stream with `fetch` instead (D-016).
- The server sends `data: {"status":"waiting"}` and a blank line, as the SSE format says. We captured the real bytes before writing the parser.
- The events carry no `attempt` or `tests` yet, so the timeline hides the attempt count and the tests bar instead of inventing numbers.
- Elise's builder reports only `working` steps and a final `ready` or `failed`, and it is not connected to the server until W-9.
- With the backend stopped, all 3 live page tests fail, so they test something real. Two test mistakes of ours showed up and were fixed: a time rounded up when the code rounds down, and a test that expected one sidebar row when other tests had made several.

**What we decided:**
- Read the stream with `fetch`, no auto-reconnect; "Open this project again" replays the history (D-016).
- Start screen, timeline, and sidebar are three small hooks and screens: `useBuild`, `useProjectList`, `StartScreen`, `BuildScreen`.
- Tests without a server point at a port where nothing listens (a real refusal); tests with a server run only with `VITE_LIVE_API=1`.

**What changed:** `src/api/events.ts`, `streamEvents` and `errorMessage` in `src/api/client.ts`, `src/build/` (`buildState.ts`, `sidebar.ts`), `src/hooks/`, `src/screens/`, `src/App.tsx`, optional attempt and tests in `BuildTimeline`, tests, `evidence/frontend/outputs_w7_live.txt`, D-016, learnings, PLAN (W-7 done, W-9 ready), README.

**Open questions / next steps:** Elise connects the builder in W-9 and decides how a build starts (there is no approve endpoint yet). Hide the AI's final JSON reply, which shows as a raw "Thinking" step. F-3 (plan screen) waits on F-2.
