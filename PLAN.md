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

## Scope

| Item | Decision | Reason |
|---|---|---|
| Plain-English request → generated FastAPI project with tests | Build | Core product |
| Agent loop (Thought → Action → Observation) with write-file and run-tests tools | Build | Core; covers Section A topics m, n, o |
| Clarifying questions + plan preview + human approval | Build | Human-in-the-loop; simple |
| Self-test and retry loop | Build | Reflection; drives quality |
| React + TypeScript UI with typed API client, tests, CI | Build | Required for non-developers; best practice |
| Zip export with Dockerfile; OpenAPI docs | Build | Free delivery path |
| Evaluation (20 requests: success rate, retries, time) | Build | 20% of grade is implementation and results |
| LLM provider switch (Gemini now, Claude later) | Build (one file, `agent/llm.py`) | No money; must be swappable |
| Auth / accounts, multi-agent, RAG | Design-doc only | Not feasible in one week |
| Hosting users' generated APIs live, payments, scaling | Skip | Costs money |

## Phase 0: Setup (Mon 26 Oct)

| ID | Task | Owner | Blocked by | Status | Done when |
|---|---|---|---|---|---|
| S-1 | Scaffold repo (these files) pushed to `main` | Perfect | none | 🔄 | Files on `main`, CI runs |
| S-2 | Turn on branch protection (settings in CONTRIBUTING.md) | Perfect | S-1 | ⛔ | Direct pushes to `main` blocked |
| S-3 | Check CODEOWNERS shows no handle errors on GitHub; add all teammates as repo collaborators | Perfect | S-1 | ⛔ | No handle errors; all four can push branches |
| S-4 | Gemini free API key in local `.env`; `agent/llm.py` hello world | Opei | none | 🟢 | `python -m agent.llm` prints a reply; key not in git |
| S-5 | FastAPI skeleton with `/health` and OpenAPI | Elise | S-1 | ⛔ | `/docs` opens locally |
| S-6 | Vite + React + TS (strict) skeleton, ESLint, Prettier, Vitest | Perfect | S-1 | ⛔ | `npm run lint`, `tsc`, `npm test`, `npm run build` all pass |
| S-7 | Draft the 20 plain-English test requests with expected endpoints | Nana | S-1 | ⛔ | `evaluation/requests.json` merged |
| S-8 | Vercel and Render accounts, confirm free tier limits | Nana | none | 🟢 | Limits written in `learnings/deployment.md` |

## Phase 1: Walking skeleton (Tue 27 – Wed 28 Oct)

| ID | Task | Owner | Blocked by | Status | Done when |
|---|---|---|---|---|---|
| W-1 | Tool definitions: write_file, read_file, run_tests | Opei | S-4 | ⛔ | Each tool has a test |
| W-2 | Sandbox runner: run a generated project's pytest in a temp folder with timeout | Elise | S-5 | ⛔ | A passing and a failing project give correct results |
| W-3 | Agent loop (Thought → Action → Observation) | Elise | W-1, W-2 | ⛔ | Loop ends with success or a clear stop reason |
| W-4 | System prompt for code generation | Opei | S-4 | ⛔ | Prompt file reviewed; produces a valid endpoint by hand |
| W-5 | Endpoints: start project, get status, stream progress (SSE) | Elise | S-5 | ⛔ | Visible in `/docs`; stream works with curl |
| W-6 | Generate typed API client from OpenAPI | Perfect | S-6, W-5 | ⛔ | `frontend/src/api` builds from the schema |
| W-7 | Chat screen: send request, show live progress | Perfect | W-6 | ⛔ | Works against local backend |
| W-8 | `GET /projects` endpoint (outside lane) | Perfect | S-5 | ⛔ | Returns list; has a test; Elise approves |
| W-9 | End-to-end: one request → one endpoint → test passes → shown in UI | Elise | W-3, W-4, W-5, W-7 | ⛔ | Screenshot + terminal output in `evidence/` |

## Phase 2: Features (Thu 29 Oct)

| ID | Task | Owner | Blocked by | Status | Done when |
|---|---|---|---|---|---|
| F-1 | Clarifying-questions prompt (outside lane) | Elise | W-4 | ⛔ | Gives ≤3 sensible questions on 5 sample requests; Opei approves |
| F-2 | Plan preview + approval step in backend | Elise | W-9, F-1 | ⛔ | Nothing is generated before approval |
| F-3 | Plan preview + approve UI | Perfect | F-2 | ⛔ | Approve and reject both work |
| F-4 | Retry / self-reflection loop (reads test failure, fixes) | Opei | W-9 | ⛔ | Fixes a seeded failing project within N tries |
| F-5 | Zip export endpoint | Elise | W-9 | ⛔ | Unzipped project runs with `pytest` |
| F-6 | Dockerfile + run instructions for the zip (outside lane) | Opei | F-5 | ⛔ | Nana can run the zip by following the text |
| F-7 | Download button; loading, error and empty states; accessibility pass | Perfect | F-5 | ⛔ | Keyboard-only walkthrough works |
| F-8 | Frontend tests for send, approve, download | Perfect | W-7 | ⛔ | Vitest passes in CI |
| F-9 | UI text and user guide for non-developers (outside lane) | Nana | F-3 | ⛔ | Guide merged; Perfect approves |
| F-10 | Test one UI page by hand and file bugs (outside lane) | Nana | F-3 | ⛔ | Bug list in `learnings/frontend-qa.md` |
| F-11 | Security and privacy checks: input size limits, no secrets in logs, sandbox timeout | Elise | W-2 | ⛔ | Checklist in `learnings/backend.md` with results |

## Phase 3: Evaluation and deployment (Fri 30 – Sat 31 Oct)

| ID | Task | Owner | Blocked by | Status | Done when |
|---|---|---|---|---|---|
| E-1 | Scoring script (pass/fail per request, retries, seconds) | Nana | W-9 | ⛔ | Runs on 2 requests |
| E-2 | Run evaluation on all 20 requests | Nana | E-1, F-4, F-5 | ⛔ | `evidence/evaluation/outputs_eval_run1.txt` saved |
| E-3 | Fix the top failures (prompts: Opei; code: Elise) | Opei | E-2 | ⛔ | Fixes listed in `learnings/` |
| E-4 | Re-run evaluation, compare to run 1 | Nana | E-3 | ⛔ | `outputs_eval_run2.txt` saved; numbers go into the report only now |
| D-1 | Deploy frontend to Vercel | Nana | S-6 | ⛔ | Public URL loads |
| D-2 | Deploy backend to Render (keys in host settings, not code) | Nana | W-9 | ⛔ | `/health` OK on public URL |
| D-3 | Smoke test deployed frontend ↔ backend | Nana | D-1, D-2 | ⛔ | One full request works online |
| D-4 | Prove the provider switch: change env var, still works | Opei | W-4 | ⛔ | Terminal output saved in `evidence/` |

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
| ☐ | Deployed and reachable | `evidence/deploy/ui-online.png`, `outputs_deploy_health.txt` | D-3 | Nana |
| ☐ | "10-minute team presentation" (after the prosit) | slides + teach-back done | R-3, R-4 | Nana |

## Risks

| Risk | What we do |
|---|---|
| Gemini free tier rate limits slow evaluation | Retries with waits in `llm.py`; small test set; run evaluation overnight if needed |
| Free tier models write buggy code | Retry loop (F-4); log failures and fix prompts (E-3) |
| Render free tier sleeps | Warm it up before the demo; say so in the report |
| Generated code could be unsafe | Run only in a temp folder with a timeout and size limits (F-11); say it is a demo sandbox, not production |
| Four people new to this; one week | Walking skeleton first (W-9); cut scope by the table, not by skipping tests |
| Someone cannot explain another's code | Outside-lane tasks and teach-back (R-4); the viva covers all the code |
| Section A (18 topics) too long for 5 pages | Start on Day 1; one diagram per cluster of topics; equations only where they explain |
