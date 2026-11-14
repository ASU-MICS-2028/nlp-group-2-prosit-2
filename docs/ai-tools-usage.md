# AI tools usage log

One line per use. Add a line in the same PR as the work. Say how you checked the output.

| Date | Who | Tool | What it was used for | How it was checked |
|---|---|---|---|---|
| 2026-10-26 | Perfect | Claude Code | Drafted the repo scaffold (README, PLAN, CONTRIBUTING, AGENTS, docs, CI) | Read every file; edited for the team's real roles and deadlines |
| 2026-11-02 | Perfect | Claude Code | Built the frontend skeleton, design tokens, 13 components, `/dev/gallery`, Start screen and tests | Ran lint, typecheck, tests and build; reviewed the screenshots against the reference and corrected the design (v0.2) |
| 2026-11-02 | Perfect | Claude Code | Wrote the FastAPI skeleton (S-5), its tests, the API contract draft and the handover docs (D-008, D-009) | Ran `pytest` (9 passed) and a live `curl` against the server; read all files |
| 2026-11-02 | Perfect | Claude Code | Wrote `agent/llm.py` (S-4) and its 18 tests | Ran `pytest` (all pass, fake model only); read the SDK's error object to confirm field names. The real Gemini call was not run |
| 2026-11-03 | Perfect | Claude Code | Reviewed Elise's runner; summarised the lecture transcript; drafted D-010 to D-012 and the PLAN, contract and README updates | Ran Elise's tests and three probes on a clean checkout (secrets leak, home folder read, output size confirmed); decisions confirmed by Perfect before writing |
| 2026-11-03 | Elise | Claude Code | Step-by-step help building the sandbox runner (W-2), its tests, the review fixes (secrets, output limit), and the learnings note | Wrote each test first and watched it fail; ran `python -m pytest` after every step (17 passed); read every line; teammate review on PR #3 |
| 2026-11-04 | Perfect | Claude Code | Ran the live Gemini check (S-4) and wrote and ran the ADK spike (W-10) | Read the output of both runs; the spike's tool call, result and final text matched the script; saved script and output in `evidence/agent/` |
| 2026-11-07 | Opei | Claude Code | Wrote the agent tools `agent/tools.py` (W-1) and their 26 tests | Ran `pytest -q agent backend` (all pass); checked that ADK turns each tool into a correct tool description; read every line |
| 2026-11-08 | Opei | Claude Code | Self-review of W-1: `read_file` now returns whole files (up to 20,000 characters) instead of the last 4,000; drive paths like `C:` refused; 2 tests | Ran `pytest -q` (all pass) |
| 2026-11-08 | Opei | Claude Code | Drafted the builder prompt `agent/prompts/builder.md` (W-4), its loader and 18 tests | Ran `pytest -q` (all pass); the prompt's example project is run through the sandbox runner in a test (9 passed); read the whole prompt. Live check: Gemini built a Bookshop API whose 8 tests passed when we re-ran them ourselves |
| 2026-11-09 | Elise | Claude Code | Step-by-step help building the W-5 endpoints (start, status, live stream), the plain-sentence 422 handler, D-013 and the learnings note | Wrote each test first and watched it fail; ran `python -m pytest` after every step; tried every endpoint by hand in `/docs` and the stream with curl; read every line |
| 2026-11-10 | Nana | Claude Code | Drafted the 20-request evaluation set `evaluation/requests.json` (S-7), its 6 format checks and `learnings/evaluation.md` | Read every request against the builder prompt's endpoint shape; ran `pytest evaluation` (6 passed); all requests are synthetic |
| 2026-11-10 | Nana | Claude Code | Looked up Vercel and Render free-tier limits; wrote `learnings/deployment.md`, `deploy/README.md` and D-014 (S-8, D-1 prep) | Read the official pages (linked in section 9); built the frontend from `main` (609 KB, under the 100 MB upload limit); accounts and the deploy are not done |
| 2026-11-10 | Opei | Claude Code | Ran the D-4 model switch check on the laptop (4 other Gemini models, only `LLM_MODEL` changed) and wrote up the results | Read every output; checked no key or folder path is in the evidence file |
| 2026-11-10 | Elise | Claude Code | Step-by-step help building the W-3 agent loop (`backend/builder.py`), its fake-model tests and five stop rules, the live check script, and the W-5/F-11 review fixes | Wrote each test first and watched it fail; ran `python -m pytest` after every step (99 passed); one real Gemini build ended `ready` and our own test run confirmed it; read every line |
| 2026-11-11 | Elise | Claude Code | Step-by-step help adding W-8 `GET /projects` (timestamps, stand-in names, newest first) and its 3 tests | Wrote the tests first and watched them fail; ran `python -m pytest` (all pass); read every line |
| 2026-11-11 | Elise | Claude Code | Step-by-step help writing the F-1 clarifying-questions prompt (rules and examples drafted from Elise's own bakery questions), `agent/questions.py`, its 7 tests and the live check | Wrote each test first; ran `python -m pytest` (all pass); judged all 5 live answers by hand and changed the off-topic rule after reading them; read every line |
| 2026-11-12 | Perfect | Claude Code | Step-by-step help adding W-6: schema export script, generated API types, the `fetch` client with plain error sentences, and 9 live tests against the real backend | Chose live tests over a fake after the first plan; ran the tests with the backend up and with it down; ran typecheck, lint and format; read every line |
| 2026-11-12 | Perfect | Claude Code | Step-by-step help building W-7: the stream reader, the event parser, the `useBuild` and `useProjectList` hooks, the Start and Build screens, and the tests (without a server, and 15 live ones) | Planned the steps first; chose a `fetch` reader so tests need no fake; ran every test against a real backend, and with it stopped to check they fail; fixed two mistakes in my own tests; read every line |
| 2026-11-12 | Opei | Claude Code | Wrote the F-4 retry / self-reflection loop `agent/retry.py`, its two prompt files, 8 tests, and two small additions to `backend/builder.py` (`start_files`, `kind`, `test_output`) | Ran `pytest -q` (all pass); fixed a fake-AI test bug found while testing; ran the live check twice on a seeded failing project (run 1 ready, run 2 Gemini busy throughout, ended failed as designed); added the "check ourselves after a busy error" rule because of run 1; read every line |
| 2026-11-13 | Nana | Claude Code | Step-by-step help with the first frontend deploy to Vercel (D-1), the `.vercelignore`, and the corrected steps in `deploy/README.md` and `learnings/deployment.md` | Claude ran the deploy from my laptop after I approved it; checked the live URL with curl (200, title "API Builder"); searched the published JavaScript for keys (none); took a screenshot |
| 2026-11-13 | Nana | Claude Code | Render limits (S-8), backend deploy steps, the request to the organisation owner (#25), the D-2 early-run checks, connecting the frontend to the backend, and the docs | I created the Render service and typed the key myself; Claude ran a laptop dry run with Render's start command, then curl checks on the live backend (`/health` 200, CORS) and the live frontend (Render address in the JavaScript, no keys, screenshot) |
| 2026-11-14 | Elise | Claude Code | Step-by-step help with W-9: starting the build in the background from `POST /projects`, the fake-build fixture and 6 tests, the new project fields, reading the first live run's timeline | Wrote the tests first and watched them fail; ran `python -m pytest` (130 pass); ran live builds from the chat screen and checked the timeline by hand; read every line |

## Sign-off
Each person confirms they understand and can explain everything they submitted.

| Person | Signed (date) |
|---|---|
| Perfect | |
| Opei | |
| Elise | |
| Nana | |
