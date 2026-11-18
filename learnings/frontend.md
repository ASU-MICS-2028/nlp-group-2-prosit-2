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

---

# F-17 Plain build timeline (Perfect, 2026-11-14)

## 1. In one sentence
The timeline now tells a non-developer what is happening in plain words ("Putting your plan into action…", "Testing your API…", "Finalizing your API…") and keeps every exact step folded under "Show details".

## 2. What I did, step by step
1. A teammate (Nana) pointed out that lines like "Writing app/database.py" mean nothing to someone who cannot code.
2. The backend now sends a fixed `phase` with every step: `planning`, `writing`, `testing`, `fixing` or `finishing` (D-019, `backend/builder.py`). The page reads only this word, never the sentence.
3. `src/build/phases.ts` holds the list. `src/build/plainSteps.ts` (`toPlainSteps`) turns the steps into short lines: file steps join into one line, each test run is its own line, a file problem gets its own red line, and a "finishing" step only counts if nothing comes after it (so a failed try does not say "Finalizing" in the middle of a build).
4. `BuildTimeline` has a new optional `details` list, shown in a native `<details>` element ("Show details"), closed by default.
5. `BuildScreen` passes the plain lines as the main list and the raw steps as the details.

## 3. Why we did it this way
- **A fixed `phase`, not the sentence:** the page cannot read a changed sentence by mistake. The live stream is not in the OpenAPI schema, so TypeScript cannot warn us about it. A backend test now fails if a step has no `phase`.
- **A safe fallback:** a step with no phase (an older server) becomes "Working on your API…", and its text is still in the details. It never shows blank or wrong.
- **The detail is folded away, not deleted:** useful for debugging, and for showing the real steps in the demo or viva.
- **The AI's own opening sentence is kept:** "Building a Bookshop API with 4 endpoints." is already plain.
- **Native `<details>`:** it works with the keyboard and needs no code of ours.

## 4. How to check it works
```
cd frontend
npm test -- --run plainSteps BuildScreen        # the plain lines and the folded details
npm test -- --run                               # 69 passed, 15 skipped (live ones)
npm run typecheck && npm run lint && npm run format:check
```
`src/build/realBuildEvents.json` is a real event sequence made by running the backend's retry loop with the pretend AI (three tries, a fix, then success). To make it again, from the repo root with the backend venv on:
```
python - <<'PY'
import asyncio, json
from agent.retry import build_with_retries
from agent.tests.test_retry import FakeModel, call, say, SEEDED_PROJECT, FIXED_APP
model = FakeModel(model="fake", replies=[call("run_tests"), call("run_tests"), call("run_tests"),
    say("The add function subtracts. I will change - to +."),
    call("write_file", path="calc.py", content=FIXED_APP), call("run_tests"), say("Done.")])
events = []
asyncio.run(build_with_retries("Build the calculator.", "You are a builder.", model, events.append, dict(SEEDED_PROJECT)))
json.dump(events, open("frontend/src/build/realBuildEvents.json", "w"), indent=2)
PY
```
Saved: `evidence/frontend/outputs_f17_tests.txt`.

## 5. What is NOT done or is faked
- **I have not seen a real Gemini build with the new timeline.** The tests use a real event sequence from the backend's own loop with a pretend AI. Please run one real build and look at it, then save a screenshot.
- **The wording is mine plus Nana's ideas.** Nana should read it.
- **The page does not show how many files were written** or how far along the build is. That would need a total from the server.
- **Two lists of phases must stay in step:** `PHASES` in `backend/builder.py` and `phases.ts`. An unknown phase is dropped by the page and becomes "Working on your API…".
- **"Finalizing your API…" can appear for a moment** between a failed try and the next one, until the "Fixing…" line arrives.

## 6. What will bite us
- Adding a new kind of step in the backend without a `phase` fails a backend test. That is on purpose.
- If you change a phase word, change `docs/api-contract.md`, `backend/builder.py` and `phases.ts` together.

## 6b. Changing words while waiting (D-020, Elise's idea)
- Each phase has a few wordings in `WORDS` (`plainSteps.ts`). The first one is the fixed one.
- `useTick(running)` (`src/hooks/useTick.ts`) counts up every 4 seconds while the build is going. `BuildScreen` passes it to `toPlainSteps(steps, status, tick)`.
- Only the newest line (the one happening now) uses `WORDS[phase][tick % length]`. `%` wraps the number back to the start of the list. Finished lines, the plan sentence and test results never change.
- Tests: `plainSteps.test.ts` ("changing words while waiting", 5 tests) and `useTick.test.ts` (4 tests, with fake timers: they fake only the clock, no data). Saved: `evidence/frontend/outputs_f17_wording_tests.txt` (78 passed, 15 skipped). I made the rotation return the first wording on purpose and one test failed, then I restored it.
- Not done: nobody has watched it on a real build yet; Nana should read the wordings. Changing the timer length is one number (`everyMs`).

## 7. Terms used
| Term | One-line meaning |
|---|---|
| Tick | A number that goes up on a timer; the page uses it to pick the next wording |
| Phase | A fixed word saying what a step is about (planning, writing, testing, fixing, finishing) |
| Plain steps | The short, non-technical lines shown by default |
| Details | The exact steps, folded away under "Show details" |
| Fixture | A saved piece of real data a test reads (`realBuildEvents.json`) |
| Fallback | What the page does when data is missing, so nothing breaks |

## 8. Lines ready for the report
- The build timeline speaks plain language to non-developers and keeps the exact steps one click away.
- Every step carries a fixed `phase`, enforced by a backend test, so the page never depends on the wording of a sentence.

# F-7 Download button (Perfect, 2026-11-15)

## 1. In one sentence
When a project is ready, the page shows a "Download your project (.zip)" button that saves the finished project, and says in plain words if it cannot.

## 2. What I did, step by step
1. `downloadProject(id)` in `src/api/client.ts` asks `GET /projects/{id}/download` (F-5, by Nana). I split the old `request` into `send` (the request, the 30 s timer and the plain error sentences) and `request` (reads JSON), so the download uses exactly the same error handling.
2. `src/build/saveFile.ts` makes the browser save the bytes: a temporary address for the file, a hidden link with a `download` name, one click, then the address is freed.
3. `src/hooks/useDownload.ts` holds the states: idle, loading, error sentence. A second click while loading does nothing, and a screen that was closed is not updated.
4. `BuildScreen` shows the button inside the green "passed its tests" notice, only when the status is `ready`. The button is the existing `Button` (a real `<button>`, so Tab and Enter work).
5. I regenerated the API types (`npm run api:generate`): they were stale (the project answer had 2 fields in the types and 7 on the server) and now include the download endpoint.

## 3. Why we did it this way
- **`fetch` and not a plain link:** with a link, a failure (server asleep, project gone) opens a page of raw JSON. With `fetch` we show a sentence and keep the button.
- **Only for `ready`:** the server refuses anything else with 409; the button is simply not shown, so a person never sees that error.
- **The file name is `<project id>.zip`:** the same name the server suggests.

## 4. How to check it works
```
cd frontend
npm test -- --run                     # 84 passed, 18 skipped (live ones)
```
Live tests need a real backend, started on your own port (never kill other servers by name). With the keys unset, builds fail at once and cost no Gemini quota:
```
env -u GEMINI_API_KEY -u LLM_MODEL uvicorn backend.main:app --port 8001      # repo root, backend venv on
VITE_LIVE_API=1 VITE_API_URL=http://localhost:8001 npm test -- --run live    # frontend/
```
The success case needs a project that is really ready, and a normal server has none without a real build. So that test only runs when you give it one: `VITE_LIVE_READY_ID=p_ready`. I started the real backend app with one project put into the "ready" state in code (the same way `backend/tests/test_download.py` does) and the real zip came back. Saved: `evidence/frontend/outputs_f7_download.txt`.

## 5. What is NOT done or is faked
- **I have not clicked the button in a real browser** and not done the keyboard-only walkthrough (PLAN F-7 stays 🔄 until someone does).
- **The success path is tested against a seeded project,** not a project built by Gemini.
- **A double click is protected by code but not tested:** counting the requests would need a fake server.
- **Not built:** F-3 (plan screen), F-14 (the live link and "Wake it up").

## 6. What will bite us
- Projects live in the server's memory (D-013): after a restart or sleep, the project is gone and the download says "Project not found."
- Live tests share one server, so projects from earlier runs stay in the list. The tests look for the newest match and do not check the status.

## 7. Terms used
| Term | One-line meaning |
|---|---|
| Blob | The bytes of a file, held in the browser's memory |
| Zip | One file that packs many files together |
| 409 | "Not at this step yet": the project is not ready |

## 8. Lines ready for the report
- When a build is ready, the person can download the whole project as a zip with one button; failures are shown as plain sentences.

# F-14 Ready screen (Perfect, 2026-11-15)

## 1. In one sentence
When a project is ready, the screen shows its facts (files, size, tests), a link that opens the live API's own Swagger page, a "Wake it up" button when the live API is asleep, and the zip download.

## 2. What I did, step by step
1. Regenerated the API types (`npm run api:generate`), so `api_url`, `live_status` and the wake endpoint are typed.
2. `wakeProject` in `src/api/client.ts` calls `POST /projects/{id}/wake` with a longer time limit (45 s), because waking can take up to 30 s on the server. `liveDocsUrl` builds the Swagger address.
3. `src/hooks/useReadyProject.ts` loads `GET /projects/{id}` once the project is ready, can load it again, and can wake the API. After a wake it reads the project again, so the screen shows what the server says and not a guess.
4. `src/screens/ReadyDetails.tsx` only draws what it is given: loading, error with "Try again", the facts, the live link when `running`, "Wake it up" when not, the wake error, and an empty sentence when the project has no live link. `src/build/readyFacts.ts` writes the facts line and leaves out anything the server did not send.
5. `BuildScreen` shows it inside the green notice, above the download button.

## 3. Why we did it this way
- **A view that gets everything as props:** every state can be tested without a server, and the loading and waking live in one hook.
- **A real link with `target="_blank"` and `rel="noopener noreferrer"`:** the Swagger page is the generated API's own, served by our backend. `noopener` stops the new tab from reaching back into ours.
- **The sleeping state shows "Wake it up" and no link:** the link would only show a 503.
- **The wake button blocks a second click** (a ref, as in the download hook), because a wake takes seconds.

## 4. How to check it works
```
cd frontend
npm test -- --run                       # 97 passed, 21 skipped (live ones)
```
Live tests need a real backend on your own port. The wake test also needs a really ready project, so start the real backend app with one put into the "ready" state in code (the same way `backend/tests/test_download.py` does), then:
```
VITE_LIVE_API=1 VITE_API_URL=http://localhost:8001 VITE_LIVE_READY_ID=p_ready npm test -- --run live
```
That test wakes a real generated API (a child process of the server) and fetches its Swagger page through `/apis/p_ready/docs`. Stopping the server also stops that child: I checked that nothing was left. Saved: `evidence/frontend/outputs_f14_ready_screen.txt`.

## 5. What is NOT done or is faked
- **Clicked in a real browser on 2026-11-15** (Perfect): the facts, the live link, the Swagger page and the download all worked; screenshot `evidence/live/f14_ready_screen.png`. **The keyboard-only walkthrough is not confirmed yet**, so PLAN F-14 and F-7 stay 🔄.
- **The live API tested is the builder prompt's example project, not one built by Gemini.** A seeded project has no test output, so the facts line first said "0 of 0 tests passed" under "Your API passed its tests". That reads badly, so the line now leaves the tests out when the total is 0 (2 tests added).
- **Not tried on Render** (free tier, 512 MB): Nana measured about 50 MB per live API.
- **A double click on "Wake it up" is guarded in code but not tested** (it would need a fake server).

## 6. What will bite us
- After a server restart or sleep, every live API is asleep and the project may be gone (D-013): the page then shows "Project not found." and a retry button.
- Swagger's "Try it out" calls our backend, so it only works while the backend is awake.

## 7. Terms used
| Term | One-line meaning |
|---|---|
| Live API | The generated project running as its own process on our server, reachable at `/apis/{id}` |
| Swagger page | The generated API's own page (`/docs`) where you can try each endpoint |
| Wake | Start a sleeping live API again from its stored files |
| `noopener` | A link setting that stops the page it opens from controlling ours |

## 8. Lines ready for the report
- A finished project opens as a live API with its own Swagger page, so a person who cannot code can try it from a link; if it has gone to sleep, one button wakes it.


---

# The API's short name appears straight away (Nana, for Perfect, 2026-11-16)

**What:** since #55 the backend names a project after the agent's first sentence ("Reading Club Library API"). The sidebar list was fetched again only when the build's status changed, so the name showed only at the end. `listRefreshKey()` in `src/build/sidebar.ts` adds one more part to `useProjectList`'s refresh key: `named` once the first Thinking step has arrived. The list is fetched **once** more at that moment, not for every step. `App.tsx` uses it.

**How to check it:** `npx vitest run src/build/sidebar.test.ts`. 3 new tests, written first: the key changes at the first Thinking step, stays the same for later steps, and still changes with the project and status. Type check, lint, all 100 tests and the build pass.

---

# Name first, refusals, and the zip name (Nana, for Perfect, 2026-11-16)

**What changed** (`src/build/naming.ts`, with its tests)
- **Name first:** after sending, the page shows "Naming your API…" until the agent has spoken and the project list has been fetched again (`waitingForName`; `useProjectList` now reports `loadedKey`). The cut-off request never shows. A build that ends without a name (a refusal) shows its result at once.
- **Refusals show only the result:** if a build ended without a single Doing step (`nothingBuilt`), the Build screen hides the steps, "Show details" and "Attempt …", and shows an amber "Nothing was built" box with the agent's reason. The badge says **"Not built"** (a new `notBuilt` look in `StatusPill`, page-only: the server still says "failed"). The sidebar recognises a refused project by the backend's name ending "(not built)".
- **Zip name:** the download is saved as the API's name, such as `bookshop-inventory-api.zip` (`zipName`, the same rule as the backend's `zip_name`).

**How to check it:** `npx vitest run` (115 passed). Checked on a local backend with real Gemini: "Naming your API…" then "Gym API"; refusals named "Church Website (not built)" and "Facebook Contact Collector (not built)" with "Not built" badges; the button saved `bookshop-inventory-api.zip`.

---

# Stop build (F-18, Nana, agreed with Perfect, 2026-11-18)

**What changed**
- **`stopProject()`** in `src/api/client.ts`: `POST /projects/{id}/stop`. `openapi.json` and `schema.ts` regenerated with `npm run api:generate`.
- **`useStopBuild`** (`src/hooks/useStopBuild.ts`), in the same style as `useDownload`: `stopping`, a plain `error`, and a guard against a double click. After the server says yes it stays "Stopping…" until the `stopped` event arrives on the live stream; then the control is gone.
- **`StopControl`** in `BuildScreen.tsx`: a quiet "Stop build" button under the timeline while the build is `waiting`, `working` or `retrying`. It asks first ("Stop this build?", "Nothing will be kept…", **Yes, stop it** / **Keep building**), so one stray click can't throw a build away. It is hidden when the live stream is lost, because then we don't know if the build still runs.
- **`plainSteps.ts`:** a stopped build ends with **"Stopped by you"**, not "Finalizing your API…". Decided from the status word, not the sentence.
- **`naming.ts`:** `nothingBuilt` is only for `failed`, so a build stopped before it wrote anything still says "The build was stopped" (red, "Stopped" pill), not "Nothing was built".

**How to check it:** `npx vitest run` (127 passed): `StopControl.test.tsx` (10 tests; port 1, so "Yes, stop it" really fails and shows the plain sentence), plus one test each in `plainSteps.test.ts` and `naming.test.ts`. Live client tests against a real local server: `stopProject` gives `409` for a finished build and `404` for an unknown one. In a browser (Playwright with Edge) on a local backend with real Gemini: Stop, the question, then "The build was stopped" with "Stopped by you"; the sidebar shows "Stopped" (screenshots checked, not committed).

**Not done:** the "Naming your API…" wait comes before the build screen, so Stop can't be pressed in those first seconds. Not tried on the live site yet.

---

# Phone menu fixes (Nana, for Perfect, 2026-11-18)

**What was wrong (under 768px):** the open menu covered the page's own menu button, so there was no way to close it; tapping "New project" or a project did its job, but the menu stayed open over the page, so it looked as if nothing happened; tapping outside or pressing Escape did nothing.

**What changed** (`src/components/AppShell.tsx`, the phone part of `components.css`)
- A tap on **any button inside the menu** closes it (`closeAfterChoice`: one click handler on the `<aside>`; `closest('button')` also catches a tap on the button's icon or text).
- A **dimmed backdrop** beside the open menu; tapping it closes the menu.
- **Escape** closes it (a `keydown` listener that exists only while the menu is open).
- An **X inside the menu** (top right), so a way out is always visible.
- The menu is at most `min(280px, 100vw - 72px)` wide, so some page always shows; the shell uses `100dvh` so the phone's address bar doesn't cut off the bottom; a closed menu has `visibility: hidden`, so Tab and screen readers skip it.
- Wide screens are unchanged: the X and the backdrop are `display: none` there.

**How to check it:** `npx vitest run AppShell` (7 tests; 5 failed on the old code). In a phone-size browser (Playwright with Edge, 390×844): open, then "New project", tap outside, Escape and the X each close it (screenshots checked, not committed).

**Terms:** *backdrop*: the dimmed layer between a menu and the page. *dvh*: "dynamic viewport height", the part of the screen a phone really shows. *Event delegation*: one click handler on a parent that reacts to clicks on its children.
