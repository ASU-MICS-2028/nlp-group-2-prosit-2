# Frontend

Owner: Perfect · Last updated: 2026-11-03 (F-12 by Nana, see section 9) · Status: partly working (skeleton, design components and Start screen done; no backend connection yet)

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
npm test -- --run   # 38 passed (13 original + 25 for F-12)
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
- People can correct the plan by editing its stored details in plain words before anything is built.

## 9. F-12: features from the earlier prototype (Nana, 2026-11-03)
Ideas came from Nana's earlier Next.js prototype. No code was copied: it was rewritten in this app's components and styles, because D-004 rules out Next.js.

**What changed, step by step**
1. `QuestionCard` now takes a whole question with a `kind`: single choice (chips + own words), multi choice (pick many), yes/no, short text. It holds one `answer` value, so "own words" is just another answer, not a second piece of state.
2. New `QuestionFlow`: one question at a time with Back / Next, and "Skip, use your best guess". It sends only answered questions, in the contract's `{question_id, answer}` shape (`answers.ts`). Buttons are off while `busy`, so a double-click sends once.
3. New `FieldsEditor` inside `PlanCard`: rename a detail, choose its type in plain words ("Whole number", not `int`), tick "Must be filled in", add or remove (2 to 10). `id`-style details are shown but locked. Approve is off until every detail has a name. Shared values live in `fields.ts`.
4. `PlanCard` shows a "Not included yet" list when the planner sends one.
5. New `CannotBuildNotice`: refused (error, read out at once) or unsupported (calm, with an optional alternative), both with "Change my request".
6. `BuildTimeline` folds raw test output behind "Show details for a developer".

**Why this way**
- Editing a detail is faster and less scary for a non-developer than rewriting the whole request.
- Helpers are in `.ts` files, not component files, because oxlint warns that Vite's fast refresh breaks otherwise.
- The plan shape changed (fields are a list, not one string), so it is written down as D-010 (Proposed) for Elise and Perfect.

**How to check it**: run the commands in section 4, then open `/dev/gallery`: every question kind, the flow (it prints what it would send), the editable plan (clear a name and Approve turns off), both cannot-build notices. Proof: `evidence/frontend/outputs_f12_checks.txt`.

**Not done / faked**
- Still not wired into `App.tsx`: no backend calls (that is W-7 and F-3). The backend does not send `kind`, structured fields or `not_included` until D-010 is agreed.
- Not checked by eye in a browser yet, and no keyboard-only walkthrough yet. Tests cover roles and labels only.
- Multi-choice has no "something else" box (the prototype had one).

**Terms**
| Term | One-line meaning |
|---|---|
| Controlled component | A component that shows a value its parent owns and reports changes through a callback (`onChange`) |
| `<details>` / `<summary>` | Built-in HTML for a fold-out section; works with the keyboard without extra code |
| Fast refresh | Vite updating the page while you edit, without losing what you typed |
| `aria-live` | Tells screen readers to read out a part of the page when it changes |
