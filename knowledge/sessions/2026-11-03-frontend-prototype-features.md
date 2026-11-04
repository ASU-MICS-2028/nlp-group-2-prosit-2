# 2026-11-03: Prototype features into the frontend (F-12)

## Goal
Compare the team frontend with Nana's earlier prototype (`coding_agent/frontend`, Next.js) and bring over its useful features without changing this app's layout.

## What we found
- The prototype is one big Next.js page with no tests, talking to its own backend (`/sessions`, `/jobs`). Its code cannot be copied: D-004 rules out Next.js, and D-001 says the UI talks only to our own backend.
- Its best ideas: typed questions asked one at a time with a Skip button, an editable "what I'll build" card, a "not included yet" list, clear refusal / unsupported messages, and hiding raw errors from non-developers.
- Our contract (D-008) sends plan fields as one string and questions without a kind, so two of these need contract additions.

## What we decided
- Rewrite the five features as components in this app's style. No backend calls (W-7 and F-3 still own the wiring).
- Propose the contract additions as D-010 for Elise and Perfect to review.
- Added task F-12 for Nana in PLAN.md.
- Connecting to the prototype's backend is for this laptop only and is not part of this branch.

## What changed
New: `QuestionFlow`, `FieldsEditor`, `CannotBuildNotice`, `fields.ts`, `answers.ts`, `planning.test.tsx`. Changed: `QuestionCard`, `PlanCard`, `BuildTimeline`, `Gallery`, `components.css`. Docs: PLAN F-12, README, D-010, api-contract additions, `learnings/frontend.md` section 9, AI-use log.

## Open questions / next steps
- Elise and Perfect: accept or change D-010.
- Check the gallery by eye and do a keyboard-only walkthrough.
- Perfect: tell Nana if any of this clashes with plans for W-7 and F-3.
