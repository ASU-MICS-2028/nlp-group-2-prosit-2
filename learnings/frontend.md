# Frontend

Owner: Perfect · Last updated: 2026-11-12 · Status: partly working (skeleton, design components, Start screen and typed API client done; no screen calls the backend yet)

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
