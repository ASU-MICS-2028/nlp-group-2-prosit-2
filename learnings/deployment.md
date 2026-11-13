# Deployment

Owner: Nana · Last updated: 2026-11-13 · Status: partly working (frontend live; backend waits for W-9)

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
8. Still to do: after W-9 is merged, redeploy the backend and run the remaining checks (one full build online, key missing,
   wake-up time after sleep, memory during a build). Then D-2 ✅ and D-3.

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
After D-2 (later, needs W-9):
```
$ curl -s https://<our-backend>.onrender.com/health
{"status":"ok"}
```

## 5. What is NOT done or is faked
- Frontend live: https://mesora-api-builder.vercel.app. Backend live (early run): https://nlp-group-2-prosit-2.onrender.com.
- **Building an API online does not work yet.** The backend runs `main` before W-9, so a new project stays "waiting".
- Not tested online yet: a full build, the missing-key error, the wake-up time after 15 idle minutes, memory during a build.
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
| Build time (for `VITE_` values) | The moment `npm run build` runs; `VITE_` values are copied into the JavaScript then, not read later |

## 8. Lines ready for the report
- The frontend is hosted on Vercel's free plan and the backend on Render's free plan, so the whole system costs nothing to run.
- The free backend sleeps after 15 idle minutes and has no persistent disk, so the first request can take about a minute and data resets when the server restarts.

## 9. Sources (read 2026-11-10)
- Render: https://render.com/docs/free
- Render bandwidth (Hobby 5 GB): https://render.com/docs/outbound-bandwidth (read 2026-11-13)
- Render build minutes (Hobby 500): https://render.com/docs/build-pipeline (read 2026-11-13)
- Render free instance size (512 MB RAM, 0.1 CPU): https://render.com/docs/compute-plans
- Vercel limits (Git organisations, deployments, upload size): https://vercel.com/docs/limits
- Vercel Hobby allowances and non-commercial rule: https://vercel.com/docs/limits/fair-use-guidelines
