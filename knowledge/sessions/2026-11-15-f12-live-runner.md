# 2026-11-15 · F-12 live runner, taken from Elise

Who: Nana, with Claude Code.

## Goal
Run a finished project as its own server so it can really be called (D-011), within the free server's limits. F-13 then puts it behind `/apis/{id}/...`.

## What we found
- The example project keeps its data in `app.db` inside its own folder, so each live API's data lasts while it runs and disappears when it stops, as the contract says.
- A pipe that nobody reads fills up and freezes the program, so the live API's log goes to `DEVNULL`.
- On Windows, a running process keeps its files locked: the folder can only be deleted after the process has ended.
- On Windows a venv's `python.exe` is a 5 MB launcher that starts the real Python (about **50 MB** per live API). Stopping ends both. Render runs Linux, so there is no launcher there.
- While writing a test we found a leak: a crashed API's folder was not deleted when it was started again. Fixed, with a test.

## What we decided
- Limit 3 at once; one more stops the **least recently used**; idle 10 minutes; start timeout 30 s. These are starting values, to be checked on Render.
- One shared `minimal_environment()` for the test runner and the live runner, so "no key for AI code" is one rule in one place.
- A lock, so two starts at the same moment can't go over the limit.

## What changed
- `backend/live.py`, `backend/runner.py` (`minimal_environment`), 13 tests in `backend/tests/test_live.py`, `evidence/backend/outputs_f12_live_runner.txt`.
- PLAN: F-12 ✅, F-13 🟢, handover row; README rows; `learnings/backend.md` (F-12 part); AI-use line.

## Open questions / next steps
- F-13: `/apis/{id}/...` pass-through, `POST /projects/{id}/wake`, `api_url` and `live_status`; call `touch` and `stop_idle`.
- Memory on Render with 3 live APIs plus a build: read the Metrics tab after F-13.
