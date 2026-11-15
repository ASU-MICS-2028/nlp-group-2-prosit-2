# 2026-11-15 · First online build, and the real cause of the "busy" failures (D-2)

Who: Nana, with Claude Code.

## Goal
Find out why builds worked on the laptop but failed online, then finish D-2.

## What we found
- **Local run problems** were about how the server was started, not the code:
  - plain `uvicorn` on Windows is the global Python's, which has no Google packages, so the server crashed with `No module named 'google'`;
  - without `--env-file .env`, the server never reads `.env`, so builds stop with "The server has no AI model set".
- **Online failures were the free quota, not "busy".** Render's Logs showed `429 RESOURCE_EXHAUSTED`. The free tier allows 20 requests per day, per Google project, per model, and one build uses about 10-20 of them.
- The app shows every Gemini error as "The AI service is busy" (`backend/builder.py`), so the code was only visible in the logs.
- Render asked for `gemini-3.4-flash` and the laptop for `gemini-3.5-flash`, but Google counted both against `gemini-3.6-flash`'s quota. So a new model name gives no fresh quota; only a key in another Google project does.

## What we decided
- Render gets **its own Gemini key** in a separate Google project, so laptop testing no longer uses up the live site's quota (Nana made it).
- Keep `LLM_MODEL=gemini-3.5-flash`, the model all our checks used.
- On demo day: one warm-up build early, then nothing until the demo.

## What changed
- First online build ended **ready**: a to-do list API, 9 of 9 tests (`evidence/deploy/outputs_backend_ready_build.txt`). D-2 ✅, D-3 and E-1 🟢.
- Evidence of the quota failure: `evidence/deploy/outputs_backend_build3.txt`, `outputs_backend_build4_quota.txt`.
- `learnings/deployment.md` (quota, own key, Windows run commands, wake-up time), `deploy/README.md` (env table, how to read a "busy" failure), PLAN, README, AI-use log.

## Open questions / next steps
- Suggested to Opei: don't retry a per-day 429. Suggested to Elise: say "today's free AI limit is used up" instead of "busy".
- E-1/E-2: 20 requests × 10-20 calls each will not fit in one day's free quota. The evaluation must be spread over days or models.
- Memory during a build (Render's Metrics tab) is still to be read.
