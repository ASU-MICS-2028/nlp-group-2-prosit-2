# Deployment

Owner: Nana · Last updated: 2026-11-15 · Status: working (frontend and backend live; first online build ended ready 2026-11-15)

## 1. In one sentence
The frontend is a set of static files hosted free on Vercel; the backend is a long-running Python server hosted free on Render (D-003, D-011).

## 2. What I did, step by step
1. Read the official free-tier pages on 2026-11-10 (links in section 9) and wrote the limits below.
2. Found two things that change how we deploy (section 6): Vercel's free plan cannot auto-deploy from an organisation's repository, and Render's free server is small (512 MB RAM).
3. Wrote the deploy steps in `deploy/README.md`.
4. 2026-11-13: created the Vercel account (Hobby, signed in with GitHub) and deployed the frontend (D-1) from my laptop
   with `npx vercel deploy --prod --yes`. Live at **https://mesora-api-builder.vercel.app**. Checked it with curl (200, page title
   "API Builder") and searched the published JavaScript for keys (none). Evidence: `evidence/deploy/outputs_frontend_url.txt`, `evidence/deploy/ui-online.png`.
5. 2026-11-13: created the Render account (S-8) and read its bandwidth and build-minute limits (section 3).
   Wrote the backend steps in `deploy/README.md`. Dry run on the laptop with Render's start command: `/health` OK,
   CORS lets in only the Vercel address, idle memory about 51 MB (`evidence/deploy/outputs_backend_dryrun.txt`).
6. 2026-11-13: the organisation owner approved Render's app (issue #25). Nana created the Render web service in the
   dashboard (settings in `deploy/README.md`; Gemini key typed into Render only). **Early run**: live at
   **https://nlp-group-2-prosit-2.onrender.com** with today's `main`. Checked: `/health` 200, CORS allows only the Vercel site,
   `/projects` answers (`evidence/deploy/outputs_backend_url.txt`).
7. Set `VITE_API_URL` in Vercel to the Render address and redeployed the frontend. The first try was **blocked** (see section 6).
   Redeployed from a clean copy without git history: the live JavaScript now has the Render address and no keys, and the Start
   screen loads "No projects yet" from the backend (`evidence/deploy/ui-online-with-backend.png`).
8. 2026-11-14: W-9 merged; redeployed the backend (Manual Deploy). The first build failed at once: "The server has no AI
   model set (LLM_MODEL)". My deploy steps had wrongly called `LLM_MODEL` optional. That was a clear message, not a crash
   (`evidence/deploy/outputs_backend_no_model.txt`). Nana added `LLM_MODEL=gemini-3.5-flash` in Render. The next two builds
   ran, then failed because Gemini's free tier was "busy" on every retry. One build wrote a file first, so the key works
   (`evidence/deploy/outputs_backend_first_builds.txt`).
9. 2026-11-15: build 4 failed the same way, while the same request on the laptop was ready in about 40 s. Nana read
   Render's Logs: the real error was **429 RESOURCE_EXHAUSTED, 20 requests per day** on the free tier, not "busy" (section 6).
   Render shared one Google project (one daily quota) with our laptops
   (`evidence/deploy/outputs_backend_build4_quota.txt`). Nana made a **separate Gemini key just for Render**.
10. 2026-11-15: the first online build that ended **ready**: a to-do list API, 6 files, **9 of 9 tests passed**, about
    4 minutes (`evidence/deploy/outputs_backend_ready_build.txt`).
11. Wake-up after 18 idle minutes: the first `/health` took **34 seconds**, then answered 200 (`evidence/deploy/outputs_backend_wakeup.txt`).
12. Still to do: memory during a build (Render's Metrics tab), then D-3.
13. 2026-11-15, D-3 ✅: redeployed the frontend (the live site was still the 13 Nov version, without the download button or
    the Ready screen: Vercel does not redeploy by itself). With paid API credit on Render's key, a Bookshop build ended ready
    in 36 s, 9 of 9 tests; the zip downloaded; `/apis/p_2/docs` and calls through the live link worked. A link to an API that
    had gone to sleep showed "This API is asleep"; fixed in #43 (the link starts it first), redeployed, and checked by Nana
    (`evidence/deploy/outputs_d3_online_smoke.txt`).
14. **After any frontend change is merged, redeploy the frontend by hand** (clean copy of `main`), and the backend first if it changed too.

## 3. Free-tier limits (checked 2026-11-10)

**Vercel, Hobby plan (frontend)**
| Limit | Value |
|---|---|
| Use | Non-commercial, personal use only (a course project is fine) |
| Data transfer | First 100 GB per month |
| Deployments | 100 per day; 100 builds per hour |
| Upload size from the command line | 100 MB per deploy |
| Projects | 200 |
| Runtime logs kept | 1 hour |
| **Git** | **A Hobby project cannot be connected to a repository owned by a Git organisation** (ours is owned by ASU-MICS-2028) |

**Render, Free web service (backend)**
| Limit | Value |
|---|---|
| Size | 512 MB RAM, 0.1 CPU, one instance (no scaling) |
| Sleep | Sleeps after 15 minutes with no requests; the next request wakes it in about 1 minute |
| Hours | 750 free instance hours per workspace per month (sleeping does not use hours); when used up, all free services stop until next month |
| Disk | No persistent disk. Files written while running are lost on redeploy, restart or sleep |
| Restarts | Render may restart a free service at any time |
| Outgoing traffic | Suspended if unusually high; email ports 25, 465, 587 blocked |
| Outbound bandwidth | **5 GB per month** on the Hobby workspace (checked 2026-11-13). With no card on file, Render stops the services until the next month if we go over |
| Build minutes | **500 per month** on Hobby (checked 2026-11-13). With no card on file, builds stop for the rest of the month if we run out |
| Free databases | One free Postgres and one free Key Value per workspace (see D-013 before using them) |

## 4. How to check it works
After D-1 (see `deploy/README.md`):
```
$ curl -s -o /dev/null -w "%{http_code}\n" https://mesora-api-builder.vercel.app/
200
```
After D-2:
```
$ curl -s https://nlp-group-2-prosit-2.onrender.com/health
{"status":"ok"}
```
A full build online (uses about 10-20 of the day's 20 free requests, so don't do it casually):
```
$ curl -s -X POST https://nlp-group-2-prosit-2.onrender.com/projects -H 'Content-Type: application/json' \
    -d '{"request":"A to-do list API: add a task, list tasks, mark a task done."}'
$ curl -s https://nlp-group-2-prosit-2.onrender.com/projects/<id>     # repeat until "ready" or "failed"
```

**Running the backend on a Windows laptop** (PowerShell, from the repo root):
```
backend\.venv\Scripts\Activate.ps1
uvicorn backend.main:app --reload --env-file .env
```
Without the venv, Windows finds the global `uvicorn`, which has no Google packages: the server crashes with
`No module named 'google'`. Without `--env-file .env`, the server never reads `.env` (no code loads it), so every build
fails with "The server has no AI model set (LLM_MODEL)".

## 5. What is NOT done or is faked
- Frontend live: https://mesora-api-builder.vercel.app. Backend live (early run): https://nlp-group-2-prosit-2.onrender.com.
- **Building an API online works** (2026-11-15, 9 of 9 tests), but only about **one build per model per day** on the free tier.
- Not tested online yet: the missing-key error, memory during a build, the frontend's "waking up" notice.
- Render account created 2026-11-13 (Nana, GitHub sign-in). The 5 GB and 500-minute numbers come from Render's docs; nobody has yet confirmed them on the account's billing page.

## 6. What will bite us
- **No auto-deploy for the frontend.** Because the repo belongs to an organisation, Vercel's free plan cannot watch it. The frontend is deployed from a laptop with the Vercel command-line tool. **Who redeploys:** Nana, after any change to `frontend/` is merged into `main`, and always on the morning of a demo. Other options cost money (Pro plan) or add secrets (a GitHub Action with a Vercel token in the organisation's settings).
- **The backend sleeps.** The first request after 15 quiet minutes takes about a minute. Open `/health` a few minutes before any demo; the frontend should show a "waking up" notice (it has a Notice component for this).
- **Small server for D-011.** D-011 runs up to 3 generated APIs live inside our backend, plus the agent and pytest runs, all in 512 MB RAM. That may run out of memory. Elise and Perfect should measure memory with 3 live APIs before the demo; the limit of 3 may need to drop to 1 on the free tier.
- **Data does not last.** No persistent disk: projects in memory (D-013) and every generated API's data reset on each restart or sleep. The report must say so (D-011 already does).
- **Do not add a card to Render.** With no card, going over a limit pauses the service instead of charging us (free tiers only). 5 GB is plenty for a demo; each redeploy uses build minutes, so don't redeploy in a loop.
- **The agent runs inside the backend.** `backend/builder.py` imports `agent/`, so the agent, Gemini calls and the pytest runs of generated code all happen on the same 512 MB Render server. There is no separate agent deploy.
- **CORS.** When the backend is deployed, its allowed origins must be set to the Vercel URL only (`deploy/AGENTS.md`).
- **Secrets.** The Gemini key goes in Render's environment settings page, never in the repo.
- **`vercel link` writes a token to `frontend/.env.local`.** It is a login token for our Vercel account. It is git-ignored
  (`.env.*`) and kept out of uploads by `frontend/.vercelignore`. Never commit or share it.
- **`vercel build` fails on Windows** with `EPERM` (it needs permission to make symlinks). Use `vercel deploy --prod --yes`
  instead: Vercel builds the code on its own servers.
- **Vercel blocks a deploy if the last commit's author is not the account owner.** Our Vercel account is iamITHub's;
  a deploy from a branch whose last commit was by isanamoa was "Blocked". Fix: deploy from a clean copy of `main`'s
  `frontend/` with no `.git` folder (`deploy/README.md` shows how).
- **Render chose the service name** `nlp-group-2-prosit-2`, not the planned `mesora-api-builder-api`. The name is only
  part of the address; it does not matter.
- **`LLM_MODEL` is required on Render**, not optional: without it every build fails at once. We use `gemini-3.5-flash`.
- **Gemini's free tier allows only 20 requests per day, per Google project, per model.** This, not "busy", was why the
  online builds of 2026-11-14 and 2026-11-15 failed (429 RESOURCE_EXHAUSTED in Render's Logs). One build uses about
  10-20 requests, so that is about one build per model per day. Since #35 (Opei) the app says so: "Today's free AI limit
  is used up. Please try again tomorrow.", and it stops at once instead of retrying. "The AI service is busy" now means a
  real 503: try again in a few minutes. If unsure, Render's Logs show the code (429 or 503).
- **Render has its own Gemini key**, in a separate Google project, so laptop testing does not use up the live site's quota.
  On demo day: one warm-up build early, then nothing until the demo.
- **Changing the model name does not give a fresh quota.** Render asked for `gemini-3.4-flash` and the laptop for
  `gemini-3.5-flash`, yet Google counted both against `gemini-3.6-flash`'s 20 a day. Only a key in a different Google
  project has its own 20. Keep `LLM_MODEL=gemini-3.5-flash`, the model all our checks used.
- **`VITE_API_URL` is baked in at build time.** Changing it in the Vercel dashboard does nothing until we redeploy.

## 7. Terms used
| Term | One-line meaning |
|---|---|
| Static files | Finished HTML, CSS and JavaScript a server only hands out; the frontend after `npm run build` |
| Vercel CLI | Vercel's command-line tool; `vercel --prod` uploads a folder and publishes it |
| Cold start | The slow first request while a sleeping free server starts up again |
| Persistent disk | Storage that survives restarts; Render's free tier has none |
| CORS | The browser rule that lets a page call a server only if the server allows that page's address |
| Instance hours | Hours a server is awake and running; free hours are counted per month |
| `.vercelignore` | A list of files the Vercel CLI must not upload, like `.gitignore` but for deploys |
| Symlink | A file that points to another file; Windows only lets some users create them, which breaks `vercel build` |
| 429 RESOURCE_EXHAUSTED | Google's answer when a quota is used up; for a per-day quota, retrying only helps the next day |
| Quota | A fixed number of requests allowed in a period (here: 20 per day per model on the free tier) |
| venv | A folder with the project's own Python and packages (`backend/.venv`), separate from the computer's global Python |
| Build time (for `VITE_` values) | The moment `npm run build` runs; `VITE_` values are copied into the JavaScript then, not read later |

## 8. Lines ready for the report
- The frontend is hosted on Vercel's free plan and the backend on Render's free plan, so the whole system costs nothing to run.
- The free backend sleeps after 15 idle minutes and has no persistent disk, so the first request can take about a minute and data resets when the server restarts.
- Gemini's free tier allows 20 requests per day per model, and one build needs about 10-20, so the free online version can build only about one API per model per day.

## 9. Sources (read 2026-11-10)
- Render: https://render.com/docs/free
- Render bandwidth (Hobby 5 GB): https://render.com/docs/outbound-bandwidth (read 2026-11-13)
- Render build minutes (Hobby 500): https://render.com/docs/build-pipeline (read 2026-11-13)
- Render free instance size (512 MB RAM, 0.1 CPU): https://render.com/docs/compute-plans
- Vercel limits (Git organisations, deployments, upload size): https://vercel.com/docs/limits
- Vercel Hobby allowances and non-commercial rule: https://vercel.com/docs/limits/fair-use-guidelines
- Gemini API rate limits (named in the 429 error, 2026-11-15): https://aistudio.google.com/docs/rate-limits
