# frontend/ (Perfect, backup owner: Nana)

React + Vite + TypeScript (`strict`). Talks to the backend only through the generated API client (D-001, D-004).

## Commands (fill in as the skeleton lands, S-6)
- Install: `npm ci --prefix frontend`
- Run: `npm run dev --prefix frontend` (needs `VITE_API_URL` pointing at the backend)
- Checks: `npm run lint`, `npx tsc --noEmit`, `npm test -- --run`, `npm run build` (all run in CI)
- Regenerate API client from the backend schema: command recorded in `learnings/frontend.md` (W-6)

## Traps this area enforces
- No `any`. No secrets in the frontend: the browser can read everything. Config only via `VITE_*` variables.
- Small components with one job; API calls in hooks; plain `fetch`.
- Every screen has loading, error and empty states.
- Accessibility: labelled inputs, keyboard use, readable contrast.
- Wording is for non-developers: no jargon without a one-line explanation.
- Free-tier backend may be asleep: show a "waking up" message on slow first requests.

## Every feature needs tests for
Normal flow · empty/too-long input · backend error or offline · slow response · double-click on submit · keyboard-only use.
