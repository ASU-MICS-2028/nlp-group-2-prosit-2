# Frontend

Owner: Perfect · Last updated: 2026-11-12 · Status: partly working (skeleton, design components, typed API client and the chat screen done; questions, plan, approve and Ready screens not connected)

## 1. In one sentence
A React + TypeScript web page where a non-developer types what API they want; it is built from small reusable pieces styled by one set of design tokens.

## 2. What I did, step by step
1. Created the project with Vite (the tool that runs and bundles the page), React and TypeScript in `strict` mode.
2. Added checks: oxlint (finds likely mistakes), Prettier (one code style), `tsc` (type check), Vitest (tests).
3. Put every colour, size and radius in `src/styles/tokens.css` from `knowledge/DESIGN-SYSTEM.md`, and component styles in `components.css`.
4. Built 13 small components in `src/components/` (Button, Chip, StatusPill, MethodBadge, IconTile, Notice, RequestCard, QuestionCard, PlanCard, BuildTimeline, ReadyCard, Sidebar, AppShell).
5. Built `/dev/gallery` (only while developing) to see every component in each state.
6. Built the Start screen (`src/App.tsx`): question, request card, example chips.

## 3. Why we did it this way
- **TypeScript strict**: the compiler catches mistakes before a user does.
- **Plain CSS with tokens, no styling library**: fewer tools to learn; changing one token changes the whole look.
- **Small components, one job each**: easy to test and to explain.
- **oxlint instead of ESLint**: ships with the Vite template and needs no setup (D-004).
- **Fonts and icons installed from npm, not a CDN**: works offline and no outside request (design rule).
- **Start screen does not fake a result**: planning is not connected yet, so it says so.

## 4. How to check it works
```
cd frontend
npm ci
npm run lint        # no output of problems
npm run typecheck   # no errors
npm test -- --run   # 13 passed
npm run build       # built in under a second
npm run dev         # open http://localhost:5173 (or the port it prints)
```
Open `/dev/gallery` on the dev server to see all components.

## 5. What is NOT done or is faked
- Nothing talks to the backend yet. The "Plan my API" button only shows a notice.
- Sidebar project list is always empty (needs `GET /projects`, task W-8).
- Questions, Plan, Building and Ready screens exist as components but are not wired into screens yet.
- The typed API client (generated from the backend's OpenAPI schema) is not generated yet (W-6).
- The glow, sheen and haze strengths were chosen by eye from a reference image; I have not checked contrast on the rendered page or done the keyboard-only walkthrough.

## 6. What will bite us
- `typescript` 7 and `vite` 8 are very new; if a tool complains about versions, check the lock file first.
- Tests need `afterEach(cleanup)` (in `src/test/setup.ts`); without it, tests see each other's leftovers.
- The haze must stay sized in pixels; percentages disappear on tall pages.
- The free-tier backend may be asleep; screens need a "waking up" notice (a Notice component exists).

## 7. Terms used
| Term | One-line meaning |
|---|---|
| Vite | Tool that runs the page while developing and bundles it for release |
| React component | A small function that returns a piece of the page |
| TypeScript strict | JavaScript with types, with the compiler's strictest checks on |
| Design token | A named value (like `--accent`) so styles stay consistent |
| oxlint / Prettier | A mistake finder / an automatic code formatter |
| Vitest | The test runner |
| jsdom | A pretend browser used by tests |
| ARIA role | A hint that lets screen readers understand what an element is |

## 8. Lines ready for the report
- The frontend is a separate React + TypeScript app that talks to the backend only through its API.
- Visual style comes from one token file, so the look can change in one place.
- Components are tested for the behaviour that matters (disabled while loading, input limits, keyboard send, accessibility roles).

---

# W-6 Typed API client (Perfect, 2026-11-12)

## 1. In one sentence
`frontend/src/api/` lets the web page call the backend through TypeScript types that are generated from the backend's own description of itself, and turns every failure into one plain sentence a user can read.

## 2. What I did, step by step
1. `frontend/scripts/export_openapi.py` asks the backend app to describe itself (its OpenAPI schema) and saves it as `src/api/openapi.json`. The server does not need to be running.
2. `openapi-typescript` turns that file into `src/api/schema.ts`: one TypeScript type per answer the backend can give (for example `ProjectSummary`).
3. `npm run api:generate` does both steps. Run it again whenever the backend changes a shape.
4. `src/api/client.ts` has one function per endpoint: `getHealth`, `listProjects`, `startProject`, `getProject`, plus `eventsUrl` (the address of the live stream). They all go through one `request` function.
5. `request` always ends in an `ApiError` with a sentence we can show as it is: the backend's own `detail` sentence when it sent one, a generic sentence for anything odd (such as an error page from the host), "could not reach the server" when the network is down, and "taking too long" after 30 seconds (the free server may be asleep).
6. `src/api/client.live.test.ts`: 9 tests that call a real backend. The generated files are listed in `.prettierignore` so CI's style check does not fail on them.

## 3. Why we did it this way
- **Generated types (D-001, D-015):** if Elise changes a response, TypeScript points at every line in the UI that no longer fits, instead of the user finding out.
- **`npx` instead of installing the tool:** the tool needs TypeScript 5, we use 7. Installing it makes npm refuse, and forcing it would hide a real conflict (see D-015).
- **One `request` function:** the error rules live in one place, so every screen shows the same kind of message.
- **The backend's sentence is used as it is:** the backend already turns validation errors into plain English (`backend/main.py`), so the UI does not translate anything.
- **Live tests, not a fake server:** a fake can agree with our mistakes. The tests start nothing themselves, so they only run when you set `VITE_LIVE_API=1`; CI skips them.

## 4. How to check it works
Terminal 1, repo root:
```
source backend/.venv/bin/activate
uvicorn backend.main:app
```
Terminal 2:
```
cd frontend
VITE_LIVE_API=1 npm test -- --run client.live      # 9 passed (Windows PowerShell: $env:VITE_LIVE_API=1; npm test -- --run client.live)
npm test -- --run                                  # 13 passed, 9 skipped (the live ones)
npm run typecheck && npm run lint && npm run format:check
npm run api:generate                               # needs the venv on and internet; then `git diff` shows what changed
```
Saved output: `evidence/frontend/outputs_w6_client_live.txt`. I also ran the live tests with the backend stopped: 8 of 9 failed, as they should. The one that passes is the "nothing is listening" test, which does not need a server.

## 5. What is NOT done or is faked
- **The 30-second timeout is not tested.** A real test would wait 30 seconds, and I chose not to fake it. The code is short, but it has never run.
- **Nothing in the UI uses the client yet.** That is W-7.
- **The types are thinner than `docs/api-contract.md`.** `GET /projects/{id}` still gives only `id` and `status`, and `questions` is always `[]`. There are no answers, approve, download or wake endpoints yet (F-2, F-5, F-13), so the client has no functions for them.
- **The live stream is not in the client.** `EventSource` (the browser's way to read a stream) needs a hook; that comes in W-7. `eventsUrl` only builds the address.
- **No test for a slow response or a double click on submit.** Those belong to the screen (W-7, F-8).

## 6. What will bite us
- Forgetting `npm run api:generate` after a backend change leaves old types. Run it after every pull that touches `backend/`.
- `api:generate` calls `python`. If your terminal shows `command not found`, switch the venv on first.
- Do not edit `schema.ts` or `openapi.json` by hand; the next run overwrites them.
- Live tests share one backend's memory: they create projects, and a restart empties them.

## 7. Terms used
| Term | One-line meaning |
|---|---|
| OpenAPI schema | A machine-readable description of every endpoint and data shape the backend has |
| Generated code | Code written by a tool from another file, so it is never edited by hand |
| `npx` | Runs a tool from npm without adding it to our dependencies |
| Peer-dependency conflict | A tool says "I only work with TypeScript 5" while the project uses 7 |
| AbortController | A switch that cancels a request that is still waiting |
| Timeout | A time limit after which we stop waiting |
| Live test | A test that talks to a real running server, not a pretend one |
| `ApiError` | Our own error type: its message is always a sentence for a person |

## 8. Lines ready for the report
- The frontend's API types are generated from the backend's OpenAPI schema, so a backend change that breaks the UI shows up as a build error.
- Every failure (validation, not found, offline, slow, a broken answer) reaches the user as one plain sentence.
- The client is tested against a real running backend, including a refused connection, not against a simulated one.

---

# W-7 Chat screen (Perfect, 2026-11-12)

## 1. In one sentence
The Start screen now really talks to the backend: it sends the request, follows the project's live progress on a timeline, and keeps the sidebar's project list up to date.

## 2. What I did, step by step
1. `src/api/events.ts`: `splitMessages` cuts the live stream's text into finished messages, and `parseEvent` turns one message into an event. A message it cannot read gives `null`, so one odd message never breaks the timeline. Both are plain functions with no network.
2. `src/build/buildState.ts`: `applyEvent` takes the current state and one event and gives the new state (status, steps, tests, attempt). Unknown words are handled (an unknown status shows as "working"; an unknown step kind is skipped).
3. `src/build/sidebar.ts`: turns the API's project row into the sidebar's row, with "just now" / "5 min ago" / "3 h ago" instead of a raw time.
4. `streamEvents` in `src/api/client.ts` opens the stream with `fetch` and reads it piece by piece (D-016).
5. `src/hooks/useBuild.ts`: `start(text)` creates the project and then watches it; `open(id)` watches an existing one; `reset()` goes back to the Start screen.
6. `src/hooks/useProjectList.ts`: loads the sidebar list, and loads it again when the open project or its status changes.
7. `src/screens/StartScreen.tsx` and `BuildScreen.tsx`, put together in `src/App.tsx`. `BuildTimeline` now hides the attempt count and tests bar when the server has not sent them.

## 3. Why we did it this way
- **Pure functions for the rules:** reading messages, changing the state, and formatting times need no server and no screen, so they are tested directly and are easy to explain.
- **`fetch` instead of `EventSource` (D-016):** `EventSource` cannot be tested for real in our test setup, and it reconnects forever by itself, even after the server hangs up on purpose.
- **Nothing invented:** the events do not carry the attempt number or the test list yet. The screen shows only what the server said.
- **A double click makes one project:** `useBuild` ignores a second `start` while the first is still running.
- **The page going away stops the stream:** when you leave, the stream is cancelled, and a late answer is ignored.
- **Picking an old project replays its history:** the server sends everything that happened, then new events, so the timeline is always complete.
- **Every state has words:** starting (with a note that a sleeping server can take half a minute), waiting to start, ready, failed or stopped (with the last reason), live connection lost (with a button), and sidebar could not load.

## 4. How to check it works
```
cd frontend
npm test -- --run          # 48 passed, 15 skipped (the live ones)
npm run typecheck && npm run lint && npm run format:check && npm run build
```
With a real backend (Terminal 1, repo root: `source backend/.venv/bin/activate && uvicorn backend.main:app`):
```
cd frontend
VITE_LIVE_API=1 npm test -- --run client.live App.live      # 15 passed
npm run dev        # open the address it prints; type a request and press "Plan my API"
```
Saved output: `evidence/frontend/outputs_w7_live.txt`. With the backend stopped, the 3 page tests fail, as they should. The tests in `App.test.tsx` point at a port where nothing listens, so the connection really is refused, and they need no server.

## 5. What is NOT done or is faked
- **A real build does not show yet.** Elise's builder is not connected to the server until W-9, so a project stays on `waiting`. The timeline, steps, retries and the tests bar are tested with the exact event shapes from the contract, but not with a real build.
- **"The server hangs up after `ready`" is not tested against a real server.** Nothing can send a final event until W-9. The code path exists and its pure parts are tested.
- **No questions, plan, approve, Ready or download screens.** They need Elise's F-2, F-5 and F-13.
- **Not tested:** a slow server (the 30-second limit), a stream that drops in the middle, and a keyboard-only walk through the sidebar. I did not look at the page in a browser or take a screenshot. Please open it once and look.
- **The AI's final JSON reply** will show as a raw "Thinking" step once builds run (Elise noted this for W-9).
- **A project is only in the sidebar while the backend runs** (D-013: memory only).

## 6. What will bite us
- The live tests share one backend, so rows from earlier runs stay in the sidebar until it restarts.
- `localhost:8000` must be where the backend runs, or set `VITE_API_URL` in `frontend/.env.local`.
- If a stream is open and you close the tab, the server notices on its next check, so wait a moment before stopping it.
- Changing `BuildTimeline` props touches `src/dev/Gallery.tsx` too: it must keep compiling.

## 7. Terms used
| Term | One-line meaning |
|---|---|
| Hook | A function (name starts with `use`) that gives a screen state and actions; ours call the backend |
| State | The values a screen remembers, such as "which project is open" |
| Ref (`useRef`) | A box that keeps a value between renders without causing a new render |
| `useEffect` | Code that runs when the page appears or a value changes; its returned function cleans up |
| SSE (Server-Sent Events) | The server keeps one connection open and writes a message each time something happens |
| Abort | Cancelling a request or stream that is still running |
| Pure function | A function that only uses its inputs and has no side effects, so it is easy to test |
| Replay | The server sends the whole history first, so a late visitor sees the full timeline |

## 8. Lines ready for the report
- The UI follows a build live through Server-Sent Events, and every state (starting, waiting, ready, failed, connection lost) has a plain-English message.
- The rules for reading events and updating the timeline are plain functions, tested on their own; the page is tested against a real running backend, not a simulation.
- The timeline shows only what the server reported: when attempt counts are not available, it shows none.
