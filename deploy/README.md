# deploy/

How we put the platform online on free tiers (D-003, D-011). Limits and pitfalls: `learnings/deployment.md`.

## Frontend on Vercel (D-1)

Vercel's free plan cannot auto-deploy from our repository (it belongs to the ASU-MICS-2028 organisation),
so we deploy from a laptop with the Vercel command-line tool. Nothing here needs a secret in the repo.

**One-time setup (Nana)**
1. Create a free Vercel account (Hobby). Signing in with GitHub is fine.
2. On your laptop, from the repo root:
   ```
   cd frontend
   npm ci
   npm run build          # must pass first: lint, typecheck and tests run in CI too
   npx vercel login       # opens the browser once
   npx vercel link        # create the project; answer the questions as below
   ```
   - Project name: `mesora-api-builder` (any name; it becomes `<name>.vercel.app`)
   - Framework: **Vite** (detected). Build command `npm run build`, output folder `dist`.
   - It then says it **could not connect the Git repository**. That is expected (Hobby plan + organisation repo); ignore it.
   - `vercel link` also writes `frontend/.vercel/` and `frontend/.env.local`. **`.env.local` holds a Vercel login token: never commit, share or upload it.**
     The root `.gitignore` already hides `.env.*`; add `frontend/.vercel/` to your own `.git/info/exclude`.
     If `vercel link` creates a `frontend/.gitignore`, delete it (its `.env*` line would hide `.env.example`).
3. Create `frontend/.vercelignore` on your laptop so the upload never includes secrets or leftovers:
   ```
   .env
   .env.*
   !.env.example
   .vercel
   node_modules
   dist
   ```
4. In the Vercel dashboard → the project → Settings → Environment Variables, add
   `VITE_API_URL` = the backend URL (after D-2; until then leave it unset: the Start screen needs no backend).
   It is not a secret: the browser can read every `VITE_` value.

**Every deploy (after a frontend change is merged into `main`, and on the morning of a demo)**
Deploy from a clean copy of `main`'s `frontend/` that has **no git history**. Vercel's free plan blocks a deploy
("the commit author doesn't have permission") when the last git commit's author is not the Vercel account owner.
Our Vercel account is iamITHub's, but our commits have different authors.
```
git fetch origin
D=$(mktemp -d)
git archive origin/main frontend | tar -x -C "$D"        # exactly main's frontend, no .git folder
mkdir -p "$D/frontend/.vercel"
cp frontend/.vercel/project.json "$D/frontend/.vercel/"  # which Vercel project to deploy to (not a secret)
cp frontend/.vercelignore "$D/frontend/"
cd "$D/frontend" && npx vercel deploy --prod --yes
```
Do **not** copy `frontend/.env.local`; it is not needed to deploy. Vercel builds the code on its own servers
(Do not use `vercel build` on Windows: it needs permission to make symlinks and fails with `EPERM`.)
To prove the build passes before deploying, run `npm ci && npm run build` in your normal `frontend/` on `main`.
Check it (D-1 is done when this prints 200):
```
curl -s -o /dev/null -w "%{http_code}\n" https://mesora-api-builder.vercel.app/
```
Then save evidence: `evidence/deploy/outputs_frontend_url.txt` (the command and its output) and a screenshot.

**Never deploy:** `.env.local` (it is git-ignored, and `.vercelignore` keeps it out of the upload), or any key.

**Live now:** https://mesora-api-builder.vercel.app (first deployed 2026-11-13; redeployed the same day with
`VITE_API_URL` = the Render backend, so the Start screen now loads the project list from it).

## Backend on Render (D-2)
**Live now (early run, 2026-11-13):** https://nlp-group-2-prosit-2.onrender.com, running `main` before W-9 is merged.
`/health`, CORS and the project list work; building an API online needs W-9. **After W-9 is merged:** Render dashboard →
the service → Manual Deploy → Deploy latest commit (auto-deploy is off), then run the checks below.

One Render web service runs the whole backend: the FastAPI server, the builder agent (`backend/builder.py` imports
`agent/`), the Gemini calls and the pytest runs of generated code. There is no separate agent deploy.

**Before the deploy day**
1. Render account: done 2026-11-13 (Nana, Hobby workspace). **Do not add a card**: with no card, going over a limit pauses
   the service instead of charging us.
2. Let Render see our repo. The repo belongs to the ASU-MICS-2028 organisation, so an **organisation owner** must approve
   Render's GitHub app for this repository (github.com/apps/render/installations/new → ASU-MICS-2028 → only this repo).
   Nana is a member, so she can request it; an owner approves it.

**Create the service** (Render dashboard → New → Web Service → pick the repo, branch `main`)
| Setting | Value | Why |
|---|---|---|
| Name | `nlp-group-2-prosit-2` (what Render chose; any name works) | Becomes `https://<name>.onrender.com` |
| Region | Frankfurt (EU Central) | Closest to Ghana |
| Instance type | **Free** | Free tiers only |
| Root directory | (empty: the repo root) | `backend/` imports `agent/`, so both must be there |
| Build command | `pip install -r backend/requirements.txt` | Same pinned versions as CI |
| Start command | `uvicorn backend.main:app --host 0.0.0.0 --port $PORT` | Render tells the app which port to use in `$PORT`; `0.0.0.0` lets outside traffic in. No `--reload` online |
| Health check path | `/health` | Render waits for this before it switches traffic to a new deploy |
| Auto-deploy | Off | Each deploy uses build minutes (500/month); Nana deploys by hand |

**Environment variables** (the service → Environment). Type them in the dashboard only, never in a file in the repo.
| Name | Value | Secret? |
|---|---|---|
| `GEMINI_API_KEY` | the team's Gemini key | **Yes** |
| `ALLOWED_ORIGINS` | `https://mesora-api-builder.vercel.app` | No |
| `PYTHON_VERSION` | `3.12.8` (CI uses 3.12) | No |
| `LLM_MODEL` | `gemini-3.5-flash` (**required**: with no model every build fails at once with "The server has no AI model set (LLM_MODEL)") | No |

**Then connect the frontend**
1. Vercel → mesora-api-builder → Settings → Environment Variables: `VITE_API_URL` = `https://nlp-group-2-prosit-2.onrender.com`.
2. Redeploy the frontend (see above). `VITE_` values are baked in at build time, so the redeploy is needed.

**Checks (D-2 is done when the first passes; save all of them in `evidence/deploy/`)**
```
curl -s https://nlp-group-2-prosit-2.onrender.com/health        # {"status":"ok"}
```
- Asleep: wait 15+ minutes, time the first request (about a minute) and check that the frontend shows its "waking up" notice.
- Key missing: remove `GEMINI_API_KEY` for one test, start a build, and check for a clear error, not a crash. Then put the key back.
- CORS: the Vercel site can call the backend. A page at any other address is refused.
- Memory: watch the service's Metrics tab during one full build. The free server has 512 MB.
