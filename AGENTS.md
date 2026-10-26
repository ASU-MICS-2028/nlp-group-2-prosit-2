# Instructions for coding assistants

You are helping a student team (four people, new to this) build a backend-API builder for non-developers.
The humans must be able to defend every line in a live viva. Optimise for **understanding**, not cleverness.

## Read order, every task
1. `README.md` (current stage) → 2. `PLAN.md` (task, owner, blockers, done-when) → 3. `docs/decisions.md`
→ 4. the area's `AGENTS.md` and `learnings/` note → 5. `knowledge/`.
If the task is not in PLAN.md, or its blockers are not ✅, say so before doing anything.

## How to work, for every task
1. Plan in small steps.
2. Explain each step in plain words **before** doing it.
3. Test each step, including failure paths: normal input; bad, missing or oversized input; repeats and races;
   failures around it (LLM down, rate limit, network drop, permission denied, timeout); undo. Say which you tried and what
   happened. Say plainly what could not be tested. Never claim a test passed without running it.
4. Capture evidence as you go (`tee` terminal output, screenshots) into `evidence/`.
5. Update the area's `learnings/` note in the simplest words.
6. Record decisions in `docs/decisions.md`.
7. Close the loop in the same PR: PLAN.md row, README table, session summary, AI-use line.

## Code style (plain code)
- Python: short functions, type hints, clear names, no metaprogramming, no clever one-liners. Tests with pytest.
- TypeScript: `strict` mode, no `any`, small components with one job, API calls in hooks, explicit loading, error and empty states.
  No state libraries unless an ADR says so.
- Comment the "why" on any line a classmate might not understand.
- Explain every technical term in one line in the learnings note.

## Where everything goes

| Thing | Place |
|---|---|
| Current stage and who can start now | `README.md` (current stage only) |
| Every task, owner, blocker | `PLAN.md` |
| Decisions | `docs/decisions.md` |
| What someone did and how to check it | `learnings/<area>.md` |
| Background, brief, grading | `knowledge/` |
| Session summaries (never transcripts) | `knowledge/sessions/` |
| Proof for graded items | `evidence/` |
| Report text | `report/` |

## Rules
- The repo is **public**: no secrets, keys, tokens, `.env`, student IDs, phone numbers, personal emails or real personal data.
- Don't edit history: accepted ADRs, evidence and session summaries are not rewritten; add a new one.
- LLM access goes only through `agent/llm.py`, so the provider (Gemini now, Claude later) can change in one place.
- Free tiers only. Do not add any paid service or dependency.
- Reuse before writing. One PR per branch; no stacked PRs.
- Real deadlines beat the syllabus: the prosit is due Sun 1 Nov 2026; presentation and viva come after.

## Ask first
Ask before anything outward-facing or hard to undo: deploying, deleting data, merging PRs, changing repo settings, sending messages.
**Never commit, push or open a PR unless the person asked for exactly that.** Show the changes and wait for agreement.

## Accountability
Each area has one owner. Everyone else relies on that owner's learnings note. A PR that leaves the team guessing is not finished.
