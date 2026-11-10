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

Last updated: 2026-11-10. Stage: **Phase 1, Walking skeleton** (frontend, backend skeleton, sandbox runner and LLM wrapper are on `main`).
Gemini key and ADK spike are done (S-4, W-10). Critical path: W-1 tools + W-4 instructions → W-3 agent → W-5 endpoints → W-9 first end-to-end → live API (F-12, F-13) → evaluation → report.
New decisions (D-010 to D-012): agent built with Google ADK; each generated API runs live at a stable link; follow-ups only after a build.
Runner security fixes are done (F-11), so the live runner (F-12) can start.
Tasks that stall get picked up by someone else (D-009); see Handovers in PLAN.md.
Deadline for the prosit deliverables (code, report, slides): **Sun 1 Nov 2026**. Presentation and viva come after (dates ❓).

| Person | Now (can start today) | Next (waiting on) |
|---|---|---|
| **Perfect** | S-2 branch protection, S-3 collaborators, W-6 typed API client (W-5 endpoints done), W-8 `GET /projects`, A-3 Section A draft | W-7 chat screen (W-6), F-14 live Ready screen |
| **Opei** | A-2 Section A draft (W-4 done 2026-11-08, D-4 done 2026-11-10) | F-4 (W-9), F-6 (F-5) |
| **Elise** | A-1 Section A draft; W-3 agent loop with ADK (W-1 tools are ready); F-1 clarifying-questions prompt (W-4 done); F-12 live runner (F-11 runner security fixes done) | F-13 live API (F-12) |
| **Nana** | S-7 evaluation set, S-8 Vercel and Render accounts, D-1 deploy frontend to Vercel, A-4 Section A draft | E-1 scoring script (W-9) |

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
