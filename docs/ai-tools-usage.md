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
| 2026-11-11 | Elise | Claude Code | Step-by-step help adding W-8 `GET /projects` (timestamps, stand-in names, newest first) and its 3 tests | Wrote the tests first and watched them fail; ran `python -m pytest` (all pass); read every line |

## Sign-off
Each person confirms they understand and can explain everything they submitted.

| Person | Signed (date) |
|---|---|
| Perfect | |
| Opei | |
| Elise | |
| Nana | |
