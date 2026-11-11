# PLAN: the single source of truth for who does what

## How to use this file
- Every task has exactly one owner. A task starts only when everything in **Blocked by** is ✅.
- Finishing a task = flip its row to ✅ **and** flip the tasks it unblocks from ⛔ to 🟢, in the same PR.
- Update the README "Pending now" table in that same PR.
- Dates: the prosit is due **Sun 1 Nov 2026**. Team target: upload by **Sat 31 Oct** so Sunday is buffer ❓ (team target, not given by the course).
  Presentation and viva dates are ❓ (they come after the prosit, not yet known).

Status legend: ✅ Done · 🔄 In progress · 🟢 Ready · ⛔ Blocked · ⚪ Optional · ❓ Confirm

## Roles

| Person | Lead role | Owns | Backup owner | Outside-lane task |
|---|---|---|---|---|
| Elise | Backend / Python | `backend/` | Opei | F-1 clarifying-questions prompt (Opei's lane) |
| Opei | Prompts / LLM | `agent/` | Nana | F-6 Dockerfile + run instructions (Nana's lane) |
| Perfect | Frontend + repo setup | `frontend/`, repo scaffold, CI, branch protection | Nana | W-8 `GET /projects` endpoint (Elise's lane) |
| Nana | Deployment, evaluation, docs | `evaluation/`, `deploy/`, `evidence/`, report assembly | Anyone else | F-9 UI text + user guide, F-10 test one UI page (Perfect's lane) |

Every person also writes their own Section A (all 18 topics, 3–5 pages) and the Section B paragraph for their area.

### Handovers (see D-009)
When a task stalls, someone picks it up. The Owner column then says "Name (from Owner)". The original owner can take any unfinished task back by asking in the team chat and changing the row. Finished work stays with whoever did it; the previous owner reads its learnings note before the teach-back.

| Date | Task | From | To | Why | Hand back by |
|---|---|---|---|---|---|
| 2026-11-02 | S-5 FastAPI skeleton | Elise | Perfect | Owner unreachable; it blocked W-2, W-5, W-6, W-7, W-8 | Done. Elise: read `learnings/backend.md` |
| 2026-11-11 | W-8 `GET /projects` | Perfect | Elise | It sits in Elise's `backend/projects.py`; Perfect can focus on W-6 and W-7, which block W-9 | Perfect can take it back any time; Elise walks Perfect through it before the teach-back |
| 2026-11-02 | S-4 `agent/llm.py` | Opei | Perfect | Owner unreachable; it blocks W-1, W-3, W-4 | Code done; Opei can take over the live check and the rest of `agent/` |

## Scope

| Item | Decision | Reason |
|---|---|---|
| Plain-English request → generated FastAPI project with tests | Build | Core product |
| Agent built with Google ADK (D-010): loop, tools (write-file, run-tests), planning and retries | Build | Core; covers Section A topics m, n, o; the lecturer recommended a framework |
| Clarifying questions + plan preview + human approval | Build | Human-in-the-loop; simple |
| Self-test and retry loop | Build | Reflection; drives quality |
| React + TypeScript UI with typed API client, tests, CI | Build | Required for non-developers; best practice |
| Live, callable API per project at a stable link (run and passed through by our backend; Swagger "Try it out") | Build | The lecturer: a non-developer must be able to call the API (D-011) |
| Zip export with Dockerfile (take-home) | Build | Extra next to the live link |
| Follow-up request after a build ("also add search"): a new round on the existing files | Build if time (F-15) | Lecturer's "loop always active", reduced to what fits (D-012) |
| Evaluation (20 requests: success rate, retries, time) | Build | 20% of grade is implementation and results |
| Model switch (Gemini now, Claude later) | Build as settings (`LLM_PROVIDER`, `LLM_MODEL`); what `agent/llm.py` keeps is decided after the ADK spike (W-10) | No money; must be swappable |
| Auth / accounts, multi-agent, RAG | Design-doc only | Not feasible in one week |
| Permanent per-project deployment, an outside database for users' data, payments, scaling, chatting with the agent during a build | Skip / future work | Costs money or does not fit in the time (D-011, D-012); the report names them as future work |

## Phase 0: Setup (Mon 26 Oct)

| ID | Task | Owner | Blocked by | Status | Done when |
|---|---|---|---|---|---|
| S-1 | Scaffold repo (these files) pushed to `main` | Perfect | none | ✅ | Files on `main`, CI runs (first CI run still to be confirmed on the Actions tab) |
| S-2 | Turn on branch protection (settings in CONTRIBUTING.md) | Perfect | S-1 | ⛔ | Direct pushes to `main` blocked |
| S-3 | Check CODEOWNERS shows no handle errors on GitHub; add all teammates as repo collaborators | Perfect | S-1 | ⛔ | No handle errors; all four can push branches |
| S-4 | Gemini free API key in local `.env`; `agent/llm.py` hello world | Perfect (from Opei) | none | ✅ | `python -m agent.llm` prints a reply; key not in git. Done 2026-11-04 with `gemini-3.5-flash`; output in `evidence/agent/outputs_s4_llm_hello.txt` |
| S-5 | FastAPI skeleton with `/health` and OpenAPI | Perfect (from Elise) | S-1 | ✅ | `/docs` opens locally |
| S-6 | Vite + React + TS (strict) skeleton, oxlint, Prettier, Vitest; design tokens, 13 components, `/dev/gallery`, Start screen | Perfect | S-1 | ✅ | `npm run lint`, `tsc`, `npm test`, `npm run build` all pass |
| S-7 | Draft the 20 plain-English test requests with expected endpoints | Nana | S-1 | 🟢 | `evaluation/requests.json` merged |
| S-8 | Vercel and Render accounts, confirm free tier limits | Nana | none | 🟢 | Limits written in `learnings/deployment.md` |

## Phase 1: Walking skeleton (Tue 27 – Wed 28 Oct)

| ID | Task | Owner | Blocked by | Status | Done when |
|---|---|---|---|---|---|
| W-10 | ADK spike: one tool and one Gemini call with Google ADK, run locally; write down what works, what the free tier allows, what its events look like, and what to keep of `agent/llm.py` (D-010) | Perfect | S-4 | ✅ | Done 2026-11-04: works; notes in `learnings/agent.md`; script and output in `evidence/agent/` |
| W-1 | Tool functions for the ADK agent: write_file, read_file, run_tests (wraps `backend/runner.py`) | Opei | W-10 | ✅ | Each tool has a test. Done 2026-11-07: `agent/tools.py` (also `list_files`), 28 tests; output in `evidence/agent/outputs_w1_tools_tests_run2.txt` |
| W-2 | Sandbox runner: run a generated project's pytest in a temp folder with timeout | Elise | S-5 | ✅ | A passing and a failing project give correct results (PR #3; the secrets leak and output cap are fixed under F-11) |
| W-3 | Agent built with Google ADK: plans, calls the tools, loops until the tests pass or there is a clear stop reason | Elise | W-1, W-2, W-10 | 🟢 | Loop ends with success or a clear stop reason |
| W-4 | Agent instructions (system prompt) for code generation | Opei | W-10 | ✅ | Prompt file reviewed; produces a valid endpoint by hand. Done 2026-11-08: `agent/prompts/builder.md`; live check with `gemini-3.5-flash` built a 4-endpoint Bookshop API whose 8 tests passed (`evidence/agent/outputs_w4_live_check.txt`) |
| W-5 | Endpoints: start project, get status, stream progress (SSE) | Elise | S-5 | ✅ | Visible in `/docs`; stream works with curl. Done 2026-11-09: `POST /projects`, `GET /projects/{id}`, `GET /projects/{id}/events`; no AI behind them yet; output in `evidence/backend/` |
| W-6 | Generate typed API client from OpenAPI | Perfect | S-6, W-5 | 🟢 | `frontend/src/api` builds from the schema |
| W-7 | Chat screen: send request, show live progress | Perfect | W-6 | ⛔ | Works against local backend |
| W-8 | `GET /projects` endpoint (outside lane) | Elise (from Perfect) | S-5 | 🟢 | Returns list; has a test; Elise approves |
| W-9 | End-to-end: one request → one endpoint → test passes → shown in UI | Elise | W-3, W-4, W-5, W-7 | ⛔ | Screenshot + terminal output in `evidence/` |

## Phase 2: Features (Thu 29 Oct)

| ID | Task | Owner | Blocked by | Status | Done when |
|---|---|---|---|---|---|
| F-1 | Clarifying-questions prompt (outside lane) | Elise | W-4 | ✅ | Gives ≤3 sensible questions on 5 sample requests; Opei approves. Done 2026-11-11 (Opei approves in the PR): `agent/prompts/questions.md`, `agent/questions.py`, 7 tests; live check 5 of 5 sensible, `evidence/agent/outputs_f1_*` |
| F-2 | Plan preview + approval step in backend | Elise | W-9, F-1 | ⛔ | Nothing is generated before approval |
| F-3 | Plan preview + approve UI | Perfect | F-2 | ⛔ | Approve and reject both work |
| F-4 | Retry / self-reflection loop (reads test failure, fixes) | Opei | W-9 | ⛔ | Fixes a seeded failing project within N tries |
| F-5 | Zip export endpoint | Elise | W-9 | ⛔ | Unzipped project runs with `pytest` |
| F-6 | Dockerfile + run instructions for the zip (outside lane) | Opei | F-5 | ⛔ | Nana can run the zip by following the text |
| F-7 | Download button; loading, error and empty states; accessibility pass | Perfect | F-5 | ⛔ | Keyboard-only walkthrough works |
| F-8 | Frontend tests for send, approve, download | Perfect | W-7 | ⛔ | Vitest passes in CI |
| F-9 | UI text and user guide for non-developers (outside lane) | Nana | F-3 | ⛔ | Guide merged; Perfect approves |
| F-10 | Test one UI page by hand and file bugs (outside lane) | Nana | F-3 | ⛔ | Bug list in `learnings/frontend-qa.md` |
| F-11 | Security and privacy checks: runner gets a minimal environment (only `PATH`, so `GEMINI_API_KEY` no longer leaks), output capped (last 20,000 characters), input size limits, no secrets in logs | Elise | W-2 | ✅ | Tests for the leak and the cap; checklist in `learnings/backend.md` with results. "No secrets in logs" is checked again once the server has logging |
| F-12 | Live runner: start a generated project as its own process on a local port, stop idle ones, limit how many run at once, minimal environment (D-011) | Elise | W-2, F-11 | 🟢 | A sample project answers a real HTTP call; starting one more than the limit stops the oldest |
| F-13 | Pass-through endpoint `/apis/{id}/...`; reopen restarts the API from stored files; `api_url` and `live_status` on the project (D-011) | Elise | F-12, W-5 | ⛔ | `/apis/{id}/docs` opens and "Try it out" works through our backend |
| F-14 | Ready screen: live link, the API's Swagger page, "Wake it up" when sleeping, zip as take-home | Perfect | F-13, F-7 | ⛔ | Keyboard-only walkthrough works; screenshot in `evidence/live/` |
| F-15 | Follow-up request after a build: a new round on the existing files (D-012) | Perfect | F-13 | ⚪ | Optional; only if there is time |

## Phase 3: Evaluation and deployment (Fri 30 – Sat 31 Oct)

| ID | Task | Owner | Blocked by | Status | Done when |
|---|---|---|---|---|---|
| E-1 | Scoring script (pass/fail per request, retries, seconds) | Nana | W-9 | ⛔ | Runs on 2 requests |
| E-2 | Run evaluation on all 20 requests | Nana | E-1, F-4, F-5 | ⛔ | `evidence/evaluation/outputs_eval_run1.txt` saved |
| E-3 | Fix the top failures (prompts: Opei; code: Elise) | Opei | E-2 | ⛔ | Fixes listed in `learnings/` |
| E-4 | Re-run evaluation, compare to run 1 | Nana | E-3 | ⛔ | `outputs_eval_run2.txt` saved; numbers go into the report only now |
| D-1 | Deploy frontend to Vercel | Nana | S-6 | 🟢 | Public URL loads |
| D-2 | Deploy backend to Render (keys in host settings, not code) | Nana | W-9 | ⛔ | `/health` OK on public URL |
| D-3 | Smoke test deployed frontend ↔ backend | Nana | D-1, D-2 | ⛔ | One full request works online |
| D-4 | Prove the model switch: change `LLM_MODEL` (and the provider if ADK allows it), still works | Opei | W-4 | ✅ | Terminal output saved in `evidence/`; if only the model name can change, say so in the report. Done 2026-11-10: the model name switches by `.env` alone; no second model finished a build (flash-lite skipped tools, others refused or overloaded on the free tier); `evidence/agent/outputs_d4_model_switch.txt` |

## Phase 4: Writing and handing in (from Wed 28; final Sat 31 Oct – Sun 1 Nov)

| ID | Task | Owner | Blocked by | Status | Done when |
|---|---|---|---|---|---|
| A-1 | Section A (18 topics a–r, 3–5 pages, maths + visuals, justified) | Elise | none | 🟢 | `report/section-a/elise.md` complete |
| A-2 | Section A | Opei | none | 🟢 | `report/section-a/opei.md` complete |
| A-3 | Section A | Perfect | none | 🟢 | `report/section-a/perfect.md` complete |
| A-4 | Section A | Nana | none | 🟢 | `report/section-a/nana.md` complete |
| R-1 | Architecture diagram | Elise | W-9 | ⛔ | Image in `report/figures/` |
| B-1 | Section B paragraph: backend | Elise | E-4 | ⛔ | In `report/section-b.md` |
| B-2 | Section B paragraph: prompts / LLM | Opei | E-4 | ⛔ | In `report/section-b.md` |
| B-3 | Section B paragraph: frontend | Perfect | E-4 | ⛔ | In `report/section-b.md` |
| B-4 | Section B paragraph: deployment + evaluation | Nana | E-4 | ⛔ | In `report/section-b.md` |
| B-5 | Assemble Section B (approach, architecture, implementation, evaluation) | Nana | B-1..B-4, R-1 | ⛔ | Reads as one text |
| R-2 | Assemble report PDF; **GitHub link on page 1** | Nana | A-1..A-4, B-5 | ⛔ | PDF checked |
| R-3 | Slides (10 min, engaging, Section B content); **GitHub link on page 1** | Nana | E-4 | ⛔ | Slides done; each person has a speaking part |
| R-4 | Teach-back: each person walks the others through their learnings note and code | Perfect | W-9, F-5 | ⛔ | Held; open questions logged |
| R-5 | Upload report and slides to Canvas | Nana | R-2, R-3 | ⛔ | Canvas receipts in `evidence/deliverables/` |
| R-6 | Final repo check: no secrets, README and PLAN current | Perfect | R-5 | ⛔ | Checked by a second person |
| P-1 | Presentation date and slot (after the prosit) | Nana | none | ❓ | Confirmed with course staff |
| V-1 | Viva date and format (after presentations; individual, covers all the code) | Nana | none | ❓ | Confirmed with course staff |

## Deliverables checklist

| ✓ | What is asked (quoted) | Evidence file | From task | Who captures |
|---|---|---|---|---|
| ☐ | "Upload Code to GitHub" | link on report and slides page 1 | S-1 | Perfect |
| ☐ | "The first page of the slides should have the link to the GitHub code" | `evidence/deliverables/slides-page1.png` | R-3 | Nana |
| ☐ | "Upload presentation slides to Canvas" | `evidence/deliverables/canvas-slides.png` | R-5 | Nana |
| ☐ | "The first page of the technical report should have the link to the GitHub code" | `evidence/deliverables/report-page1.png` | R-2 | Nana |
| ☐ | "Upload technical report to Canvas" | `evidence/deliverables/canvas-report.png` | R-5 | Nana |
| ☐ | Section A: all topics a–r, 3 ≤ p ≤ 5, "mathematical explanations and visuals where appropriate", justification | `report/section-a/<name>.md` (one per person) | A-1..A-4 | each person |
| ☐ | Section B: approach and justification, architecture, implementation choices, evaluation (3 ≤ p ≤ 5) | `report/section-b.md` | B-5 | Nana |
| ☐ | Evaluation results | `evidence/evaluation/outputs_eval_run1.txt`, `outputs_eval_run2.txt` | E-2, E-4 | Nana |
| ☐ | Working end-to-end demo | `evidence/skeleton/ui-end-to-end.png`, `outputs_skeleton_e2e.txt` | W-9 | Elise |
| ☐ | A non-developer can call the generated API from a link ("a link where you can make requests", lecture) | `evidence/live/ui-live-api.png`, `evidence/live/outputs_live_calls.txt` | F-13, F-14 | Perfect |
| ☐ | Deployed and reachable | `evidence/deploy/ui-online.png`, `outputs_deploy_health.txt` | D-3 | Nana |
| ☐ | "10-minute team presentation" (after the prosit) | slides + teach-back done | R-3, R-4 | Nana |

## Risks

| Risk | What we do |
|---|---|
| Gemini free tier rate limits slow evaluation | Retries with waits in `llm.py`; small test set; run evaluation overnight if needed |
| Free tier models write buggy code | Retry loop (F-4); log failures and fix prompts (E-3) |
| Render free tier sleeps | Warm it up before the demo; say so in the report |
| Generated code could be unsafe | Run only in a temp folder with a timeout and size limits (F-11); say it is a demo sandbox, not production |
| Running AI-written code live on a free host (memory, security) | Limit how many run, stop idle ones, minimal environment (F-11, F-12); say in the report it is a demo, not production |
| A generated API's data resets when the free host restarts | Reopening restarts it from stored source; say so plainly in the report (D-011) |
| ADK is new to us | Spike first (W-10); fall back to a hand-written loop and record a new decision |
| Four people new to this; one week | Walking skeleton first (W-9); cut scope by the table, not by skipping tests |
| Someone cannot explain another's code | Outside-lane tasks and teach-back (R-4); the viva covers all the code |
| Section A (18 topics) too long for 5 pages | Start on Day 1; one diagram per cluster of topics; equations only where they explain |
