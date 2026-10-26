# agent/ (Opei, backup owner: Nana)

`llm.py` (the only door to the model), prompts, tool definitions, and the retry/reflection step.

## Commands (fill in as it lands, S-4)
- Hello world: `python -m agent.llm`
- Test: `pytest agent`

## Traps this area enforces
- `llm.py` reads `LLM_PROVIDER`, `LLM_MODEL` and the API key from the environment. Nothing else imports a provider library (D-002).
- Free-tier rate limits: retry with waiting and a maximum number of tries; fail with a clear message.
- Prompts live in files (`agent/prompts/`), not buried in code, so the team can read and review them.
- Tool results sent back to the model are trimmed to a size limit.
- Never put keys or user data in prompts files or tests.

## Every feature needs tests for
Valid model reply · malformed reply (not the format we asked for) · rate limit / network error · empty reply · tool failing · max retries reached.
Tests use a fake model, not the real API.
