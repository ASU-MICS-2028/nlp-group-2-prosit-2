# Decisions

## D-001: Frontend and backend are separate programs that talk only through an API
Date: 2026-10-26 · Status: Proposed
Affects: Elise, Perfect
Decision: The React UI never imports backend code. It calls the FastAPI server through its OpenAPI schema, and a typed TypeScript client is generated from that schema.
Why: This is Mesora's stated principle (separation of concerns). The generated client turns a backend change that breaks the UI into a build error instead of a demo-day surprise.
Gave up: A single-folder app would be quicker to start but would not follow the brief.

## D-002: All LLM calls go through `agent/llm.py`; Gemini free tier now, Claude later
Date: 2026-10-26 · Status: Proposed
Affects: Opei (owns), everyone who calls the model
Decision: One file wraps the provider. `LLM_PROVIDER` and `LLM_MODEL` in `.env` choose which one runs. Start with the Gemini free tier. Add Claude when the team has credits.
Why: No budget. Free tiers change, so the switch must be one place. D-4 in PLAN.md proves the switch works.
Gave up: Free-tier rate limits and weaker code quality than a paid model.

## D-003: Hosting: frontend on Vercel, backend on Render (or Hugging Face Spaces), generated APIs delivered as a zip
Date: 2026-10-26 · Status: Proposed
Affects: Nana (owns), Elise, Perfect
Decision: Free tiers only. Users receive their generated API as a zip with a Dockerfile instead of us hosting it. Backend host is kept swappable (config in `deploy/`).
Why: Vercel serverless has no persistent disk and short time limits, which does not suit an agent that writes files and runs tests. Hosting users' APIs live would cost money.
Gave up: The backend sleeps when idle on free tiers (slow first request). No one-click live API for the user.

## D-004: Frontend uses React + Vite + TypeScript (strict), plain `fetch`, no state library
Date: 2026-10-26 · Status: Proposed
Affects: Perfect, Nana
Decision: React + Vite + TypeScript with `strict`, ESLint, Prettier, Vitest + Testing Library, a generated API client, SSE for live progress.
Why: Standard best practice, easy to explain, strong type safety.
Gave up: Heavier tools (Redux, Next.js) that would be harder for everyone to explain in the viva.

## D-005: Generated APIs use FastAPI + SQLite + pytest
Date: 2026-10-26 · Status: Proposed
Affects: Elise, Opei
Decision: Every generated project is plain FastAPI with SQLite storage and pytest tests, in a fixed folder layout the agent is told to follow.
Why: A fixed, small target makes the LLM's output more reliable and the tests easy to run. FastAPI gives OpenAPI docs for free.
Gave up: Other languages and databases.

## D-006: Plain-code rule
Date: 2026-10-26 · Status: Proposed
Affects: everyone
Decision: Short functions, clear names, comments on non-obvious lines, no clever tricks. Every member must be able to explain all the code.
Why: The viva is individual and covers all the code.
Gave up: Some speed and elegance.

## D-007: Generated code runs in a temporary folder with a timeout and size limits
Date: 2026-10-26 · Status: Proposed
Affects: Elise
Decision: The sandbox runner copies generated files to a temp folder, runs pytest with a time limit, and caps input and output size. It is a demo sandbox, not production-grade isolation, and the report says so.
Why: LLM-written code is untrusted. Full isolation (containers) is out of scope for one week.
Gave up: Strong isolation guarantees.
