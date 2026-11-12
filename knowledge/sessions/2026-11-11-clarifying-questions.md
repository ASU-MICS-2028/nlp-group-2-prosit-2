# 2026-11-11: Clarifying questions (F-1)

**Goal:** Before planning, let the AI ask the person up to 3 plain questions about anything unclear in their request.

**What we found:**
- Good questions change what gets built (what to store, which details, which actions). Questions about the future or things we can't build (payments) don't.
- The AI copies examples closely, so examples must obey the rules (a first draft had an "Other"-style option, which broke our own rule).
- Gemini can wrap JSON in a ```json fence and can send too many questions or miss parts, so the answer is checked in code.
- Gemini `503` ("too busy") reaches the person as "The model returned an error (code 503)", because `llm.py` retries only `429`.

**What we decided:**
- Instructions in `agent/prompts/questions.md`; checking in `agent/questions.py`; one plain `QuestionsError` for any unusable answer.
- More than 3 questions: keep the first 3. Missing parts: refuse.
- Off-topic requests: say plainly what we can't make and what we can (Elise's change after the first live run).
- The 503 fix stays with Opei (`llm.py` is his area); flagged to him.
- Elise takes W-8 (`GET /projects`) from Perfect (Handovers table in PLAN.md).

**What changed:** `agent/prompts/questions.md`, `agent/questions.py`, `agent/tests/test_questions.py` (7 tests),
`evidence/agent/f1_live_check.py` and output, F-1 section in `learnings/agent.md`, PLAN (F-1 ✅), README table.

**Open questions / next steps:**
- F-2: call `ask_questions` from `POST /projects`, then answers → plan → approve. Whether F-2 can start before W-9 is still to agree with the team.
- Opei: treat 503 like 429 in `llm.py`.
