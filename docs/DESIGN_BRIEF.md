# DataFlow AI — Design Brief

A copy-paste brief for generating or extending the visual design. Hand this to
any design tool (or to Claude) to produce on-brand screens, slides, or assets.

---

## 1. One-line direction

> A **clean, light, editorial** interface for a senior data scientist — calm
> whitespace, refined typography, a single confident accent, and **subtle real
> 3D** (a rotating data manifold) that signals "this is about data," never
> decoration for its own sake.

Think: a top-tier consultancy report meets a modern AI research lab. Restraint,
precision, and craft. The opposite of a cluttered dashboard.

## 2. Mood & principles

- **Editorial, not corporate-generic.** Big confident headlines, lots of air,
  strong typographic hierarchy. Content leads; chrome recedes.
- **One accent, used sparingly.** Electric indigo for actions and emphasis only.
- **Depth through softness.** Hairline borders + soft shadows, never heavy boxes.
- **3D as signal, not noise.** One tasteful 3D object (geometric + point cloud),
  slow motion, low opacity. It should feel premium and quiet.
- **Reproducible & trustworthy** vibe: monospace for numbers/metrics where it
  helps legibility; everything aligned to a grid.

## 3. Color tokens

| Token | Hex | Use |
|---|---|---|
| `paper` | `#FBFBF9` | page background (warm white) |
| `surface` | `#FFFFFF` | cards, panels |
| `ink` | `#0F1222` | primary text, headlines |
| `muted` | `#6B7280` | secondary text, captions |
| `line` | `#ECECE6` | hairline borders, dividers |
| `accent` | `#4F46E5` | primary actions, links, emphasis |
| `accent-soft` | `#EEF0FF` | hover fills, accent backgrounds |
| `accent-2` | `#0D9488` | secondary data accent (teal), charts only |

Background uses two very faint radial gradient blooms (indigo top-right, teal
top-left) over paper, for subtle depth.

## 4. Typography

- **Display / headings:** `Space Grotesk` (600/700), tight tracking (-0.02em).
- **Body / UI:** `Inter` (400–600).
- **Kicker** (eyebrow label above headings): Space Grotesk, UPPERCASE,
  letter-spacing 0.18em, 0.72rem, accent color.
- Scale: H1 ~2.45rem / H2 ~1.55rem / H3 ~1.18rem / body 1rem / caption 0.85rem.

## 5. Components

- **Buttons:** pill (radius 999px), white with hairline border by default; on
  hover → accent text + `accent-soft` fill + 1px lift. Primary = solid indigo.
- **Cards:** white, 16px radius, 1px `line` border, soft shadow
  `0 8px 24px rgba(15,18,34,.06)`, ~16px padding.
- **Metrics / KPIs:** rendered as cards; value in Space Grotesk bold, label in
  `muted`.
- **Tabs:** quiet text tabs; active tab gets an ink label + 2px indigo underline.
- **Tables / dataframes:** wrapped in a bordered, rounded, shadowed container.
- **Chips:** small pill tags for tech labels (e.g. `scikit-learn`), white with
  hairline border, accent for emphasised words.
- **Section header pattern:** `kicker` → `H2 title` → `muted subtitle`.

## 6. The 3D hero

- **Object:** a wireframe icosahedron (indigo, ~0.28 opacity) with a smaller
  inner wireframe (teal), wrapped in an orbiting **point cloud** of ~900 points
  (the "data manifold").
- **Motion:** very slow auto-rotation; gentle mouse parallax; exponential fog
  for depth on the light background. Transparent canvas so it sits on paper.
- **Layout:** 3D pushed to the right; left side holds the kicker + "DataFlow AI"
  headline + one-sentence description + capability chips.
- **Tech:** Three.js r128, rendered in an isolated iframe (Streamlit
  `components.html`). Keep geometries r128-safe (no `CapsuleGeometry`).
- **Tone:** quiet and expensive. If it ever feels flashy, reduce opacity/speed.

## 7. Do / Don't

- ✅ Whitespace, hairlines, one accent, slow 3D, aligned grid, real numbers.
- ❌ Neon gradients everywhere, drop-shadows on text, multiple accent colors,
  fast/spinning 3D, emoji-as-icons, dense dashboards with no breathing room.

## 8. Implementation notes (this repo)

- Global stylesheet + 3D hero live in `ui/theme.py`
  (`inject_theme()`, `hero_3d()`, `section()`).
- Base theme (light, indigo primary) is set in `.streamlit/config.toml`.
- To restyle a screen, call `theme.section(title, kicker, sub)` for headers and
  rely on the injected CSS for cards/metrics/tabs/buttons.

## 9. Prompt you can paste into Claude

> Design a clean, light, **editorial** UI for a data-science web app called
> "DataFlow AI" aimed at a senior data scientist. Warm-white background
> (#FBFBF9), ink text (#0F1222), a single electric-indigo accent (#4F46E5),
> hairline borders (#ECECE6), soft shadows, generous whitespace. Typography:
> Space Grotesk for headings (tight tracking), Inter for body, an uppercase
> letter-spaced indigo "kicker" above each section title. Components: pill
> buttons, white rounded cards, KPI cards, quiet underlined tabs, rounded
> bordered tables, small chip tags. Include a tasteful **3D hero**: a slowly
> rotating wireframe icosahedron surrounded by an orbiting point cloud (a "data
> manifold"), low opacity, soft fog, mouse parallax, on a transparent canvas,
> 3D on the right and headline on the left. Keep it calm and premium — one
> accent, slow motion, lots of air. Deliver screens for: landing/hero, a data
> workspace with tabs (Data, EDA, Modeling, Chat), an EDA dashboard with stat
> cards + correlation heatmap, and a modeling results view with a model
> leaderboard, feature-importance bar chart, and confusion matrix.
