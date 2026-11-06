# 2026-11-03: Lecture notes and decisions

**Goal:** Check our plan against what the lecturer said about the prosit, and settle the open decisions.

**What the lecture said (summary, not the transcript):**
- The front end sends the request to a backend endpoint; the backend hands it to an agent. The agent can live in the same code base as the backend or run as a separate service. Either way, the front end should not talk to the agent directly; the backend sits in between.
- The language model is only a brain. It cannot write files, run code or start a database, so the agent needs tools. MCP is a standard way to plug in outside tools (his example: Supabase).
- The agent is a loop: plan the endpoints, write code, write it to a file, run it, test it, fix it, repeat until it works. It should keep working and accept follow-up messages ("don't add that endpoint").
- The result he expects is a working backend with all its methods, given back as a link where requests can be made. Swagger docs were the example. A non-developer must be able to call it.
- He suggested using a framework for the agent (LangGraph, or a Google one that sounds like ADK; the transcript is garbled). Multi-agent or single agent is our choice. Deploying everything is preferred over local demos, using free services.
- HTTP is stateless: the backend does not remember between requests, so state must be kept somewhere.
- The lecture did not mention training or tuning a model. The submission date was only described as "next week".

**What we decided (see `docs/decisions.md`):**
- D-010: build the agent with Google ADK, starting with a spike (W-10).
- D-011: each generated API runs live behind our backend at `/apis/{id}`; the zip is a take-home; data resets when the free host restarts.
- D-012: follow-up requests only after a build, if time.
- Scope stays inside the prosit: no model training or tuning, no paid services, no per-project deployments.

**What changed:** PLAN.md (new tasks W-10, F-12 to F-15; W-1, W-3, W-4 reworded; W-2 done; scope and risks updated), `docs/api-contract.md` (live API endpoints), README table.

**Open questions / next steps:**
- Perfect: Gemini API key and live check (S-4), then the ADK spike (W-10).
- Elise: runner security fixes (F-11), and whether she takes W-3 or W-5.
- Confirm the real submission date.
