# design.md — SiliconBrains University Design System

> v0.2 — Palette updated to **Bordo · Green · Cream** with the **60 : 30 : 10** rule. Source palette: BORDO `#6C151E`, GREEN `#0F3D3A`, CREAM `#F5DABF`. White is added only as a neutral surface.

## 1. Design Philosophy
Warm, academic, and prestigious — like a heritage university with a modern interface. Cream gives a calm, paper-like reading surface; deep green gives structure and trust; bordo is used sparingly as the single "action and achievement" color. Dashboards prioritize clarity; the exam screen prioritizes focus. Consistency over novelty: use only the tokens defined here.

### Aarsh Intelligence animation
The animated AI orb is used consistently in the assistant page, floating launcher, and floating chat panel. Preserve the animation's transparent-looking appearance by screen-blending its black canvas into the UI rather than adding a black tile or circular background. Keep it sized to the available control space and provide accessible text/labels on the interactive controls. The site favicon is the graduation-cap `web/src/app/icon.svg`.

## 2. The 60 : 30 : 10 Color Rule

| Share | Role | Color family | Where it appears |
|---|---|---|---|
| **60% — Dominant** | Backgrounds & breathing space | **Cream** family + **White** surfaces | Page backgrounds, section bands, cards, forms, tables, modals |
| **30% — Secondary** | Structure & identity | **Green** family | Sidebar, navbar/top bars, hero & footer bands, headings, links, icons, selected states, charts (primary series) |
| **10% — Accent** | Attention & action | **Bordo** family | Primary CTAs, active/selected indicators, key numbers (score, rank), urgent badges, certificate seal, ID-card stripe |

**How to apply it (rules of thumb)**
1. The ratio is measured by **visible area on a screen**, not by number of classes.
2. Bordo is scarce on purpose: **max 1–2 bordo elements per viewport** (usually the primary button + one highlight). If everything is bordo, nothing is important.
3. White is a **neutral inside the 60%** (cards on cream). It never replaces cream as the page background.
4. Never use bordo for large backgrounds in the app (only in tiny accents, the certificate seal, and optional hero highlight shapes).
5. Functional colors (success/warning/danger/rank medals) are **exceptions outside the ratio** and must stay under ~2% of any screen.

## 3. Color Tokens

### 3.1 Brand scales (derived only from the 3 source colors)
**Cream (60%)**
| Token | Hex | Use |
|---|---|---|
| `cream-50` | `#FDF6EE` | **Default page background** |
| `cream-100` | `#FAE9D6` | Alternate sections, table header, hover on cream |
| `cream-200` | `#F5DABF` | **Brand cream** — feature bands, banners, ID card body, certificate paper |
| `cream-300` | `#E8C39C` | Borders & dividers on cream |
| `cream-400` | `#D4A574` | Decorative only (illustrations, patterns) — never text |

**Green (30%)**
| Token | Hex | Use |
|---|---|---|
| `green-50` | `#ECF4F3` | Selected row/option background, info tint |
| `green-100` | `#CFE3E1` | Chips, progress track, subtle highlights |
| `green-500` | `#2F7F78` | Charts secondary series, icons on light bg |
| `green-600` | `#17524E` | **Hover** for green elements |
| `green-700` | `#0F3D3A` | **Brand green** — sidebar, navbar, headings, links, secondary buttons |
| `green-900` | `#092A28` | Primary text color, pressed states, deepest backgrounds |

**Bordo (10%)**
| Token | Hex | Use |
|---|---|---|
| `bordo-50` | `#FBEFEF` | Urgent badge background, subtle accent tint |
| `bordo-100` | `#F3D6D8` | Accent chips, focus tint |
| `bordo-500` | `#9A2A36` | Hover for bordo buttons |
| `bordo-700` | `#6C151E` | **Brand bordo** — primary CTA, key highlight, certificate seal |
| `bordo-900` | `#4F0F16` | Pressed state of bordo buttons |

**Neutral**
| Token | Hex | Use |
|---|---|---|
| `white` | `#FFFFFF` | Cards, inputs, modals, table body |
| `ink` | `#092A28` | Primary text (deep green, = `green-900`) |
| `ink-muted` | `#4B5F5D` | Secondary text |
| `ink-placeholder` | `#5F7270` | Placeholders, disabled labels |

### 3.2 Functional colors (outside the 60/30/10 count)
| Token | Hex | Use |
|---|---|---|
| `success` | `#2F855A` (bg `#E6F4EC`) | Passed, saved, valid certificate |
| `warning` | `#B7791F` (bg `#FDF1DC`) | Timer < 5 min, expiring notice |
| `danger` | `#C62828` (bg `#FDECEC`) | Failed, errors, destructive confirm, revoked |
| `rank-gold` | `#C9A227` | Rank #1 medal only |
| `rank-silver` | `#9CA3AF` | Rank #2 medal only |
| `rank-bronze` | `#A8672D` | Rank #3 medal only |
Rank #4 uses `green-700`. Danger is intentionally a **brighter red than bordo** and is always paired with an icon + text, so destructive actions are never confused with the bordo brand CTA.

### 3.3 Chart palette (admin analytics)
Series 1 `green-700` · Series 2 `bordo-700` · Series 3 `green-500` · Series 4 `cream-400` · Series 5 `bordo-500`. Gridlines `cream-300`. Always add labels/patterns — never rely on color alone.

### 3.4 Tailwind config (reference)
```ts
// tailwind.config.ts → theme.extend.colors
colors: {
  cream:  { 50:'#FDF6EE', 100:'#FAE9D6', 200:'#F5DABF', 300:'#E8C39C', 400:'#D4A574' },
  green:  { 50:'#ECF4F3', 100:'#CFE3E1', 500:'#2F7F78', 600:'#17524E', 700:'#0F3D3A', 900:'#092A28' },
  bordo:  { 50:'#FBEFEF', 100:'#F3D6D8', 500:'#9A2A36', 700:'#6C151E', 900:'#4F0F16' },
  ink:    { DEFAULT:'#092A28', muted:'#4B5F5D', placeholder:'#5F7270' },
  success:'#2F855A', warning:'#B7791F', danger:'#C62828',
  rank:   { gold:'#C9A227', silver:'#9CA3AF', bronze:'#A8672D' },
}
// Semantic aliases (use these in components, not raw scales):
// bg-page = cream-50 · bg-surface = white · bg-brand = green-700 · bg-cta = bordo-700
```

### 3.5 Contrast reference (WCAG, approximate)
| Pair | Ratio | Verdict |
|---|---|---|
| `ink` on `cream-50` | ~14 : 1 | ✅ AAA |
| `ink-muted` on `cream-50` | ~6.3 : 1 | ✅ AA |
| `green-700` on `cream-50` / `cream-200` | ~11 / ~9 : 1 | ✅ |
| `bordo-700` on `white` / `cream-200` | ~12 / ~8.9 : 1 | ✅ |
| White on `bordo-700` / `green-700` | ~12 : 1 | ✅ |
| `cream-50` text on `green-700` / `bordo-700` | ~11 / ~11 : 1 | ✅ |
| **`bordo-700` on `green-700` (either direction)** | **~1 : 1** | ❌ **FORBIDDEN** |
| `cream-400` text on `cream-50` | < 2 : 1 | ❌ decorative only |

## 4. Forbidden Combinations
- ❌ Bordo text/icons/buttons on a green background (and green on bordo) — they have almost identical brightness and vibrate. On green surfaces use **cream or white** for text and a **cream button** for the CTA.
- ❌ Bordo as a page, sidebar, or navbar background.
- ❌ Pure black (`#000`) text or pure grey borders — use `ink` and `cream-300`.
- ❌ Introducing blue, purple, or any new hue outside section 3.

## 5. Typography
- **Headings:** `Poppins` (600/700) · **Body/UI:** `Inter` (400/500/600) · **Mono (codes):** `JetBrains Mono` — via `next/font`.
- Headings default to `green-900`/`green-700`; body to `ink`; metadata to `ink-muted`.
| Style | Size / Line height | Weight |
|---|---|---|
| Display (hero) | 48/56 (md: 60/64) | 700 |
| H1 | 32/40 | 700 |
| H2 | 24/32 | 600 |
| H3 | 20/28 | 600 |
| H4 | 18/28 | 600 |
| Body | 16/24 | 400 |
| Small | 14/20 | 400/500 |
| Caption | 12/16 | 500 |

## 6. Spacing, Radius, Shadows
- Spacing: Tailwind 4px base (use 2, 3, 4, 6, 8, 12, 16).
- Page padding: `px-4` mobile, `px-6` tablet, `px-8` desktop; content `max-w-7xl`.
- Radius: `rounded-lg` inputs/buttons, `rounded-xl` cards, `rounded-2xl` ID card/modals (matches the soft rounded look of the palette reference), `rounded-full` avatars/badges.
- Shadows are warm-tinted: `shadow-sm` = `0 1px 2px rgba(9,42,40,.06)`, `shadow-md` = `0 6px 16px rgba(9,42,40,.10)`, `shadow-xl` = `0 20px 40px rgba(9,42,40,.18)`.

## 7. Components
### Buttons
| Type | Style |
|---|---|
| **Primary (10% accent)** | `bg-bordo-700 text-cream-50`, hover `bg-bordo-500`, pressed `bg-bordo-900` |
| **Secondary** | `bg-white text-green-700 border border-green-700`, hover `bg-green-50` |
| **Ghost** | transparent, `text-green-700`, hover `bg-green-100` |
| **Inverse (on green surfaces)** | `bg-cream-200 text-green-900`, hover `bg-cream-100` |
| **Danger** | white bg, `border-danger text-danger` + icon; solid `bg-danger text-white` only on the final confirm step |
Heights: sm 32 / md 40 / lg 48. Disabled: 50% opacity. Loading: spinner + disabled. **One primary button per view.**
### Cards
`bg-white border border-cream-300 rounded-xl shadow-sm p-6`. Clickable: hover `shadow-md` + `-translate-y-0.5`. Highlight card (rare): `bg-cream-200`. Feature/brand card: `bg-green-700 text-cream-50`.
### Inputs & Forms
h-10, white bg, `border-cream-300`, `rounded-lg`, text `ink`, placeholder `ink-placeholder`. Focus: `ring-2 ring-green-700`. Error: `border-danger` + message with icon. Labels above (14px/500, `green-900`). Single column on mobile, two on `md+`.
### Links
`text-green-700 underline-offset-2`, hover underline + `green-600`. (Bordo is **not** used for links.)
### Navbar
Public: `bg-cream-50` + bottom `border-cream-300`, logo in green, CTA bordo. App: `bg-green-700` bar with cream text, Clerk `UserButton`, notice dot in `bordo` → on green use `cream-200` dot with count.
### Sidebar (dashboards)
`bg-green-700`, width 256px; text `cream-100`, icons 20px; hover `bg-green-600`; **active item**: a cream pill (`bg-cream-200 text-green-900`) with a small `bordo-700` dot inside the pill (bordo sits on cream, never directly on green). Mobile: drawer.
### Tables
Header `bg-cream-100 text-green-900` uppercase caption; body `bg-white`; row 48px; divider `cream-300`; hover `bg-cream-50`; selected `bg-green-50`; sticky header; horizontal scroll on mobile; pagination footer.
### Modals
White, `rounded-2xl`, `shadow-xl`, backdrop `bg-green-900/60`, focus trap, ESC closes.
### Badges
`rounded-full px-2.5 py-0.5 text-xs font-medium`.
| Badge | Style |
|---|---|
| Neutral / Normal | `bg-cream-200 text-green-900` |
| Info / Important | `bg-green-100 text-green-700` |
| Urgent | `bg-bordo-50 text-bordo-700` + icon |
| Success / Pass | `bg-[#E6F4EC] text-success` + check icon |
| Warning | `bg-[#FDF1DC] text-warning` |
| Fail / Revoked | `bg-[#FDECEC] text-danger` + x icon |
### Icons
`lucide-react` only; 16/20/24px; stroke 1.75; default `green-700`.

## 8. Key Screens — 60/30/10 Map
| Screen | 60% (cream/white) | 30% (green) | 10% (bordo) |
|---|---|---|---|
| **Landing** | `cream-50` page, `cream-200` feature band, white cards | Hero text/headings, green "how it works" band, green footer | "Get Started" CTA, one highlight shape/underline |
| **Student/Teacher dashboard** | `cream-50` page, white cards | Sidebar, top bar, headings, icons, progress track | Primary button, key stat (e.g., rank number), active dot |
| **Virtual ID Card** | `cream-200` card body | Green header block + name/labels | Bordo stripe + "ACTIVE" seal (small) |
| **Exam runner** | `cream-50` bg, white question card | Slim green top bar, selected option (`green-50` + `green-700` border), palette "answered" | **Submit** button only; timer = green → warning → danger |
| **Result page** | cream bg, white cards | Headings, score ring track | Score number + **Download PDF** button |
| **Certificate page** | cream bg, white certificate cards | Card headings, borders `green-700` | Seal icon, Download button |
| **Tasks page** | cream bg, white task cards | Headings, active filter chips, progress track | One primary action per card ("Submit"), `+pts` highlight on the total |
| **Live Ranking** | cream bg, white rows | Header band, rank #4 chip, row text | Rank #1 points value, "Your rank" badge; medals use rank colors |
| **Notice board** | cream bg, white notices | Headings, filter chips (active), author chip | Pinned/Urgent accent only |
| **Aarsh Intelligence** | white panel, AI bubbles `cream-100` | Chat header `green-700`, user bubbles `green-700` + cream text | Send button, small "AI" badge |
| **Admin** | cream bg, white tables/cards | Sidebar, headers, chart series 1 | Primary action, alert counts, chart series 2 |

### Virtual ID Card spec
340×540 portrait, `rounded-2xl shadow-xl`. Top 40%: `green-700 → green-900` gradient with logo (cream). Circular photo 96px, 4px `cream-200` ring. Name (H3, `green-900`), student code (mono), department/batch rows (`ink-muted`), QR 112px on white tile, "Valid until" caption, thin `bordo-700` bottom stripe (≈4% of area), subtle cream pattern at 6% opacity.

### Live Ranking spec (Task Points)
- Title "Top Performers", subtitle "Ranked by Task Points". Filter: Overall / by Course.
- Podium-style Top 4: #1 center-large card (white, `rank-gold` medal, **bordo points value**), #2 / #3 / #4 smaller cards (silver / bronze / `green-700`).
- Each card: avatar, name, **points** (`1,250 pts`), small caption `12 tasks completed` (`ink-muted`).
- "Live" pulse dot in `success`. "Your rank" sticky card `bg-green-700 text-cream-50` showing rank + points.
- When the logged-in student earns points: toast `+50 pts — {Task name}`, their points count up over 600ms, rows re-order with a 300ms slide (all respect `prefers-reduced-motion`).
- Empty state: "No points yet — complete a task to appear here."

### Task card & Points chip spec
- Task card: white, `border-cream-300`, `rounded-xl`; title (H4 `green-900`), course name (`ink-muted`), due date caption, **points chip**, status badge, one action button.
- **Points chip:** `+50 pts` — `bg-cream-200 text-green-900` (not yet earned); earned: `bg-green-100 text-green-700` + check icon.
- Task status badges: Open → `bg-green-100 text-green-700` · Pending review → warning · Completed → success + check · Rejected → danger + x · Revoked → danger-outline.
- Action buttons: Assignment "Submit for review" (primary bordo); Exam task "Go to exam" (secondary green). Only **one** primary button per card/view.
- Teacher approval queue: table (student, task, note/link, submitted at) with `Approve` (primary) and `Reject` (danger-outline) actions; approving shows toast "Points awarded".

### Exam runner spec
No sidebar. Sticky `green-700` top bar (title in cream, timer chip: `cream-200` bg / `green-900` text → `warning` < 5 min → `danger` < 1 min with `aria-live`). Question palette: answered `green-700`, current ring `bordo-700`, unanswered `cream-100` with `cream-300` border. Mobile: palette as bottom sheet.

## 9. PDF Documents (generated in backend)
Result and certificate PDFs must match the web brand.
- **Certificate (A4 landscape):** paper `cream-200` (or white for print-friendly variant), double border `green-700` (outer 3pt / inner 1pt), title in Poppins `green-900`, student name large `bordo-700`, details `ink`, circular **bordo seal** bottom center, QR + code (mono) bottom right, signature lines `green-700`.
- **Result (A4 portrait):** white page, green header band with cream logo/title, table header `cream-100`, pass/fail pill (success/danger), score highlight `bordo-700`, QR/verification footer in `ink-muted`.
- Fonts embedded (Poppins, Inter). Include a monochrome-safe layout (information must not depend on color).

## 10. Loading, Empty, Error States
- **Loading:** skeletons in `cream-100 → cream-200` shimmer; button spinners in current text color.
- **Empty:** centered icon (48px, `cream-400`), title (`green-900`), one-line help, primary bordo CTA.
- **Error:** inline alert `bg-[#FDECEC] text-danger` with icon + retry; full-page 403/404/500 on `cream-50` with green heading and bordo "Go home" button.
- **Success:** toast top-right (`white` card, green check, `border-success`), auto-dismiss 4 s.

## 11. Hover / Focus / Animation
- Hover: color shift 150ms; cards lift.
- Focus (always visible): `ring-2 ring-green-700 ring-offset-2 ring-offset-cream-50`; on green surfaces use `ring-cream-200`.
- Animations: `transition-all duration-200 ease-out`; page fade-in 200ms; respect `prefers-reduced-motion`.

## 12. Responsive Breakpoints & Mobile Rules
`sm 640` · `md 768` · `lg 1024` · `xl 1280` · `2xl 1536`. Mobile-first.
- Touch targets ≥ 44×44px; sidebar → drawer or bottom tab bar (≤ 5 items).
- Tables scroll horizontally or become card lists.
- Chat widget goes full-screen; forms single column with sticky primary action when long.
- Keep the 60/30/10 balance on small screens: green top bar stays slim so cream remains dominant.

## 13. Accessibility
Contrast ≥ 4.5:1 for text (see 3.5), visible focus on every interactive element, labels/aria for icon-only buttons, `aria-live` for timer & ranking, reduced-motion support, never rely on color alone (icons + text for pass/fail/urgent).

## 14. Palette QA Checklist (run in Phase 2 and Phase 13)
- [ ] Screenshot each key page; color-pick/eyeball ≈ 60% cream+white, ≈ 30% green, ≈ 10% bordo.
- [ ] No more than 1–2 bordo elements per viewport.
- [ ] No bordo-on-green anywhere.
- [ ] Only tokens from section 3 are used (no raw hex in components).
- [ ] All text pairs pass contrast (section 3.5).
- [ ] PDFs (result, certificate) match section 9.
