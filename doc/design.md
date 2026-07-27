# Solar Docs Auto-Fill — Design Spec (v2)

## 1. Where this stands right now

The current `app.py` renders a single-page form with a fixed sidebar, grouped
field cards, a live completion tracker, and a ZIP download button. Functionally
it's solid. Visually, it's fighting itself:

| Element | Current state | Problem |
|---|---|---|
| Color system | Dark navy + indigo/purple gradient text and glow | Reads as a SaaS marketing site, not a paperwork tool |
| Theme picker | 3 swappable themes (Indigo / Cyberpunk Neon / Sunset Flame) | Unneeded complexity for a single-user local form. Cut it. |
| Icons | Emoji (☀️ 👤 📍 ⚡ 🔌 🏢) | Inconsistent rendering across OS/browsers, looks unfinished |
| Cards | Heavy blur, glow-on-hover, lift-on-hover | Distracting on a form you'll fill in 10+ times a week |
| `full-width-section` class | Referenced in the Jinja template, never defined in CSS | Dead code — currently does nothing |
| Sidebar nav + progress badges | Genuinely good idea | Undercut by decoration, not the concept |

Verdict: don't rebuild the structure, restyle it. Sidebar nav, section
grouping, live progress, sample-data button — all keep. What changes is the
visual language: from "glowing dashboard" to "clean utility tool."

---

## 2. Design direction

**Reference point:** Linear, Notion forms, a well-built internal admin panel —
not a landing page. The people using this are solar installers filling in the
same 23 fields for the Nth consumer this month. The job of the UI is to get
out of the way: high scan-ability, obvious required fields, zero ambiguity
about what's been filled in.

**Principles:**
- Flat, not glowing. No box-shadow glow, no gradient text, no blur-heavy glass.
- One accent color, used sparingly (focus states, primary button, progress bar).
- Real icons or none — not emoji.
- Density over decoration. More visible fields per scroll, less padding theater.
- Motion only where it communicates state (progress bar fill, focus ring) —
  drop hover-lift on cards.

---

## 3. Color tokens

Single light-mode-first palette (dark mode optional later, not themeable at runtime):

```css
:root {
  --bg-page:        #f7f8fa;
  --bg-surface:      #ffffff;
  --bg-sidebar:      #14161f;
  --border:          #e2e4e9;
  --border-sidebar:  rgba(255,255,255,0.08);

  --text-primary:    #14161f;
  --text-secondary:  #6b7280;
  --text-on-dark:    #f4f5f7;
  --text-on-dark-secondary: #9497a5;

  --accent:          #4f46e5;   /* indigo-600, one accent, not a gradient */
  --accent-hover:    #4338ca;
  --accent-soft:     #eef0fd;   /* focus rings, active nav bg */

  --success:         #16a34a;
  --danger:           #dc2626;

  --radius-sm: 6px;
  --radius-md: 10px;
  --font-sans: 'Inter', system-ui, -apple-system, sans-serif;
}
```

No gradients. No glow shadows. `--accent` is the only saturated color in the
UI — it appears on the primary button, focus rings, active nav item, and
progress bar. Everything else is near-neutral grayscale, which is what makes
a form feel calm and fast to scan instead of decorated.

---

## 4. Typography

- **Font:** Inter (or system-ui fallback) for everything — drop the two-font
  pairing (Plus Jakarta Sans + Outfit). One typeface, weight does the work.
- **Scale:**
  - Page title: 28px / 700
  - Section card title: 16px / 600
  - Field label: 13px / 600
  - Input text: 14px / 400
  - Hint text: 12px / 400, `--text-secondary`
- No gradient-clipped text anywhere. Headings are solid `--text-primary`.

---

## 5. Layout

Keep the two-column shell: fixed sidebar (280px, down from 320px — it's just
nav + two buttons, doesn't need the width) + scrollable form column, max
width 840px so lines don't run edge-to-edge on wide monitors.

```
┌─────────────┬──────────────────────────────────────┐
│  Sidebar     │  Solar Docs Auto-Fill                │
│  (dark,      │  Fill once, generate 7 documents     │
│  280px)      │                                       │
│              │  ┌─ Consumer General Info ─────────┐ │
│  ● Consumer  │  │ [fields...]                      │ │
│  ● Address   │  └───────────────────────────────────┘ │
│  ○ Solar     │  ┌─ Address Information ────────────┐ │
│  ○ Dates     │  │ [fields...]                      │ │
│  ○ Vendor    │  └───────────────────────────────────┘ │
│  ○ MSEDCL    │                                       │
│  ○ Meter     │  [more cards...]                     │
│              │                                       │
│  [progress]  │  [ Generate & Download ZIP ]         │
│  ⚡ Sample    │                                       │
│  🗑 Clear     │                                       │
└─────────────┴──────────────────────────────────────┘
```

Sidebar background stays dark (`--bg-sidebar`) for contrast against the light
form area — that part of the original works, keep it. Everything inside the
sidebar loses glow/blur.

---

## 6. Component specs

### Sidebar nav item
- Default: `--text-on-dark-secondary`, no background
- Hover: `rgba(255,255,255,0.05)` background, text → `--text-on-dark`
- Active section (scroll-spy): left border 2px `--accent`, background
  `rgba(79,70,229,0.12)`, text → `--text-on-dark`
- Status indicator: replace `●`/`✓` glyphs with a small solid dot
  (`--text-on-dark-secondary` = incomplete, `--success` = complete). No
  text-shadow glow on the checkmark.

### Progress bar
- Track: `rgba(255,255,255,0.08)`, 4px height
- Fill: solid `--accent`, no glow shadow
- Percentage label: 13px/600, `--text-on-dark`

### Section card
- `--bg-surface`, 1px `--border`, `--radius-md`, 24px padding (down from 36px —
  reclaim vertical space, these forms have 20+ fields)
- No hover lift, no hover glow. A 1px border-color change to `--accent` on
  focus-within is enough signal that you're in that section.
- Card title: icon slot uses a proper icon (Lucide/Feather — `user`, `map-pin`,
  `sun`, `calendar`, `building-2`, `zap`, `plug`), 18px, `--text-secondary`,
  not emoji.

### Input / select
- 1px `--border`, `--radius-sm`, 10px 12px padding, 14px text
- Focus: border → `--accent`, box-shadow `0 0 0 3px var(--accent-soft)` — this
  is the one acceptable "glow," because it's a functional focus indicator,
  not decoration
- Required fields: red asterisk stays, it's clear and standard
- Fix the missing `full-width-section` — either delete the dead class
  reference from the Jinja template or actually implement it (make those
  three sections span full width / disable the 2-column grid, if that was
  the original intent). Right now it's just noise in the markup.

### Primary button ("Generate & Download ZIP")
- Solid `--accent`, white text, `--radius-md`, 14px 28px padding, 600 weight
- Hover: `--accent-hover`, no transform/lift, just color change
- No box-shadow glow — a plain, confident button reads more trustworthy for
  a "this generates my legal paperwork" action than a floaty gradient one

### Secondary buttons (Sample data / Clear)
- Sample data: outline button, `--accent` border/text, fills white/accent-soft
  on hover
- Clear: outline button, `--danger` border/text — keep the color-coding,
  drop the glow

---

## 7. What to explicitly remove

- The `data-theme` attribute system and all three theme palettes (Indigo /
  Cyberpunk / Sunset) — one clean palette only
- `backdrop-filter: blur()` on cards and sidebar
- All `box-shadow` glow effects (`--accent-glow`, `--success-glow`, etc.)
  except the input focus ring
- Gradient-clipped text (`background-clip: text`) on the logo and h1
- `transform: translateY()` hover lift on `.card` and `.btn-primary`
- Emoji icons — swap for an icon set (Lucide is free, MIT-licensed, easy
  CDN include, matches the "internal tool" register better than Feather or
  emoji)

---

## 8. Priority if you're doing this incrementally

1. Fix the dead `full-width-section` class (5-minute bug fix, currently
   shipping broken)
2. Strip the theme picker + glow/blur CSS, land on one flat palette
3. Swap emoji → Lucide icons in `GROUPS` and the sidebar nav
4. Reduce card padding, tighten vertical rhythm
5. Everything else (font swap to Inter, sidebar width) is polish, do it last

This gets you from "impressive-looking AI-generated dashboard" to "tool a
solar contractor trusts to fill out their MSEDCL paperwork correctly" — which
is the actual job the UI has to do.
