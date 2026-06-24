# Prompt for Claude Design — DataFlow AI

Copy everything in the box below and paste it into Claude. It asks for a
high-fidelity, **light-themed**, interactive design with a 3D hero and a clear,
guided user experience.

---

You are a senior product designer. Design a **stunning, premium, LIGHT-THEMED**
web interface for my final-year Data Science project and build it as a single
self-contained, responsive **HTML file** (Tailwind via CDN + vanilla JS, and
**Three.js from cdnjs** for the 3D). Make it feel like a polished SaaS product
from a top design studio — elegant, modern, and immediately easy to understand.

## The product
"**DataFlow AI**" — an automated data-science platform. A user uploads a tabular
dataset (CSV/Excel) and a team of specialised agents runs a full workflow:
**Cleaning → Exploratory Data Analysis → Statistical testing → Machine learning
→ Reporting.** Everything is real, computed, reproducible data science (pandas,
SciPy, scikit-learn). It is NOT a chatbot — it is a data-science pipeline with a
beautiful interface.

## Audience & tone
A senior data scientist would be proud to present this. Professional, refined,
trustworthy, and a little bit "wow". Clean and intelligent, not flashy or
cartoonish.

## HARD CONSTRAINTS (important)
- **LIGHT theme only** — warm white / soft ivory backgrounds. **No dark mode.**
- **Clarity first.** A first-time visitor must instantly understand what to do.
  There must be one obvious primary call-to-action, and a clear "Getting started
  in 3 steps" path. No empty, confusing screens.
- Accessible: strong contrast, readable type, sensible focus states.
- Responsive: looks great on laptop and mobile.

## Visual language
- **Palette (light, elegant, vibrant-but-refined):** warm white base
  (#FBFBFA / #FFFFFF surfaces), deep ink text (#13132B), a confident primary
  accent of **violet/indigo (#5B5BF0)**, a warm secondary of **coral/rose
  (#FF6B6B or #F2789F)**, and a fresh **teal (#15B8A6)** for data viz. Use soft
  pastel tints of these for backgrounds and gradients. Tasteful, not loud.
- **Typography:** an expressive display font for headlines (e.g. "Space
  Grotesk", "Clash Display", or "Fraunces" for an editorial touch) paired with a
  clean sans (e.g. "Inter") for body. Big, confident headings.
- **Components:** rounded cards (16–20px radius) with soft shadows, pill
  buttons, gentle gradient accents, glass-like translucent panels over the hero,
  small chip/tag labels, and elegant KPI/stat cards.
- **Motion & delight:** smooth hover lifts, animated number count-ups on stats,
  subtle fade/slide-in on scroll, a gradient that softly shifts. Keep it smooth
  and classy, never distracting.

## The 3D (make it a centrepiece)
A beautiful, interactive **3D "data manifold"** in the hero using Three.js:
a glowing point cloud / particle field forming an organic cluster, optionally
wrapped around a soft wireframe shape, slowly rotating with gentle mouse
parallax, in the light palette (violet/teal points on white, soft depth).
It should feel premium and alive — the visual signature of the product.

## Screens to design (in one scrolling page or tabbed app shell)
1. **Hero / landing** — product name, one-line value prop, the 3D manifold, and
   a clear primary CTA ("Try with sample data") plus secondary ("Upload your
   data"). Include a small "Getting started: 1) Load data 2) Explore 3) Model"
   strip so it's obvious how to use it.
2. **The pipeline** — 5 elegant cards (Cleaning, EDA, Testing, Modeling,
   Reporting) each with an icon, one line, and the tech used.
3. **Workspace shell** — a clean app layout with a sidebar and tabs:
   **Data Preview · EDA · Modeling · Chat**. Show what each looks like.
4. **EDA dashboard** — KPI cards (rows, columns, missing %, duplicates), a
   beautiful correlation heatmap, a distribution chart, and a tidy statistics
   table.
5. **Modeling results** — a model leaderboard, big headline metric (e.g. F1 /
   R²), a horizontal feature-importance bar chart, and a confusion matrix.

## Deliverable
One polished, working HTML file I can open in a browser, with the 3D animating
and realistic placeholder data (use an "employee promotion" dataset theme:
columns like age, department, salary, performance_score, satisfaction,
promoted). Prioritise visual quality and clarity. Surprise me with the level of
craft.

---

### Tips when you get the result
- If it's too plain, reply: *"make the hero bigger and more immersive, add the
  animated count-up stats, and make the 3D particle field denser and more
  glowing."*
- If it's unclear, reply: *"add clearer onboarding — a prominent 'Try with
  sample data' button and a 3-step guide at the top."*
- When you pick a version you love, send it back to me (Cowork) and I'll rebuild
  the real Streamlit app to match it.
