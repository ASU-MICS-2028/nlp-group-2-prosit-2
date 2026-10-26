# deploy/ (Nana, backup owner: anyone)

Deployment config for Vercel (frontend) and Render (backend) on free tiers (D-003). Keep the backend host swappable.

## Traps this area enforces
- Secrets (API keys) go in the host's settings page, never in the repo.
- Hosted demo servers run the image or build that was last deployed, not the latest commit. Say who redeploys and when.
- Free tier sleeps when idle: warm it up before any demo.
- CORS: the backend must allow the Vercel URL only.
- Record free-tier limits and the live URLs in `learnings/deployment.md`.

## Checks needed
`/health` responds on the public URL · one full request works from the deployed frontend · behaviour when the backend is asleep · key missing gives a clear error, not a crash.
