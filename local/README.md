# local/ (Nana's sandbox, for reference only: do not merge)

A sandbox for trying team components against Nana's older prototype backend.
It is shared on the branch `dont-merge` (draft PR) so the team can read it; it is **not** part of the team project.
It uses OpenAI (paid), so it does not follow the team's "free tiers only" rule (`agent/llm.py`, Gemini).

Never pushed (see `local/.gitignore`): `prototype-backend/data/` (accounts database, embedding model),
`prototype-backend/generated/` (built projects contain real keys in `.env`), `.venv/`, `node_modules/`, any `.env`.
Setup after cloning: create the venv and install `requirements.txt`, run `npm ci` in `prototype-frontend/`,
download the embedding model (command below), and put `OPENAI_API_KEY` in `coding_agent/.env` next to the repo
folder, or set `PROTOTYPE_ENV_FILE` to another file.

| Folder | What | Start it |
|---|---|---|
| `prototype-backend/` | Copy of `coding_agent/backend` (FastAPI + OpenAI). No `.env` copied: `run.ps1` reads the key from `coding_agent/.env` | `.\local\prototype-backend\run.ps1` → http://localhost:8001/docs |
| `prototype-frontend/` | Copy of the team `frontend/` plus `src/prototype/` (adapter + hook) and a wired `App.tsx` | `npm run dev --prefix local/prototype-frontend` → http://localhost:5173 |

Design of storage, login and roles (built) and memory and RAG (planned): [`design-doc.md`](design-doc.md).

## Accounts (since 2026-11-03, steps 1–2)
- Everything except `/health` needs a login. Open the app, choose "Create an account instead", then log in.
- Make yourself an admin (sees all projects and the demand log, no daily limit), from `local/prototype-backend/`:
  `.venv\Scripts\python -m app.make_admin you@example.com` (and `... you@example.com user` to undo).
- Data lives in `local/prototype-backend/data/builder.db` (accounts, sessions, builds). Delete the file to start empty.
- **Restart the backend after pulling these changes**: a server started before them still runs the old code.

## Generated APIs (since 2026-11-03, step 3)
- Every downloaded API has its own two keys in its `.env` file: `EDITOR_KEY` (look and change; keep private) and `READER_KEY` (look only; can be shared). There is no `demo-api-key` any more.
- APIs downloaded **before** step 3 still use `demo-api-key`. Build them again to get real keys.

## Memory and similar designs (since 2026-11-03, steps 4–5)
- After you approve a plan, the builder notes up to 3 lasting facts about you (e.g. "Uses GHS for prices") and keeps the design. Your next requests use them; the plan says "I used …".
- See and delete what it remembers on the start screen ("What I remember about you"). Nothing is shared with other accounts.
- Switch off with `MEMORY_ENABLED=false` / `RAG_ENABLED=false` in the environment. Measure retrieval: `.venv\Scripts\python -m app.rag_check`.

## Sidebar, build timeline and refresh (since 2026-11-03)
- The sidebar lists your projects (newest first) with a status and "Just now / Yesterday"; click one to reopen it.
- Every build runs the generated project's own 11 tests; the timeline shows Thinking / Doing / Result steps and the real pass/fail bar.
- The open project is kept in the address (`#project=…`): refreshing the page, even after a download, reopens it.
- If OpenAI is down during a build, the OpenAPI file and README now fall back to their templates instead of failing the build.
- Evidence: `evidence/live_check_timeline_projects.txt` (a real build over HTTP with a fake key: 11 of 11 passed).

## Several linked record types and more questions (since 2026-11-04)
- A design can have 1–8 record types (e.g. a school: teachers, classrooms, students, exams, exam results, attendance). A detail can be a **link** (`classroom_id` → one classroom).
- Generated APIs check links: a link to a missing record is refused (422), a record still linked to cannot be deleted (409), and lists can be filtered (`/students?classroom_id=3`).
- Checks per project: 6 for keys and roles + 5 per record type + 3 per link (a 6-type school: 54).
- Vague requests get 5–8 questions (record types, connections, key details, dates, money, status values, who may change data). If the model asks fewer, it is asked once more.
- Evidence: `evidence/screens/7-…11-*.png`, `evidence/backend_tests_multi_record.txt`, `evidence/frontend_tests_multi_record.txt`, `evidence/rag_check_multi.txt`.

## Meaning-based retrieval (since 2026-11-04)
- Similar designs are found with a small free embedding model (model2vec `potion-base-8M`, ~30 MB, CPU only), stored in `prototype-backend/data/embedding-model`. Without that folder, retrieval falls back to word matching (TF-IDF).
- Download it once (needs internet), from `prototype-backend/`:
  `.venv\Scripts\python -c "from model2vec import StaticModel; StaticModel.from_pretrained('minishlab/potion-base-8M').save_pretrained('data/embedding-model')"`
- Measured (`evidence/rag_check_embeddings.txt`): held-out set 20 of 21 right, 0 wrong, 1 of 5 unrelated wrongly matched (TF-IDF: 11 of 21, 1 wrong, 0 of 5).
- Repeated project names in the sidebar are numbered: "School Management API (2)".

## Live check with the real model (2026-11-04, with permission, 21 OpenAI calls)
- `.venv\Scripts\python -m app.live_eval` shows the plan and spends nothing; add `--yes` to run it (needs the key in the environment).
- Result (`evidence/live_eval_2026-11-04.json`, `evidence/live_eval_output.txt`): 21 of 21 checks passed. Both school requests got 7 linked record types; vague requests got 5–7 questions; every built API passed all its own tests (62, 56, 35, 38, 11).
- Seen but not a failed check: the clinic request ("patients, doctors, appointments and prescriptions") got no questions, although the prompt calls record types without details "vague". The salon got 5 questions and skipped "who may change the data". One run each: the model's answers can vary between runs.

## Checks (last run 2026-11-04)
- Backend: `.venv/Scripts/python -m pytest` in `prototype-backend/` → 140 passed (`evidence/backend_tests_weak_points.txt`). Retrieval: 7 of 20 right, 0 wrong (`evidence/rag_check_step5.txt`). Live checks of steps 1–2, with a fake key and a throwaway database: `evidence/live_check_step1_step2.txt`. A generated API's own report: `evidence/generated_api_step3.txt` (11 of 11).
- Frontend: `npx vitest --run` → 75 passed (`evidence/frontend_tests_multi_record.txt`); `npm run typecheck` and `npm run build` pass.
- Lint trap: oxlint skips git-ignored folders, so `npm run lint` says "No files found" here. Lint a copy outside the repo instead:
  `T=$(mktemp -d); cp -r src .oxlintrc.json $T/; (cd $T && <this folder>/node_modules/.bin/oxlint -c .oxlintrc.json src)` → no problems.
- Not tried yet: a real request through OpenAI (costs money), and clicking through in a browser.

## Rules
- Uses OpenAI, which is paid: every request costs a little on your own key. The team app must not (free tiers only, `agent/llm.py`).
- When a feature works here, port it to the real `frontend/` on a normal branch with tests. Do not copy `src/prototype/`: the team backend has a different API (`docs/api-contract.md`).
- One-time setup (already done on 2026-11-03):
  `python -m venv local/prototype-backend/.venv`, `local/prototype-backend/.venv/Scripts/pip install -r local/prototype-backend/requirements.txt`, `npm ci --prefix local/prototype-frontend`.
