# 2026-11-12: Typed API client (W-6)

**Goal:** Let the frontend call the backend through generated types, so the chat screen (W-7) can be built on it.

**What we found:**
- `openapi-typescript` needs TypeScript 5 and we use 7, so installing it fails. Running it through `npx` works and leaves our dependencies alone.
- The backend's schema is thinner than `docs/api-contract.md`: `GET /projects/{id}` has only `id` and `status`, and there are no answers or approve endpoints yet.
- With the backend stopped, 8 of the 9 live tests fail (the ninth, "nothing is listening", needs no server), so they test something real. The first run showed 7 because one test was too weak; it now asserts a real 404.
- D-014 was taken by the deploy decision while this was open, so the new decision is D-015.

**What we decided:**
- Generate types with `npx openapi-typescript@7.13.0`, commit the generated files, hand-write a thin `fetch` layer (D-015).
- Test the client against a real backend, not a fake; the live tests run only with `VITE_LIVE_API=1`.

**What changed:** `frontend/src/api/` (`client.ts`, `client.live.test.ts`, generated `openapi.json` and `schema.ts`), `frontend/scripts/export_openapi.py`, `frontend/.prettierignore`, an `api:generate` script, D-015, a W-6 section in `learnings/frontend.md`, PLAN (W-6 done, W-7 ready), README table, `evidence/frontend/`.

**Open questions / next steps:** The 30-second timeout was not tested. W-7 builds the chat screen on this client; W-9 and F-4 wait on it. Elise's questions, plan and approve endpoints (F-2) decide when the question and plan screens can connect.
