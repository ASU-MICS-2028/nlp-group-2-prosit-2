# AI tools usage log

One line per use. Add a line in the same PR as the work. Say how you checked the output.

| Date | Who | Tool | What it was used for | How it was checked |
|---|---|---|---|---|
| 2026-10-26 | Perfect | Claude Code | Drafted the repo scaffold (README, PLAN, CONTRIBUTING, AGENTS, docs, CI) | Read every file; edited for the team's real roles and deadlines |
| 2026-11-02 | Perfect | Claude Code | Built the frontend skeleton, design tokens, 13 components, `/dev/gallery`, Start screen and tests | Ran lint, typecheck, tests and build; reviewed the screenshots against the reference and corrected the design (v0.2) |
| 2026-11-02 | Perfect | Claude Code | Wrote the FastAPI skeleton (S-5), its tests, the API contract draft and the handover docs (D-008, D-009) | Ran `pytest` (9 passed) and a live `curl` against the server; read all files |
| 2026-11-02 | Perfect | Claude Code | Wrote `agent/llm.py` (S-4) and its 18 tests | Ran `pytest` (all pass, fake model only); read the SDK's error object to confirm field names. The real Gemini call was not run |
| 2026-11-03 | Perfect | Claude Code | Reviewed Elise's runner; summarised the lecture transcript; drafted D-010 to D-012 and the PLAN, contract and README updates | Ran Elise's tests and three probes on a clean checkout (secrets leak, home folder read, output size confirmed); decisions confirmed by Perfect before writing |
| 2026-11-04 | Perfect | Claude Code | Ran the live Gemini check (S-4) and wrote and ran the ADK spike (W-10) | Read the output of both runs; the spike's tool call, result and final text matched the script; saved script and output in `evidence/agent/` |
| 2026-11-08 | Opei | Claude Code | Drafted the builder prompt `agent/prompts/builder.md` (W-4), its loader and 18 tests | Ran `pytest -q` (all pass); the prompt's example project is run through the sandbox runner in a test (9 passed); read the whole prompt |

## Sign-off
Each person confirms they understand and can explain everything they submitted.

| Person | Signed (date) |
|---|---|
| Perfect | |
| Opei | |
| Elise | |
| Nana | |
