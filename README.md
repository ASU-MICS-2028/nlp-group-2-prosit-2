# NLP Group 2: PROSIT 2: A Backend API Builder for Non-Developers

Repo: https://github.com/ASU-MICS-2028/nlp-group-2-prosit-2
Course: ICS554 Natural Language Processing, Master's in Intelligent Computing Systems (Ashesi)
Team: Perfect, Opei, Elise, Nana

## What this is

Mesora (an AI lab in Ghana) wants a platform where **someone who cannot code describes an API in plain
English and gets a working, tested backend API**. It is "Lovable or Replit, but for backend APIs".
Underneath it is a coding agent: it asks questions, shows a plan, waits for approval, writes a FastAPI
project, runs its own tests, fixes failures, and hands over a downloadable zip.
The frontend and backend are separate programs that talk only through an API.

## The one rule

**Everyone must be able to explain every part of this project in plain words.** The viva quiz is
individual and covers all the code. If you cannot explain it, it is not finished.
Code is kept short and plain on purpose. See [CONTRIBUTING.md](CONTRIBUTING.md) and [AGENTS.md](AGENTS.md).

## Pending now

Last updated: 2026-10-26 (Mon). Stage: **Phase 0, Setup**.
Critical path: S-1 scaffold → S-5 backend skeleton → W-2/W-5 → W-9 first end-to-end → features → evaluation → report.
Deadline for the prosit deliverables (code, report, slides): **Sun 1 Nov 2026**. Presentation and viva come after (dates ❓).

| Person | Now (can start today) | Next (waiting on) |
|---|---|---|
| **Perfect** | S-1 push scaffold to `main`, S-2 branch protection, S-3 check CODEOWNERS handles and add everyone as collaborators, A-3 Section A draft | S-6 frontend skeleton (S-1) |
| **Opei** | S-4 Gemini key + `llm.py` hello world, A-2 Section A draft | W-1 tools, W-4 system prompt (S-4) |
| **Elise** | A-1 Section A draft | S-5 FastAPI skeleton (S-1), W-2 sandbox runner (S-5) |
| **Nana** | S-8 Vercel and Render accounts, A-4 Section A draft | S-7 evaluation set (S-1) |

Full task list, owners and blockers: [PLAN.md](PLAN.md). Rows leave this table once they are finished.

## Where things are

| Folder | What | Owner |
|---|---|---|
| `backend/` | FastAPI platform server, agent loop, sandbox runner | Elise |
| `agent/` | `llm.py`, prompts, tools, retry/reflection | Opei |
| `frontend/` | React + TypeScript web UI | Perfect |
| `evaluation/`, `deploy/` | 20-request test set, scoring, deployment config | Nana |
| `docs/` | Decisions (ADRs), AI-use log | everyone |
| `learnings/` | One note per area: what was done and how to check it | each owner |
| `knowledge/` | Background, brief, session summaries | everyone |
| `evidence/` | Proof for graded deliverables | Nana |
| `report/` | Section A (per person) and Section B (shared) | each owner / Nana |
