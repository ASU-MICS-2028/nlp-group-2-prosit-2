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
5. Still to do by Nana: the Render account (S-8) and its two "check after sign-up" numbers; the backend (D-2, needs W-9).

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
| Bandwidth, build minutes | Count against the workspace's monthly allowance: **check the numbers on the billing page after sign-up** |
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
- Frontend is live: https://mesora-api-builder.vercel.app. Backend: not deployed (no Render account yet).
- The live frontend shows "We could not reach the server" on the Start screen. That is expected: the build uses the
  default backend address `http://localhost:8000` until D-2 gives us a real one and we set `VITE_API_URL` in Vercel and redeploy.
- Render bandwidth and build-minute numbers are not on Render's public pages; fill them in from the dashboard.

## 6. What will bite us
- **No auto-deploy for the frontend.** Because the repo belongs to an organisation, Vercel's free plan cannot watch it. The frontend is deployed from a laptop with the Vercel command-line tool. **Who redeploys:** Nana, after any change to `frontend/` is merged into `main`, and always on the morning of a demo. Other options cost money (Pro plan) or add secrets (a GitHub Action with a Vercel token in the organisation's settings).
- **The backend sleeps.** The first request after 15 quiet minutes takes about a minute. Open `/health` a few minutes before any demo; the frontend should show a "waking up" notice (it has a Notice component for this).
- **Small server for D-011.** D-011 runs up to 3 generated APIs live inside our backend, plus the agent and pytest runs, all in 512 MB RAM. That may run out of memory. Elise and Perfect should measure memory with 3 live APIs before the demo; the limit of 3 may need to drop to 1 on the free tier.
- **Data does not last.** No persistent disk: projects in memory (D-013) and every generated API's data reset on each restart or sleep. The report must say so (D-011 already does).
- **CORS.** When the backend is deployed, its allowed origins must be set to the Vercel URL only (`deploy/AGENTS.md`).
- **Secrets.** The Gemini key goes in Render's environment settings page, never in the repo.
- **`vercel link` writes a token to `frontend/.env.local`.** It is a login token for our Vercel account. It is git-ignored
  (`.env.*`) and kept out of uploads by `frontend/.vercelignore`. Never commit or share it.
- **`vercel build` fails on Windows** with `EPERM` (it needs permission to make symlinks). Use `vercel deploy --prod --yes`
  instead: Vercel builds the code on its own servers.
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
- Render free instance size (512 MB RAM, 0.1 CPU): https://render.com/docs/compute-plans
- Vercel limits (Git organisations, deployments, upload size): https://vercel.com/docs/limits
- Vercel Hobby allowances and non-commercial rule: https://vercel.com/docs/limits/fair-use-guidelines
