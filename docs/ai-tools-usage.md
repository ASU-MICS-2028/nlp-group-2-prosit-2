# AI tools usage log

One line per use. Add a line in the same PR as the work. Say how you checked the output.

| Date | Who | Tool | What it was used for | How it was checked |
|---|---|---|---|---|
| 2026-10-26 | Perfect | Claude Code | Drafted the repo scaffold (README, PLAN, CONTRIBUTING, AGENTS, docs, CI) | Read every file; edited for the team's real roles and deadlines |
| 2026-11-02 | Perfect | Claude Code | Built the frontend skeleton, design tokens, 13 components, `/dev/gallery`, Start screen and tests | Ran lint, typecheck, tests and build; reviewed the screenshots against the reference and corrected the design (v0.2) |
| 2026-11-02 | Perfect | Claude Code | Wrote the FastAPI skeleton (S-5), its tests, the API contract draft and the handover docs (D-008, D-009) | Ran `pytest` (9 passed) and a live `curl` against the server; read all files |
| 2026-11-03 | Elise | Claude Code | Step-by-step help building the sandbox runner (W-2), its tests, the review fixes (secrets, output limit), and the learnings note | Wrote each test first and watched it fail; ran `python -m pytest` after every step (17 passed); read every line; teammate review on PR #3 |

## Sign-off
Each person confirms they understand and can explain everything they submitted.

| Person | Signed (date) |
|---|---|
| Perfect | |
| Opei | |
| Elise | |
| Nana | |
