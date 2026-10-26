# 2026-10-26: Project setup

**Goal:** Turn the PROSIT 2 brief into a repo where every member owns something and can explain everything.

**What we found:** The brief has no functional spec, so we define scope ourselves. Section A (18 topics) is large for 3–5 pages.
The viva (individual, 35%) covers all the code.

**What we decided (proposed, see `docs/decisions.md`):**
- Roles: Elise backend, Opei prompts/LLM, Perfect frontend + repo setup, Nana deployment/evaluation/docs. Backup owners set in PLAN.md.
- Gemini free tier behind `agent/llm.py` (Claude later). Vercel (frontend) + Render (backend); generated APIs delivered as zips.
- React + TypeScript (strict) frontend with a generated API client.
- Prosit due Sun 1 Nov 2026; presentation and viva after (dates unknown).

**What changed:** Repo cloned over SSH; scaffold written.

**Open questions / next steps:**
- GitHub handles are now in CODEOWNERS; teammates still need collaborator access (S-3).
- Presentation and viva dates (P-1, V-1).
- Perfect pushes the scaffold to `main`, then turns on branch protection (S-1, S-2).
