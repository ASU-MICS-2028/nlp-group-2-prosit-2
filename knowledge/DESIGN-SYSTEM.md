# Mesora API Builder: Design System

**Owner:** Frontend · **Status:** v0.2, for team review · **Stack:** React + Vite + TypeScript (D-004)

**v0.2 changes (2026-11-02), after comparing the first build with the reference:** panel sheen and top-edge light (7.6), inner glow and stronger bloom on glow-edge pills (7.1), haze pinned in pixels to the top-right corner (7.2), Display size 32 → 44px (section 5). v0.1 produced flat grey panels and outline-only pills that felt plain next to the reference.

## 0. How to use this file (for Claude Code)

1. Read this whole file before writing any UI.
2. First build only `frontend/src/styles/tokens.css` (section 4–6 values, exactly) and a `/dev/gallery` page that shows every component in section 8. Wait for approval before building screens.
3. Use only the tokens here. No new colours, fonts, radii or shadows.
4. If something isn't covered here, ask. Don't improvise a new style.

---

## 1. Design direction

**Reference:** a dark AI-assistant app concept (left sidebar, "Ready to Create Something New?" headline, chat box, red-orange glow).

**The feeling:** a dark, quiet workshop where one red-orange light shows you where to look. Calm and premium, not flashy. A non-developer should feel the tool is powerful but in control.

### What we take from the reference
- **Near-black, neutral** background (not brown, not blue) with **neutral grey panels**.
- One accent: **red-orange `#FA3D1D`**, used as light, not as paint.
- The **glow edge**: dark pills and cards whose 1px border lights up red-orange at one corner and fades out (section 7.1). This is the signature.
- A soft **red-orange haze** in the top-right of the main area (section 7.2).
- The **left sidebar**: logo tile, "New" pill, grey section labels, nav rows with a small square icon tile.
- Big, bold, white headline above a dark **input card** with small pill buttons inside it.
- A **warm highlight card** whose top fades from red-orange into the panel colour (the reference's "Upgrade" card).
- Small, dense UI type in one clean sans.

### What we change, and why
| Reference does | We do | Why |
|---|---|---|
| "Lumix AI" name, sparkle logo, gem icon | Our own name and a `{ }` logo tile (section 3) | Inspiration, not copying another designer's work. |
| "Upgrade to Premium" card | The same card style for **plan approval** and **API ready** | We have no payments; the style is perfect for the one moment that matters on a screen. |
| "ChatGPT v4.0" model picker | Removed | The LLM provider is a backend setting (D-002), not the user's choice. |
| Create Image / Brainstorm / Image Generator | Example API requests and our five-step flow | Out of scope; our product builds APIs. |
| Very small grey text (11px) | Body text 14px minimum, grey no darker than `--text-muted` | Must pass 4.5:1 contrast. |
| Possibly SF Pro | **Inter** | See section 5. |

---

## 2. Principles (apply to every screen)

1. **One glowing thing per area.** The glow marks the next action. If two things glow, neither does.
2. **Show the plan before building.** Nothing is generated until the user approves (human-in-the-loop).
3. **Show the work.** The build screen shows the agent's steps and test results live, in plain words.
4. **Plain language.** Explain a technical word once: "Endpoints (addresses your app will call)". Buttons are verbs: "Plan my API", "Approve plan", "Download project".
5. **Every screen has loading, error and empty states**, plus a "server is waking up" message for the free-tier backend (from `frontend/AGENTS.md`).

---

## 3. Brand

- **Name:** `MesoraForge` in the sidebar (confirm with the team).
- **Logo tile:** 28×28px, radius 8px, the accent gradient (section 7.3), with `{ }` in white, Inter 600 14px, centred. It says "API" without a generic sparkle or robot.
- No mascot, no illustrations. Empty states use one Lucide icon in a tile plus one sentence.

---

## 4. Colour

Dark only. All text pairs below pass WCAG AA (4.5:1) on every surface listed.

| Token | Hex | Use |
|---|---|---|
| `--bg` | `#050505` | App background (reference: `#010101`) |
| `--panel` | `#151515` | Sidebar, cards, input card (reference: `#151515`) |
| `--panel-raised` | `#1C1C1C` | Hover rows, chips, cards inside cards |
| `--tile` | `#282828` | Nav icon tiles, method-badge backgrounds (reference: `#282828`) |
| `--border` | `#262626` | Decorative 1px borders around panels and cards |
| `--border-control` | `#6B6B6B` | Text inputs only (needs 3:1) |
| `--text` | `#EEEEEE` | All readable text (reference: `#EEEEEE`) |
| `--text-muted` | `#9A9A9A` | Secondary text, section labels, placeholders |
| `--accent` | `#FA3D1D` | Glow, logo tile, active step dot, focus ring. **Never a background behind text.** |
| `--accent-text` | `#FF6A4D` | Accent-coloured text and icons (e.g. "Question 1 of 2") |
| `--accent-deep` | `#C42A10` | Dark end of the accent gradient |
| `--success` | `#2DD4BF` | Tests passed, ready, POST badge |
| `--error` | `#FF6B6B` | Failed, stopped, DELETE badge |
| `--warning` | `#FBBF24` | Waiting, retrying, waking up, PUT/PATCH badge |
| `--info` | `#60A5FA` | Neutral info, GET badge |

- White text on solid `--accent` is only 3.6:1, so **don't put text on solid orange**. The reference never does either: its buttons are dark pills that glow.
- Status colours always come with a word and an icon. Never colour alone.

---

## 5. Typography

**Inter** for everything; **JetBrains Mono** only for code-shaped text (endpoint paths, file names, test output, the run command).

- Why Inter: the reference looks like Inter or Apple's SF Pro (same shapes; you can't tell for sure from a screenshot). SF Pro's licence only covers apps for Apple platforms, so we use Inter, which is free (SIL Open Font Licence) and looks almost identical.
- Install, no CDN: `npm i @fontsource-variable/inter @fontsource/jetbrains-mono`, import once in `main.tsx`.

| Style | Size / line height | Weight | Tracking | Use |
|---|---|---|---|---|
| Display | 44 / 50 | 700 | -0.02em | The one start-screen question: "What should your API do?" (v0.2: was 32 / 38; the reference's headline is much bigger than everything around it) |
| Title | 20 / 26 | 600 | -0.01em | Screen and card titles |
| Body | 14 / 20 | 400 | 0 | All running text |
| Label | 13 / 18 | 500 | 0 | Buttons, chips, nav rows |
| Caption | 12 / 16 | 500 | 0 | Metadata, status pills, counters |
| Section label | 12 / 16 | 500 | 0.02em | Sidebar group names ("Projects"), muted |
| Code | 13 / 20 | 400 | 0 | JetBrains Mono, code-shaped text only |

---

## 6. Space, radius, depth

- **Spacing:** 4px grid. `4, 8, 12, 16, 20, 24, 32, 48`.
- **Radius:** tiles and badges `8px` · cards and input card `16px` · sidebar and big panels `20px` · buttons, chips, pills `999px`.
- **Depth comes from light, not shadows.** No grey drop shadows. Depth = panel colour steps + glow edges + the ambient haze.
- **Focus ring:** `0 0 0 2px var(--bg), 0 0 0 4px var(--accent)` on every interactive element.

---

## 7. Signature effects (this is the "feel"; get these right)

### 7.1 Glow edge
A dark pill or card whose 1px border is red-orange at one corner and fades to nothing. Used on: the primary button, the "New project" pill, chips, the small pills inside the input card.

```css
/* v0.2: the first layer is a soft inner light at the lit corner */
.glow-edge {
  border: 1px solid transparent;
  background:
    radial-gradient(80px 32px at 0 0, rgba(250, 61, 29, 0.3), transparent 70%) padding-box,
    linear-gradient(var(--panel), var(--panel)) padding-box,
    linear-gradient(135deg, rgba(250, 61, 29, 0.9), rgba(250, 61, 29, 0) 45%) border-box;
}
/* stronger version for the one primary button */
.glow-edge--strong {
  background:
    radial-gradient(100px 40px at 0 0, rgba(250, 61, 29, 0.45), transparent 70%) padding-box,
    linear-gradient(var(--panel-raised), var(--panel-raised)) padding-box,
    linear-gradient(135deg, #FF6A4D, rgba(250, 61, 29, 0) 60%) border-box;
  box-shadow: -8px -6px 24px -8px rgba(250, 61, 29, 0.6);
}
```
The bright corner is always **top-left**, like the reference.

### 7.2 Ambient haze
Only on the main area (not the sidebar), once per screen. v0.2: sized in pixels and pinned to the top-right corner. v0.1 used percentages of the main area's height, so on a tall page the glow slid off the top and disappeared.
```css
.haze { position: relative; isolation: isolate; background: var(--bg); }
.haze::before {
  content: ''; position: absolute; z-index: -1; top: 0; right: 0;
  width: min(900px, 100%); height: 560px; pointer-events: none;
  background: radial-gradient(ellipse at 100% 0%, rgba(250, 61, 29, 0.32), transparent 70%);
}
```

### 7.3 Accent gradient
For the logo tile and the active-step dot only:
`linear-gradient(135deg, #FF6A4D 0%, #FA3D1D 45%, #C42A10 100%)`.

### 7.4 Warm highlight card
For the **plan approval** card and the **API ready** card (one per screen):
```css
.warm-card {
  background: linear-gradient(180deg, rgba(250, 61, 29, 0.22), rgba(21, 21, 21, 0) 55%), var(--panel);
  border: 1px solid rgba(250, 61, 29, 0.35);
  border-radius: 16px;
}
```

### 7.6 Panel sheen (new in v0.2)
Panels (sidebar, cards) get a faint light from above and a 1px lit top edge, so they read as surfaces and not flat grey blocks. This is light, not a drop shadow, so the "no grey drop shadows" rule still holds.
```css
--sheen: linear-gradient(180deg, rgba(255, 255, 255, 0.035), rgba(255, 255, 255, 0) 40%);
--edge-light: inset 0 1px 0 rgba(255, 255, 255, 0.06);
.card, .sidebar { background: var(--sheen), var(--panel); box-shadow: var(--edge-light); }
```
The warm card keeps its own red-orange fade (7.4). It is written as `.card.warm-card` so the plain card background cannot overwrite it (v0.1 bug).

### 7.5 Motion
- The active build step's dot pulses (opacity 1 → 0.5, 1.6s, ease-in-out).
- Hover: glow edges brighten over 150ms.
- Under `prefers-reduced-motion`, nothing pulses.

---

## 8. Components

Build each in `/dev/gallery` first, with its states.

**8.1 App shell.** Sidebar 260px, `--panel`, radius 20px, 12px inset from the window edges. Main column max 720px, centred, with the ambient haze. Under 768px the sidebar becomes a slide-over behind a menu button.

**8.2 Sidebar.** Logo tile + "Mesora" (Title 16px 600). "New project" pill with glow edge, full width, `+` icon. Section label "Projects". Project rows: name (Label) + status pill + "Yesterday" (Caption muted). Active row: `--panel-raised`. Empty: "No projects yet. Describe your first API to start one."

**8.3 Nav/project row icon tile.** 28×28px, `--tile`, radius 8px, 16px Lucide icon in `--text-muted`.

**8.4 Buttons.** Height 40px, radius 999px, Label style.
- Primary: `--panel-raised` + `.glow-edge--strong`, `--text`. One per screen.
- Secondary: `--panel-raised`, `1px --border`, `--text`.
- Ghost: no fill, `--text-muted`, hover `--text`.
- Loading: spinner + the label still visible ("Reading your request"); disabled while loading.

**8.5 Chips.** Height 32px, radius 999px, `.glow-edge`, Label style. Example-request chips under the input card ("Bookshop API", "Clinic appointments", "Farm produce orders"). As answer chips: selected = `.glow-edge--strong` + `aria-pressed="true"`.

**8.6 Request input card** (the reference's "Ask Anything" card). `--panel`, radius 16px, 16px padding. Top-left label with a Lucide sparkles icon in `--accent-text`: "Describe the API you need". Textarea, Body style, no border, min 4 rows. Bottom row: character counter (Caption muted, "115 / 2000"; turns `--error` with "Too long by 40 characters"), and the primary button "Plan my API →". Ctrl/Cmd + Enter sends.

**8.7 Question card.** `--panel`, radius 16px. "Question 1 of 2" (Caption, `--accent-text`), the question (Title), one line on why it's asked (Body muted), 2–4 answer chips, then an "Or answer in your own words" input (`--border-control`, radius 8px).

**8.8 Plan card** (warm highlight card). "Nothing is built until you approve" (Caption, `--accent-text`), plan name (Title), one-sentence summary. Endpoint rows: method badge + path (Code) + plain-English description (Body muted), separated by `--border`. "What it stores": one row per table, name + fields (Code muted). Footer: "5 tests will check it" (Caption muted), "Change something" (secondary), "Approve plan" (primary).

**8.9 Method badge.** Code style 11px 600, uppercase, min-width 56px, radius 8px, `--tile` background, text in GET `--info`, POST `--success`, PUT/PATCH `--warning`, DELETE `--error`. (These match the colours on FastAPI's `/docs` page.)

**8.10 Build timeline.** `--panel`, radius 16px. Header: "Building Bookshop API" (Title), "Attempt 2 of 3" (Caption muted), status pill. Test bar: one segment per test (success fill / error striped / `--tile` pending) + "4 passing · 1 failing · 5 tests". Steps down a 2px `--tile` rail; each step labelled **Thinking / Doing / Result** (Caption, uppercase, muted) with Body text and optional code output in a `--bg` well. Current step: accent-gradient dot that pulses + label in `--accent-text`. Failed result: `--error` dot and label.

**8.11 Status pill.** Height 24px, radius 999px, `--panel-raised`, icon + word in the status colour: Working (pulsing accent dot), Waiting, Retrying, Passed, Ready, Failed, Stopped.

**8.12 Ready card** (warm highlight card). Success check in a 40px circle, "Your API is ready" (Title), "9 files · 14 KB · 5 of 5 tests passed" (Caption muted), primary "Download project (.zip)", then the run command in a code well with a ghost "Copy" button, then "Then open localhost:8000/docs to try every endpoint."

**8.13 Notice.** `--panel-raised`, radius 16px, 1px border in the status colour at 40% opacity, icon + title + one sentence + optional small secondary button. Waking up: "The server is waking up. The first request after a quiet spell takes about half a minute."

### Screen map
| Screen | Components | States |
|---|---|---|
| Start | Display headline, request input card, example chips | Empty (chips shown), waking up, error |
| Questions | Question cards (max 3) | Loading, error |
| Plan | Plan card | Loading, "Change something" goes back to Questions |
| Building | Build timeline | Running, retrying, stopped (with a notice saying what to do) |
| Ready | Ready card | Ready, download failed |
| Every screen | Sidebar | Empty project list |

---

## 9. Icons

**Lucide** (`lucide-react`, ISC licence), 16px in controls and 18px in the sidebar, stroke 1.5, `currentColor`. The reference uses the same thin rounded line style.

---

## 10. Accessibility checklist

- [ ] Text 4.5:1, icons and control borders 3:1 (use the pairs in section 4 only).
- [ ] No text on solid `--accent`.
- [ ] Focus ring visible on every interactive element.
- [ ] Every icon-only button has an `aria-label`.
- [ ] Status never shown by colour alone (word + icon).
- [ ] The live status uses `role="status"`; errors use `role="alert"`.
- [ ] Keyboard-only walkthrough of all five screens works.
- [ ] Respects `prefers-reduced-motion`.

---

## 11. Do and don't

**Do**
- Keep backgrounds neutral black and grey. The only colour is the red-orange light.
- Put the bright corner of every glow edge at the top-left.
- Use the warm highlight card only for "Approve plan" and "Your API is ready".
- Keep UI text small and calm; let the display headline be the one big thing.

**Don't**
- Tint the greys warm or brown. The reference is neutral.
- Fill buttons with solid orange or put text on orange.
- Add grey drop shadows, extra gradients or a second accent colour.
- Copy the reference's name, logo, gem, "Upgrade to Premium" copy or model picker.
- Load fonts or icons from a CDN.
- Add screens or features not in `PLAN.md`.
