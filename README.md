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

Last updated: 2026-11-15. Stage: **Phase 4, Writing and handing in**. The walking skeleton is done: a request typed in the web page
starts a real build (agent with retries and a backup model), and the page shows its progress live in plain words (W-9, F-4, F-16, F-17).
The server hands over the finished project as a zip (F-5) and starts it as a live API at a link (F-12, F-13). The ready screen shows the facts, the link to the API's
Swagger page, "Wake it up" and the download button (F-7, F-14; the check in a real browser is still to do). The frontend and backend are deployed (Vercel and Render).
Not built (so the report must not claim them): plan preview and approval (F-2, F-3).
Evaluation numbers wait for E-2 and E-4; the free Gemini quota limits those runs.
Tasks that stall get picked up by someone else (D-009); see Handovers in PLAN.md.
Deadline for the prosit deliverables (code, report, slides): **Sun 15 Nov 2026** (moved from Sun 1 Nov). Presentation and viva come after (dates ❓).

| Person | Now (can start today) | Next (waiting on) |
|---|---|---|
| **Perfect** | F-7 and F-14 are built: click them in a browser, keyboard walkthrough, screenshots; A-3 Section A; B-3 frontend paragraph (slot in the Section B draft, PR #32); R-6 final repo check; S-2 branch protection and S-3 collaborators | R-4 teach-back |
| **Opei** | A-2 Section A; B-2 agent, prompts and LLM paragraph (in `report/section-b.md`); F-6 Dockerfile + run instructions for the zip (F-5 is done) | E-3 fix the top failures (E-2) |
| **Elise** | A-1 Section A; B-1 backend paragraph; R-1 architecture diagram (F-5, F-12 and F-13 handed to Nana 2026-11-15) | F-2 plan + approval is not started |
| **Nana** | F-18 stop a running build (D-022, agreed with Perfect): built and checked locally, then PR and redeploy; (F-5 zip download, F-12 live runner and F-13 live link done 2026-11-15, from Elise; D-2 done 2026-11-15: first online build ready); E-1 live run once the quota resets; A-4 Section A; B-5 assemble Section B, R-2 report PDF, R-3 slides, R-5 Canvas upload | E-2 and E-4 evaluation runs |

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
