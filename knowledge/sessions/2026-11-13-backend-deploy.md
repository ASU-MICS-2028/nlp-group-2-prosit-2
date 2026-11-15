# 2026-11-13 · Render account and backend early run (S-8, D-2)

Who: Nana, with Claude Code.

## Goal
Finish S-8 (Render account and limits), prepare D-2, and put the backend online early so the deploy path is proven before W-9.

## What we found
- Render Hobby: 5 GB outbound bandwidth and 500 build minutes per month. With no card, going over pauses the service instead of charging.
- The agent is not a separate deploy: `backend/builder.py` imports `agent/`, so one Render service runs everything.
- Render needs an organisation owner to approve its GitHub app. Nana is a member, so we asked the owner in issue #25. They approved it.
- Render named the service after the repo: https://nlp-group-2-prosit-2.onrender.com.
- Vercel blocked the frontend redeploy because the last commit's author (isanamoa) is not the Vercel account owner (iamITHub). Deploying a clean copy of `main`'s `frontend/` with no git history works.

## What we decided
- Deploy the backend now as an **early run**, even though W-9 (its blocker) is not merged. D-2 stays 🔄 until we redeploy after W-9 and run the full checks.
- Auto-deploy off on Render: Nana redeploys by hand, which saves build minutes.
- No card on Render (free tiers only).

## What changed
- Backend live: `/health` 200, CORS allows only the Vercel site (`evidence/deploy/outputs_backend_url.txt`; laptop dry run in `outputs_backend_dryrun.txt`).
- Vercel `VITE_API_URL` set to the Render address; frontend redeployed. The Start screen loads the project list from Render (`evidence/deploy/ui-online-with-backend.png`).
- `deploy/README.md` (Render steps, new frontend redeploy method), `learnings/deployment.md`, PLAN S-8 ✅ and D-2 🔄, README row, AI-use log.

## Open questions / next steps
- After W-9: redeploy the backend (Manual Deploy), run one full build online, the missing-key check, the wake-up time and memory during a build. Then D-2 ✅ and D-3.
- One blocked deployment remains in the Vercel project list. It is harmless; it can be removed from the dashboard if wanted.
