# 2026-11-13 · Frontend deploy (D-1)

Who: Nana, with Claude Code.

## Goal
Put the frontend online on Vercel's free plan (D-1), following `deploy/README.md` and D-014.

## What we found
- `vercel link` cannot connect our repository to the project (Hobby plan + organisation repo). Expected; D-014 already plans for a laptop deploy.
- `vercel link` writes `frontend/.env.local` with a Vercel login token and a `frontend/.vercel/` folder. Neither may go in the repo.
- `vercel build` fails on Windows with `EPERM` (no permission to make symlinks). `vercel deploy --prod --yes`, which builds on Vercel's servers, works.
- The live Start screen says "We could not reach the server", because `VITE_API_URL` is not set and the build falls back to `http://localhost:8000`.

## What we decided
- Deploy with `npx vercel deploy --prod --yes` from `frontend/`, with a laptop-only `frontend/.vercelignore` that keeps `.env*`, `.vercel`, `node_modules` and `dist` out of the upload.
- Set `VITE_API_URL` only after D-2 gives us a backend URL, then redeploy.

## What changed
- Live: https://mesora-api-builder.vercel.app (curl 200, title "API Builder"; no keys found in the published JavaScript).
- Evidence: `evidence/deploy/outputs_frontend_url.txt`, `evidence/deploy/ui-online.png`.
- Updated `deploy/README.md`, `learnings/deployment.md`, PLAN D-1 ✅, the README Nana row, and the AI-use log.

## Open questions / next steps
- S-8: create the Render account and fill in its bandwidth and build-minute numbers.
- D-2 (needs W-9): deploy the backend, then set `VITE_API_URL` in Vercel and redeploy; D-3 smoke test after that.
- Turn on two-factor sign-in for the Vercel account.
