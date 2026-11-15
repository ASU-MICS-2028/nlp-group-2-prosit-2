# 2026-11-15 · F-5 zip download, taken from Elise

Who: Nana, with Claude Code.

## Goal
Elise is busy, so Nana takes the download (F-5), the live runner (F-12) and the live link (F-13), agreed with Elise first (D-009). This session does F-5.

## What we found
- The generated files are already kept in memory after a build (`results` in `backend/projects.py`), so the zip needs no new storage.
- The agent's `write_file` tool already refuses unsafe file names (`clean_path` in `agent/tools.py`), so unzipping the download cannot write outside its folder.
- Opei's timing test `test_builder_model_cuts_a_hanging_call_and_sends_it_again` sometimes misses its 1.9 s limit by a few milliseconds when the whole suite runs; it passes alone.

## What we decided
- Only a **ready** project can be downloaded (`409` otherwise), as the contract says: a failed build's tests fail.
- The zip is made in memory, not in a temp file.
- Order for the rest: F-12, then F-13, one PR each.

## What changed
- `GET /projects/{id}/download`, 5 tests (written first; all 5 failed before the code), `evidence/backend/outputs_f5_download.txt`.
- PLAN: F-5 ✅; F-5, F-12 and F-13 now "Nana (from Elise)"; a Handovers row. README rows, `learnings/backend.md` (F-5 part), AI-use line.

## Open questions / next steps
- Not tried on a real Gemini-built project yet (quota used up today).
- F-12: memory on Render's 512 MB with up to 3 live APIs must be measured; the limit may drop to 1.
