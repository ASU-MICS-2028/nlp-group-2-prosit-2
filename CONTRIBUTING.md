# Contributing

## The rule behind everything
Explain it in plain words. Every teammate must be able to explain every part of the code in the viva.
Write short, plain code. Prefer the boring way. Comment any line that is not obvious.

## Where things go

| Path | What | Lead owner | Backup owner |
|---|---|---|---|
| `backend/` | FastAPI server, agent loop, sandbox runner | Elise | Opei |
| `agent/` | `llm.py`, prompts, tools, retry loop | Opei | Nana |
| `frontend/` | React + TypeScript UI | Perfect | Nana |
| `evaluation/`, `deploy/`, `evidence/` | Test set, scoring, deployment, proof | Nana | anyone |
| `.github/`, root files | Setup, CI, branch protection | Perfect | Nana |
| `docs/` | Decisions (ADRs), AI-use log | everyone | n/a |
| `learnings/` | One note per area | each owner | n/a |
| `knowledge/` | Background and session summaries | everyone | n/a |
| `report/` | Section A per person, Section B shared | each owner / Nana | n/a |

## Ground rules
1. The repo is **public**. Never commit keys, tokens, `.env` files, student IDs, phone numbers, personal emails or real personal data. Use synthetic data only.
2. Secrets live in `.env` (local, git-ignored) and in the host's settings page (Vercel, Render). `.env.example` shows the names only.
3. Do not rewrite history: accepted ADRs, session summaries and recorded evidence are never edited; add a new one.
4. Reuse before writing. Real deadlines beat the syllabus.
5. One PR per branch, cut from an up-to-date `main`. **No stacked PRs.**
6. Every technical term gets a one-line explanation (in learnings notes, and in comments where needed).

## Flow
1. `git switch main && git pull`, then `git switch -c <area>/<short-topic>` (e.g. `backend/sandbox-runner`).
2. Make small commits. Commit style: imperative and scoped, e.g. `backend: add sandbox timeout`.
3. Open a PR with the template filled in. CI must pass.
4. **One teammate approves** (not the author). Any teammate can approve.
5. Squash-merge. Delete the branch.

(The very first scaffold commit is pushed straight to `main` by Perfect, before branch protection is turned on.)

## Definition of Done (also the PR template)
- [ ] The task ID from PLAN.md is in the PR title; its row is flipped, and tasks it unblocks are flipped from ⛔ to 🟢.
- [ ] README "Pending now" table updated.
- [ ] Code is plain and the author can explain every line.
- [ ] Tests exist, including bad input, repeats, service down and permission-denied cases. Say what could not be tested.
- [ ] `learnings/<area>.md` updated in simple words.
- [ ] Decisions recorded in `docs/decisions.md`.
- [ ] Evidence captured if the task is on the deliverables checklist.
- [ ] AI use logged in `docs/ai-tools-usage.md`.
- [ ] No secrets in the diff.

## Branch protection (Perfect sets these on `main`, task S-2)
- Require a pull request before merging; **1 approval**; dismiss stale approvals on new commits.
- Require status checks to pass (the `python` and `frontend` CI jobs) and require the branch to be up to date.
- Do **not** require code-owner review (CODEOWNERS lists everyone, but one approval from any teammate is enough).
- Block direct pushes to `main`; allow squash merging only; delete branches on merge.

## Report writing
Nana assembles the report, but each owner writes the paragraph about their own area. Section A is written
individually by each person. Do not quote results before they are measured; leave "to fill after the test".
