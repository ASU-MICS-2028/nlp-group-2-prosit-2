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
```
git switch main && git pull
cd frontend
npm ci && npm run build      # local check only: proves the build passes
npx vercel deploy --prod --yes
```
The last line uploads the source and Vercel builds it on its own servers, then prints the public URL.
(Do not use `vercel build` + `vercel deploy --prebuilt` on Windows: `vercel build` needs permission to make
symlinks and fails with `EPERM`.) Check it (D-1 is done when this prints 200):
```
curl -s -o /dev/null -w "%{http_code}\n" https://mesora-api-builder.vercel.app/
```
Then save evidence: `evidence/deploy/outputs_frontend_url.txt` (the command and its output) and a screenshot.

**Never deploy:** `.env.local` (it is git-ignored, and `.vercelignore` keeps it out of the upload), or any key.

**Live now:** https://mesora-api-builder.vercel.app (first deployed 2026-11-13). Until D-2 the Start screen shows
"We could not reach the server": the build points at `http://localhost:8000` because `VITE_API_URL` is not set yet.

## Backend on Render (D-2, later: needs W-9)
Not yet. Notes for when it starts:
- Render must be allowed to see the organisation's repository (an organisation owner approves Render's GitHub app), or we deploy from a Docker image.
- Keys (Gemini) go in Render's Environment page, never in the repo.
- Allowed origins (CORS): only the Vercel URL.
- Check: `/health` on the public URL, behaviour when asleep, and a clear error when the key is missing.
