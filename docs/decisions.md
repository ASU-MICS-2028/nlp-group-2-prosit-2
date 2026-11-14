# Decisions

From D-017 on, each decision also records **when** (date and time, GMT) and **who made the call**, so we can trace it later. Older entries are not rewritten.

## D-001: Frontend and backend are separate programs that talk only through an API
Date: 2026-10-26 · Status: Proposed
Affects: Elise, Perfect
Decision: The React UI never imports backend code. It calls the FastAPI server through its OpenAPI schema, and a typed TypeScript client is generated from that schema.
Why: This is Mesora's stated principle (separation of concerns). The generated client turns a backend change that breaks the UI into a build error instead of a demo-day surprise.
Gave up: A single-folder app would be quicker to start but would not follow the brief.

## D-002: All LLM calls go through `agent/llm.py`; Gemini free tier now, Claude later
Date: 2026-10-26 · Status: Proposed
Affects: Opei (owns), everyone who calls the model
Note (2026-11-03): partly replaced by D-010. Inside the agent, ADK makes the model calls; this wrapper keeps the settings and one-off calls.
Decision: One file wraps the provider. `LLM_PROVIDER` and `LLM_MODEL` in `.env` choose which one runs. Start with the Gemini free tier. Add Claude when the team has credits.
Why: No budget. Free tiers change, so the switch must be one place. D-4 in PLAN.md proves the switch works.
Gave up: Free-tier rate limits and weaker code quality than a paid model.

## D-003: Hosting: frontend on Vercel, backend on Render (or Hugging Face Spaces), generated APIs delivered as a zip
Date: 2026-10-26 · Status: Proposed
Affects: Nana (owns), Elise, Perfect
Note (2026-11-03): refined by D-011. The backend runs on Render because it must be a long-running server, and generated APIs run live behind it; the zip is now only a take-home.
Decision: Free tiers only. Users receive their generated API as a zip with a Dockerfile instead of us hosting it. Backend host is kept swappable (config in `deploy/`).
Why: Vercel serverless has no persistent disk and short time limits, which does not suit an agent that writes files and runs tests. Hosting users' APIs live would cost money.
Gave up: The backend sleeps when idle on free tiers (slow first request). No one-click live API for the user.

## D-004: Frontend uses React + Vite + TypeScript (strict), plain `fetch`, no state library
Date: 2026-10-26 · Status: Proposed
Affects: Perfect, Nana
Decision: React + Vite + TypeScript with `strict`, oxlint (the linter the current Vite template ships with), Prettier, Vitest + Testing Library, a generated API client, SSE for live progress. Visual style follows `knowledge/DESIGN-SYSTEM.md`: design tokens in one CSS file, plain CSS classes, Lucide icons, Inter and JetBrains Mono fonts installed from npm (no CDN).
Why: Standard best practice, easy to explain, strong type safety. oxlint needs no config and is one fewer tool to explain than ESLint. Plain CSS with tokens means no styling library to learn.
Gave up: Heavier tools (Redux, Next.js, Tailwind, ESLint plugin setups) that would be harder for everyone to explain in the viva.

## D-005: Generated APIs use FastAPI + SQLite + pytest
Date: 2026-10-26 · Status: Proposed
Affects: Elise, Opei
Decision: Every generated project is plain FastAPI with SQLite storage and pytest tests, in a fixed folder layout the agent is told to follow.
Why: A fixed, small target makes the LLM's output more reliable and the tests easy to run. FastAPI gives OpenAPI docs for free.
Gave up: Other languages and databases.

## D-006: Plain-code rule
Date: 2026-10-26 · Status: Proposed
Affects: everyone
Decision: Short functions, clear names, comments on non-obvious lines, no clever tricks. Every member must be able to explain all the code.
Why: The viva is individual and covers all the code.
Gave up: Some speed and elegance.

## D-007: Generated code runs in a temporary folder with a timeout and size limits
Date: 2026-10-26 · Status: Proposed
Affects: Elise
Decision: The sandbox runner copies generated files to a temp folder, runs pytest with a time limit, and caps input and output size. It is a demo sandbox, not production-grade isolation, and the report says so.
Why: LLM-written code is untrusted. Full isolation (containers) is out of scope for one week.
Gave up: Strong isolation guarantees.

## D-008: The API between frontend and backend is agreed in writing first (`docs/api-contract.md`)
Date: 2026-11-02 · Status: Proposed
Affects: Elise (reviews and changes it), Perfect (owns the draft), Nana (evaluation calls the same API)
Decision: The contract lists every endpoint, its JSON shape, the live-progress stream (SSE) and the error format. Elise reviews it; once both agree it becomes Accepted, and the FastAPI code and the generated TypeScript client must match it.
Why: Both sides can build at the same time without waiting. It follows D-001 (frontend and backend talk only through the API).
Gave up: Some freedom to change shapes quickly. Changing an agreed shape needs a new decision.

## D-009: Stalled tasks are picked up by whoever can, and owners can take them back
Date: 2026-11-02 · Status: Accepted (Perfect, after the team stopped responding; teammates can still object)
Affects: everyone, most of all Elise (backend) and Opei (agent)
Decision: When a 🟢 task has no progress and its owner is unreachable, someone else picks it up. The pick-up is recorded in the same PR: the Owner column says "Name (from Owner)" and a row is added to "Handovers" in PLAN.md. The original owner can take any unfinished task back at any time by asking in the team chat and changing the row. Finished work stays with whoever did it, and the previous owner must read its learnings note before the teach-back.
Why: The week is short and the backend is on the critical path. Waiting stalls everyone, and PLAN.md should say who really does what.
Gave up: One owner per area is now a default, not a promise. The viva still covers all the code, so everyone has to be able to explain the picked-up parts too.

## D-010: The agent is built with Google ADK (the lecturer's recommendation)
Date: 2026-11-03 · Status: Accepted (Perfect; Elise, Opei and Nana to confirm)
Affects: Elise (W-3), Opei (W-1, W-4), Perfect (W-10)
Decision: The agent loop uses Google's Agent Development Kit. Tools are plain Python functions (write_file, read_file, run_tests, which wraps the sandbox runner). Our code provides the tools, the instructions (prompts), the approval flow, the retry limit and the event stream for the UI. The first step is a spike (W-10): one tool and one Gemini call, to learn how ADK really behaves before the rest is planned around it. If the spike fails, we fall back to a hand-written loop and record a new decision.
Why: The lecturer said to use a framework and named ADK. It fits Gemini, removes most of the loop plumbing, and its events map to the live progress timeline in the UI.
Gave up: A hand-written loop is easier to explain line by line. ADK adds a library and concepts that everyone must be able to explain in the viva. Inside the agent, ADK makes the model calls, so `agent/llm.py` (D-002) shrinks to settings and one-off calls; the spike decides what to keep.

## D-011: Each generated API runs live behind our backend, at a stable link
Date: 2026-11-03 · Status: Accepted (Perfect; Elise and Nana to confirm)
Affects: Elise (live runner, security), Perfect (Ready screen), Nana (deployment)
Decision: After the tests pass, the backend starts the generated project as its own process on a local port and passes calls through at `/apis/{id}/...`. Its own Swagger page at `/apis/{id}/docs` lets a non-developer click "Try it out" and really call it. The project's files are stored, so reopening it restarts the same API at the same link. Limits: a small number of running APIs at once (start with 3), idle ones stopped, a minimal environment with no secrets, and caps on output and request size. The zip download stays as a take-home. The backend runs on Render (a long-running server); Vercel hosts only the frontend (D-003).
Why: The lecturer expects "a link where you can make requests", with Swagger, so a non-developer can use the API. Free hosting gives one public port and no persistent disk, so passing calls through our own backend is the simplest way to do it.
Gave up: Permanent per-project deployments (for example through Vercel's API), an outside database for users' data, and a live API that keeps its data across host restarts. Data inside a generated API lasts while the server is awake and resets when the free host restarts; the report says so. Running AI-written code live is a real risk and depends on the F-11 fixes (secrets leak, output cap).

## D-012: Follow-up requests only after a build
Date: 2026-11-03 · Status: Accepted (Perfect; team to confirm)
Affects: Perfect (F-15), Elise
Decision: After the API is ready, the user can ask for a change ("also add search") and the agent runs a new round on the existing files, if there is time (F-15, optional). Changing the agent while it is building is future work and is described as such in the report.
Why: The lecturer's "the loop must always be active" described the ideal. Mid-build interruption needs background tasks and careful handling of timing; a follow-up after the build avoids that.
Gave up: Chatting with the agent during a build.

## D-013: Projects are kept in server memory for now; the database choice is open
Date: 2026-11-06 · Status: Proposed (Elise; team to decide the database)
Affects: Elise (W-5, owns), Perfect (sidebar needs projects to survive a reload), Nana (deployment)
Decision: For W-5, projects live in a Python dictionary inside `backend/projects.py`. All storing code stays in that one place so a database can replace it later.
Open question for the team: a shared, hosted database would let projects survive restarts. Options on free tiers: hosted Postgres (for example Neon or Supabase) or Firebase Firestore (NoSQL). Either needs a connection secret shared with everyone who runs the backend and in CI, and tests that don't touch the shared data. Check each free tier's current limits before choosing.
Why: Building and testing the endpoints needs no database today. Adding one now means more setup, more secrets and more to explain in the viva.
Gave up (for now): Projects are lost when the server restarts, so the sidebar empties after a restart.

## D-014: The frontend is deployed to Vercel from a laptop with the Vercel CLI
Date: 2026-11-10 · Status: Proposed (Nana; Perfect to confirm, as frontend owner)
Affects: Nana (owns, D-1), Perfect (frontend changes need a redeploy)
Decision: Deploy the built frontend with `npx vercel --prod` from a laptop (steps in `deploy/README.md`). Nana redeploys after any `frontend/` change is merged into `main`, and on the morning of every demo.
Why: Vercel's free (Hobby) plan cannot connect a project to a repository owned by a Git organisation, and ours belongs to ASU-MICS-2028 (https://vercel.com/docs/limits, read 2026-11-10). The CLI upload is free and needs no secret in the repo.
Gave up: Automatic deploys on every merge. Alternatives were the paid Pro plan, or a GitHub Action with a Vercel token stored in the organisation's settings (more secrets to manage and explain).

## D-015: The frontend's API types are generated with `openapi-typescript`, run through `npx`
Date: 2026-11-12 · Status: Proposed (Perfect; Elise to confirm, since the backend's schema feeds it)
Affects: Perfect (owns), Elise (any change to a response shape changes the generated types)
Decision: `npm run api:generate` saves the backend's OpenAPI schema (`frontend/scripts/export_openapi.py`) and turns it into TypeScript types (`frontend/src/api/schema.ts`) with `openapi-typescript@7.13.0`, started through `npx`. Both generated files are committed. On top of the types, `frontend/src/api/client.ts` is a small hand-written `fetch` layer that turns every failure into one plain sentence. Its tests call a real backend (`client.live.test.ts`, switched on with `VITE_LIVE_API=1`), not a fake.
Why: It follows D-001: a backend change that breaks the UI becomes a build error. `openapi-typescript` needs TypeScript 5 but the project uses TypeScript 7, so installing it makes npm refuse (a peer-dependency conflict). Forcing it with `--legacy-peer-deps` would hide the conflict and could break `npm ci` in CI. `npx` gives it its own TypeScript 5 in a throwaway folder and leaves our dependencies and lockfile alone.
Gave up: Regenerating needs internet (npx downloads the tool) and Python with the backend's virtual environment on. The generated files can go out of date if nobody regenerates after a backend change. The live tests need a running backend, so CI skips them.

## D-016: The live progress stream is read with `fetch`, not the browser's `EventSource`
Date: 2026-11-12 · Status: Proposed (Perfect; Elise to confirm, since she decides what the stream sends)
Affects: Perfect (owns), Elise (the events her builder reports)
Decision: `streamEvents` in `frontend/src/api/client.ts` opens `GET /projects/{id}/events` with `fetch`, reads the body piece by piece, and cuts it into SSE messages with `splitMessages` (`frontend/src/api/events.ts`). The server still speaks SSE, as in D-004 and `docs/api-contract.md`. Only the reader on our side differs.
Why: `EventSource` does not exist in the test environments we use (jsdom and Node), so testing it would need a pretend one, and we agreed to test against a real server. A `fetch` reader runs the same in tests and in the browser. We also control when it stops: `EventSource` reconnects by itself forever, even after the server hangs up on purpose.
Gave up: Automatic reconnect. If the connection drops, the screen shows "Live progress stopped" with a button that opens the project again, and the server replays the whole history (as the contract says). We also wrote about 30 lines of parsing that `EventSource` would have done for us.

## D-017: Until the approve step exists, `POST /projects` starts the build at once, and the server reads `.env` at start-up
Date: 2026-11-14 05:55 GMT · Decided by: Elise (backend owner) · Status: Accepted (Perfect agreed in the W-7 review, 2026-11-12)
Affects: Elise (owns), Perfect (the chat screen only calls `POST /projects`), Opei (his retry loop is what runs)
Decision: `POST /projects` answers `201` straight away and then runs the build in FastAPI's `BackgroundTasks` (`run_build` in `backend/projects.py`). The AI gets the request as written, because there is no plan yet. The build is Opei's `build_with_retries`, with `add_event` as the reporter. The server is started with `uvicorn backend.main:app --env-file .env`, so it gets `GEMINI_API_KEY` and `LLM_MODEL` without any code reading the file.
Why: W-9 needs one request to become a tested API on screen, and the approve endpoint is F-2 (which waits on W-9). Building in the background lets the page get the id at once and watch the live stream. `BackgroundTasks` is built into FastAPI, so there is no new library. `--env-file` is a uvicorn option, so there is no new code and the key stays out of the repo.
Gave up: The plan and approval before building (comes with F-2, which moves the build start to `POST /projects/{id}/approve`). A real job queue: a build is lost if the server restarts. The AI builds from the raw request, which is less precise than an approved plan.


## D-018: The main model gets 3 tries; if it was busy on all 3, a 4th try runs on a backup model
Date: 2026-11-14 06:13 GMT, changed to "after 3 busy tries, 4 tries in total" at 06:33 GMT · Decided by: Elise · Status: Proposed (Opei to confirm: it changes his retry loop and `agent/llm.py`)
Affects: Opei (owns `agent/retry.py` and `agent/llm.py`), Elise (`run_build` passes the backup in), Perfect (the screen now says "Attempt 1 of 4")
Decision: A new optional setting `LLM_BACKUP_MODEL` (read by `backup_model()` in `agent/llm.py`). `MAX_ATTEMPTS` goes from 3 to 4. In `build_with_retries`, each try that ends "busy" (503) or "too many requests" (429) is counted. After the third one (`SWITCH_AFTER_BUSY = 3`), the last try uses the backup model straight away, with no 30-second wait. Fewer busy tries: the main model is kept, as before. No backup set: the 4th try is simply one more try on the main model. Backup for now: `gemini-3-flash-preview`, the fastest of the models that made a tool call in a one-call check on 2026-11-14 (`gemini-3.1-flash-lite` also did).
Why: The free tier was busy for long stretches on 2026-11-14; run 1 of W-9 lost a whole try to waiting. The main model is the one tested with full builds, so it keeps its 3 tries and the backup is a last resort (Elise: only when it is critical; the 4th try is "one last shot"). We wrote it ourselves instead of using ADK's `FallbackModel`, because that one switches on every single busy reply, the opposite of "last resort", and a few plain lines are easier to explain. This also answers the contract's open question "Is `max_attempts` fixed at 3?": it is 4.
Gave up: Every build can now take a 4th try, also when the tests keep failing: worst case about 20 minutes and 160 AI calls instead of 15 and 120. Switching sooner (faster, but uses the less-tested model for short blips). A second provider (Groq or OpenRouter through LiteLLM): a real backup when all of Google is busy, but a new library and untested tool use; kept as future work. The backup has passed a one-call tool check; a full build with it was tried on 2026-11-14 (see `learnings/agent.md`).
