# Frontend

Owner: Perfect · Last updated: 2026-11-02 · Status: partly working (skeleton, design components and Start screen done; no backend connection yet)

## 1. In one sentence
A React + TypeScript web page where a non-developer types what API they want; it is built from small reusable pieces styled by one set of design tokens.

## 2. What I did, step by step
1. Created the project with Vite (the tool that runs and bundles the page), React and TypeScript in `strict` mode.
2. Added checks: oxlint (finds likely mistakes), Prettier (one code style), `tsc` (type check), Vitest (tests).
3. Put every colour, size and radius in `src/styles/tokens.css` from `knowledge/DESIGN-SYSTEM.md`, and component styles in `components.css`.
4. Built 13 small components in `src/components/` (Button, Chip, StatusPill, MethodBadge, IconTile, Notice, RequestCard, QuestionCard, PlanCard, BuildTimeline, ReadyCard, Sidebar, AppShell).
5. Built `/dev/gallery` (only while developing) to see every component in each state.
6. Built the Start screen (`src/App.tsx`): question, request card, example chips.

## 3. Why we did it this way
- **TypeScript strict**: the compiler catches mistakes before a user does.
- **Plain CSS with tokens, no styling library**: fewer tools to learn; changing one token changes the whole look.
- **Small components, one job each**: easy to test and to explain.
- **oxlint instead of ESLint**: ships with the Vite template and needs no setup (D-004).
- **Fonts and icons installed from npm, not a CDN**: works offline and no outside request (design rule).
- **Start screen does not fake a result**: planning is not connected yet, so it says so.

## 4. How to check it works
```
cd frontend
npm ci
npm run lint        # no output of problems
npm run typecheck   # no errors
npm test -- --run   # 13 passed
npm run build       # built in under a second
npm run dev         # open http://localhost:5173 (or the port it prints)
```
Open `/dev/gallery` on the dev server to see all components.

## 5. What is NOT done or is faked
- Nothing talks to the backend yet. The "Plan my API" button only shows a notice.
- Sidebar project list is always empty (needs `GET /projects`, task W-8).
- Questions, Plan, Building and Ready screens exist as components but are not wired into screens yet.
- The typed API client (generated from the backend's OpenAPI schema) is not generated yet (W-6).
- The glow, sheen and haze strengths were chosen by eye from a reference image; I have not checked contrast on the rendered page or done the keyboard-only walkthrough.

## 6. What will bite us
- `typescript` 7 and `vite` 8 are very new; if a tool complains about versions, check the lock file first.
- Tests need `afterEach(cleanup)` (in `src/test/setup.ts`); without it, tests see each other's leftovers.
- The haze must stay sized in pixels; percentages disappear on tall pages.
- The free-tier backend may be asleep; screens need a "waking up" notice (a Notice component exists).

## 7. Terms used
| Term | One-line meaning |
|---|---|
| Vite | Tool that runs the page while developing and bundles it for release |
| React component | A small function that returns a piece of the page |
| TypeScript strict | JavaScript with types, with the compiler's strictest checks on |
| Design token | A named value (like `--accent`) so styles stay consistent |
| oxlint / Prettier | A mistake finder / an automatic code formatter |
| Vitest | The test runner |
| jsdom | A pretend browser used by tests |
| ARIA role | A hint that lets screen readers understand what an element is |

## 8. Lines ready for the report
- The frontend is a separate React + TypeScript app that talks to the backend only through its API.
- Visual style comes from one token file, so the look can change in one place.
- Components are tested for the behaviour that matters (disabled while loading, input limits, keyboard send, accessibility roles).
