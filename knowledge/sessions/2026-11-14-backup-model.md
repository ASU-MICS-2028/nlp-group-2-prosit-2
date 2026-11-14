# 2026-11-14: Backup model when Gemini is busy (F-16, D-018)

**Goal:** Stop losing builds to a busy free tier ("503 busy", "429 too many requests").

**What we found:** ADK has `FallbackModel`, but it switches on every busy reply. Of five other Gemini models, two made a tool call quickly (`gemini-3-flash-preview`, `gemini-3.1-flash-lite`); the rest were slow, out of quota or erroring.

**What we decided (Elise):** the main model keeps 3 tries; if all 3 were busy, a 4th "last shot" runs on `LLM_BACKUP_MODEL`. `MAX_ATTEMPTS` is now 4. Written in our retry loop, not with `FallbackModel`.

**What changed:** `agent/llm.py`, `agent/retry.py`, `backend/projects.py`, tests in `agent/tests/` and `backend/tests/`, `.env.example`, D-018, PLAN F-16, `learnings/agent.md`.

**Open questions / next steps:** Opei to confirm D-018 (his loop). Perfect: the screen now says "of 4". A second provider (Groq or OpenRouter) as a backup outside Google is future work.
