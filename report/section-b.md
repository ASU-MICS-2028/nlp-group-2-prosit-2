# Section B: Mesora API Builder — approach, architecture, implementation, evaluation

> **DRAFT (started 2026-11-14 by Nana, assembler, B-5).** Not final. Rules for this file:
> - Each owner writes the paragraph for their own area, in their own words (B-1 to B-4). Slots are marked ✍️.
>   The "Facts to use" lists come from the repo (PLAN, decisions, learnings, evidence). Check them, then **replace** the list with your paragraph.
> - **No results before they are measured** (`report/README.md`). Every number marked ⏳ waits for E-2 / E-4.
> - Target length: 3–5 pages in the PDF. Plain words; every line must be explainable in the viva.

GitHub: https://github.com/ASU-MICS-2028/nlp-group-2-prosit-2 (this link also goes on page 1 of the report)

Live demo: frontend https://mesora-api-builder.vercel.app · backend https://nlp-group-2-prosit-2.onrender.com
(free tier: the backend sleeps after 15 idle minutes, and the first request then takes about a minute)

---

## 1. Approach and justification

**The problem.** Mesora, an AI lab in Ghana, wants a tool like Lovable or Replit, but for **backend APIs**: a person who
cannot code describes what they need in plain English and gets a working, tested API. Mesora also believes the frontend
and backend of an app should stay separate and talk only through a well-defined API.

**Our approach.** We built a web platform where the user types a request (for example *"a bookshop where I can add books
and see which are in stock"*). A **coding agent** then writes a small FastAPI project with its own tests, runs those tests in a
sandbox, reads any failures, and fixes its code before saying the API is ready. The user sees each step live, in plain words
(Thinking, Doing, Result).

**Why this way** (each choice is a recorded decision in `docs/decisions.md`):
| Choice | Why | What we gave up |
|---|---|---|
| Frontend and backend are separate programs that talk only through an API (D-001, D-008) | Matches Mesora's belief; each half can be built, tested and deployed alone | A little more setup (CORS, two deploys) |
| One agent built with Google ADK (D-010) | The lecturer recommended a framework and named ADK; it runs the tool-calling loop and its events map onto our live timeline | A hand-written loop would be easier to explain line by line |
| The agent must **prove** its work with tests (D-005, D-007) | A non-developer cannot read code, so "the tests pass" is the evidence they can trust | A passing test is not proof the API is good; the evaluation checks more (section 4) |
| Gemini free tier, behind one file `agent/llm.py` (D-002) | No money; the provider can change in one place | Free-tier limits: the model is sometimes "busy" (section 4.4) |
| Plain code everywhere (D-006) | Every member must explain every line in the viva | Fewer clever shortcuts |
| Free hosting: Vercel + Render (D-003, D-014) | Costs nothing; anyone can try the live demo | The backend sleeps, and has no permanent disk (section 3.4) |

✍️ *Team: check this table against your own understanding before B-5 is final.*

## 2. Architecture

✍️ **Figure 1 (R-1, Elise): architecture diagram** → `report/figures/architecture.png`. Suggested boxes:
Browser (React UI on Vercel) → HTTPS + JSON → FastAPI backend (Render) → builder agent (Google ADK) → Gemini;
the agent's tools → sandbox runner (temporary folder, pytest, time and size limits).

**How one request flows** (draft from the code; Elise to confirm):
1. The user types a request on the Start screen. The frontend sends `POST /projects`.
2. The backend creates the project and starts the build in the background (W-9, D-017), so the page does not wait.
3. The builder agent (ADK) is given the builder instructions (`agent/prompts/builder.md`) and four tools: write a file,
   read a file, list files, run the tests. It plans, writes `app/main.py` and `tests/`, and calls `run_tests`.
4. `run_tests` copies the files into a fresh temporary folder and runs `pytest` with a time limit, an output limit and a
   minimal environment, so AI-written code never sees our secrets (D-007, F-11).
5. If tests fail, the retry loop (F-4) shows the failure to the model, asks it to reflect on the cause, and lets it try again
   (up to 3 tries).
6. Every step is sent to the browser as a live event stream (`GET /projects/{id}/events`), which the chat screen shows as a timeline.
7. The project ends `ready` (all tests pass) or `failed` with one plain sentence saying why.

**Where state lives.** Projects are kept in the backend's memory (D-013). That is simple, but projects are lost when the
server restarts, which on the free host happens after every sleep or redeploy.

## 3. Implementation choices and details

### 3.1 Backend ✍️ (B-1, Elise)
Facts to use (replace with your paragraph):
- FastAPI server: `/health`, `POST /projects`, `GET /projects`, `GET /projects/{id}`, `GET /projects/{id}/events` (live stream). Plain-sentence 422 errors (W-5, D-013).
- The build starts in the background from `POST /projects` (W-9, D-017). First Ready build from the chat screen: 2026-11-14 (`evidence/backend/outputs_w9_run2_ready.txt`).
- Agent loop `backend/builder.py` with five stop rules (too slow, too many steps, service busy, no files, tests failed) (W-3).
- Sandbox runner: temporary folder, timeout, output cap, only `PATH` and `SYSTEMROOT` passed on (W-2, F-11).
- Tests: 130 passing on 2026-11-14 (Elise's AI-use log line); count again before the report.
- Not done yet (check before writing): plan + approval step (F-2), zip export (F-5), live generated API at a link (F-12, F-13).

### 3.2 Agent, prompts and the LLM (B-2, Opei)
A language model can only write text, so the agent works through four tools in `agent/tools.py` (W-1): write a file,
read a file, list the files, and run the tests. They are plain Python functions; ADK reads their names, type hints and
docstrings to tell the model how to call them. Each project's files live in memory, and unsafe names (absolute paths,
`..`, `./`, drive letters, backslashes) are refused. The tools never crash: a mistake comes back as a message the model can read
and fix. The model's instructions are a Markdown file, `agent/prompts/builder.md` (W-4), so the whole team can review them:
a fixed FastAPI + SQLite layout, safe SQL, plain-English endpoint summaries, a complete worked example, and the rule to build
exactly the approved endpoints with tests. In a live check, Gemini built a Bookshop API whose 8 tests passed when we re-ran them.

Free models fail in ordinary ways, so the agent is built to recover. The retry loop in `agent/retry.py` (F-4) allows up to three
tries. After failing tests, the next try gets the test output and must first explain what went wrong, then fix it
(self-reflection). A try that writes no files gets a firm reminder, and after a "busy" error we run the tests ourselves before
starting over. On a project with a planted bug, the loop ended `ready`. Inside each try, a busy or hanging Gemini call is now
retried up to five times, with a 90-second limit per call (#29). All model access goes through `agent/llm.py` (D-002), so the
model is a setting: switching `LLM_MODEL` needed no code change (D-4), but other free models were busy, unavailable to new users,
or, in one case, answered without using the tools at all.

### 3.3 Frontend ✍️ (B-3, Perfect)
Facts to use (replace with your paragraph):
- React + Vite + TypeScript `strict`, plain `fetch`, no state library (D-004).
- Design tokens and 13 small components; `/dev/gallery` to see them all.
- API types generated from the backend's schema with `openapi-typescript` (D-015, W-6), so a backend change that breaks the frontend fails the type check.
- Live progress read with a `fetch` stream reader, not `EventSource` (D-016, W-7); explicit loading, error and empty states.

### 3.4 Deployment (B-4, Nana) — draft
The two halves are deployed separately, both on free plans. The frontend is a set of static files on **Vercel**; the backend is a
long-running Python server on **Render**, and it runs the agent too, because the builder is part of the backend program.

Two limits shaped how we deploy. First, Vercel's free plan cannot watch a repository owned by a GitHub organisation, so the
frontend is published from a laptop with Vercel's command-line tool (D-014). We deploy a clean copy of `main` without
git history, because Vercel blocks a deploy whose last commit was written by someone other than the account owner.
Second, Render's free server is small (512 MB of memory, 0.1 of a CPU), sleeps after 15 idle minutes, and has no permanent
disk, so projects reset whenever it restarts.

Secrets never enter the repository. The Gemini key and the model name are typed into Render's settings page; the backend
only accepts browser calls from our Vercel address (CORS); the published frontend was searched for keys and none were found.
We checked each step on the live sites: the backend's `/health` answers, other web addresses are refused, and a build
started online runs the agent (`evidence/deploy/`).

Deploying also showed us real failure cases. Without the model setting, a build stops at once with *"The server has no AI
model set"*, a clear message rather than a crash. On 2026-11-14, Gemini's free tier was busy for every online try, so builds
failed after their retries, with a plain message to the user. ⏳ *To add after D-2 is complete: one Ready build online, the
wake-up time after sleep, and memory use during a build.*

## 4. Evaluation (B-4, Nana) — method drafted, results ⏳

### 4.1 Test set
We wrote **20 synthetic requests** before any run (`evaluation/requests.json`, S-7), in five kinds, so the score is not
inflated by easy cases:
| Kind | Count | Expected behaviour |
|---|---|---|
| Clear, one table | 8 | Build that table with its 5 endpoints and the named fields |
| Several tables | 4 | Build every named table (at least 3) |
| Vague | 4 | Ask questions first, then build at least *N* tables |
| Partly supported | 2 | Build the supported part; list the rest (payments, SMS, logins, photos) as not included |
| Out of scope | 2 | Build nothing and say why (a website; collecting personal data) |

All requests are made up, because the repository is public. Six automatic checks keep the file well-formed.

### 4.2 What counts as a pass
A request passes when (1) the build ends `ready`, (2) its own tests pass, and (3) every expected endpoint exists
(any path-parameter name is accepted, e.g. `{book_id}` for `{id}`). For "ask first" requests the platform must ask before
building; for "refuse" requests it must build nothing. We also record the number of tries and the seconds per build,
and we count free-tier "busy" failures separately from bad code, so a busy model is not mistaken for a bad agent.

A passing test is **not** proof of a good API: the agent writes its own tests, so it can test the wrong thing. Checking the
expected endpoints and fields against the request is our guard against that.

### 4.3 Results ⏳
| | Run 1 (E-2) | Run 2 after fixes (E-4) |
|---|---|---|
| Passed (of 20) | ⏳ | ⏳ |
| By kind (clear / several / vague / partly / out of scope) | ⏳ | ⏳ |
| Average tries per build | ⏳ | ⏳ |
| Average seconds per build | ⏳ | ⏳ |
| Failures from a busy model (not counted against the agent) | ⏳ | ⏳ |

✍️ *Fixes made between the runs (E-3, Opei and Elise): to list after run 1.*

### 4.4 What we learned / limitations (so far)
- The free model is the weakest link: on 2026-11-14 every online build attempt was refused as "busy", and our error message
  does not yet say whether the cause was overload or the daily quota. ✍️ *Update when merged:* a free backup Gemini model
  for the last try (D-018, PR #28) is in review; a paid second provider (issue #30) would need a team decision because of our free-tiers-only rule.
- The free host has no permanent disk, so projects (and, later, live generated APIs, D-011) reset on restart.
- Running AI-written code on a server is a real risk; we limit it with a sandbox, time and output limits, and no secrets, but it is a demo, not production.
- ⏳ *More after E-2 / E-4.*

## 5. Future work
- Plan preview and approval before anything is generated (F-2), zip export (F-5), the live API at a link with Swagger (F-12, F-13).
- A shared database so projects survive restarts (D-013).
- Permanent per-project deployment, payments, scaling, and chatting with the agent during a build (D-011, D-012), which are out of scope for a free, four-week project.
