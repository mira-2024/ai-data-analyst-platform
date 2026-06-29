"""
ui/theme.py -- DataFlow AI design system. v2: Professional Blue.

Dark sidebar + clean white workspace. Navy/blue palette.
Feels like Retool, Metabase, or enterprise Grafana -- not a student project.
"""

from __future__ import annotations
import streamlit as st
import streamlit.components.v1 as components

# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------
PALETTE = {
    "bg":       "#F0F4FA",
    "surface":  "#FFFFFF",
    "ink":      "#0F172A",
    "ink2":     "#334155",
    "muted":    "#64748B",
    "line":     "#E2E8F0",
    "blue":     "#1D4ED8",
    "blue_lt":  "#3B82F6",
    "blue_soft":"#EFF6FF",
    "cyan":     "#0EA5E9",
    "sidebar":  "#0F172A",
}

_FONTS = ("https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800"
          "&family=Plus+Jakarta+Sans:wght@500;600;700;800"
          "&family=JetBrains+Mono:wght@400;500&display=swap")

_CSS = f"""
<style>
@import url('{_FONTS}');

:root {{
  --bg:#F0F4FA; --surface:#FFFFFF; --ink:#0F172A; --ink2:#334155;
  --muted:#64748B; --line:#E2E8F0;
  --blue:#1D4ED8; --blue-lt:#3B82F6; --blue-soft:#EFF6FF;
  --cyan:#0EA5E9; --sidebar:#0F172A;
  --radius:10px;
  --shadow:0 1px 3px rgba(15,23,42,.06), 0 8px 24px rgba(15,23,42,.06);
  --shadow-md:0 4px 16px rgba(15,23,42,.10), 0 1px 4px rgba(15,23,42,.06);
}}

/* ── Base ── */
html, body, [class*="css"] {{
  font-family: 'Inter', system-ui, sans-serif;
  color: var(--ink);
}}
.stApp {{
  background: var(--bg);
}}
.block-container {{
  padding: 1.5rem clamp(1.25rem, 3vw, 2.5rem) 3rem;
  max-width: 100%;
}}
[data-testid="stHeader"] {{ background: transparent; }}
#MainMenu, footer {{ visibility: hidden; }}

/* ── Typography ── */
h1, h2, h3, h4 {{
  font-family: 'Plus Jakarta Sans', 'Inter', sans-serif;
  letter-spacing: -.028em;
  color: var(--ink);
}}
h1 {{ font-weight: 800; font-size: 2rem; }}
h2 {{ font-weight: 700; font-size: 1.5rem; }}
h3 {{ font-weight: 600; font-size: 1.15rem; }}
p, li, .stMarkdown {{ color: var(--ink2); line-height: 1.65; }}
a {{ color: var(--blue-lt); text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
code, pre {{ font-family: 'JetBrains Mono', monospace; }}

/* ── Sidebar -- dark navy ── */
section[data-testid="stSidebar"] {{
  background: var(--sidebar) !important;
  border-right: 1px solid rgba(255,255,255,.07) !important;
}}
section[data-testid="stSidebar"] * {{
  color: #CBD5E1 !important;
}}
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] strong {{
  color: #F1F5F9 !important;
}}
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {{
  color: #94A3B8 !important;
  font-size: .875rem;
}}
section[data-testid="stSidebar"] hr {{
  border-color: rgba(255,255,255,.08) !important;
}}
section[data-testid="stSidebar"] [data-testid="stMetric"] {{
  background: rgba(255,255,255,.05) !important;
  border: 1px solid rgba(255,255,255,.08) !important;
}}
section[data-testid="stSidebar"] [data-testid="stMetricLabel"] {{
  color: #94A3B8 !important;
}}
section[data-testid="stSidebar"] [data-testid="stMetricValue"] {{
  color: #F1F5F9 !important;
}}
section[data-testid="stSidebar"] .stButton > button {{
  background: rgba(59,130,246,.15) !important;
  border: 1px solid rgba(59,130,246,.30) !important;
  color: #93C5FD !important;
  border-radius: 8px !important;
}}
section[data-testid="stSidebar"] .stButton > button:hover {{
  background: rgba(59,130,246,.25) !important;
  color: #BFDBFE !important;
}}
section[data-testid="stSidebar"] [data-testid="stFileUploader"] {{
  background: rgba(255,255,255,.04) !important;
  border: 1px dashed rgba(255,255,255,.15) !important;
  border-radius: 10px !important;
}}
section[data-testid="stSidebar"] [data-baseweb="select"] > div {{
  background: rgba(255,255,255,.06) !important;
  border-color: rgba(255,255,255,.12) !important;
  color: #CBD5E1 !important;
}}
section[data-testid="stSidebar"] [data-testid="stCheckbox"] span {{
  color: #94A3B8 !important;
}}

/* ── Buttons ── */
.stButton > button {{
  border-radius: 8px;
  border: 1px solid var(--line);
  background: var(--surface);
  color: var(--ink2);
  font-weight: 600;
  font-size: .9rem;
  padding: .55rem 1.1rem;
  transition: all .15s ease;
  box-shadow: 0 1px 2px rgba(15,23,42,.05);
}}
.stButton > button:hover {{
  border-color: var(--blue-lt);
  color: var(--blue);
  background: var(--blue-soft);
  box-shadow: 0 4px 12px rgba(29,78,216,.12);
  transform: translateY(-1px);
}}
.stButton > button[kind="primary"] {{
  background: var(--blue);
  color: #fff;
  border-color: var(--blue);
  box-shadow: 0 4px 14px rgba(29,78,216,.35);
}}
.stButton > button[kind="primary"]:hover {{
  background: #1a43b8;
  box-shadow: 0 8px 22px rgba(29,78,216,.45);
  transform: translateY(-1px);
}}

/* ── Metrics ── */
[data-testid="stMetric"] {{
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 1.1rem 1.25rem;
  box-shadow: var(--shadow);
  border-top: 3px solid var(--blue);
}}
[data-testid="stMetricLabel"] {{
  color: var(--muted);
  font-size: .8rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: .05em;
}}
[data-testid="stMetricValue"] {{
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-weight: 800;
  font-size: 1.9rem;
  color: var(--ink);
  letter-spacing: -.03em;
}}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {{
  gap: 2px;
  border-bottom: 2px solid var(--line);
  background: transparent;
  padding: 0;
}}
.stTabs [data-baseweb="tab"] {{
  background: transparent;
  border: 0;
  color: var(--muted);
  font-weight: 600;
  font-size: .9rem;
  padding: .65rem 1.1rem;
  border-radius: 0;
  transition: color .15s;
}}
.stTabs [data-baseweb="tab"]:hover {{
  color: var(--ink);
  background: rgba(29,78,216,.04);
}}
.stTabs [aria-selected="true"] {{
  color: var(--blue) !important;
  border-bottom: 2px solid var(--blue) !important;
  margin-bottom: -2px;
}}
[data-baseweb="tab-highlight"] {{ background: transparent !important; }}
[data-baseweb="tab-border"] {{ display: none !important; }}

/* ── Cards & surfaces ── */
[data-testid="stDataFrame"],
[data-testid="stTable"] {{
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  overflow: hidden;
  box-shadow: var(--shadow);
}}

/* ── Inputs ── */
[data-baseweb="select"] > div,
.stTextInput > div > div {{
  border-radius: 8px !important;
  border-color: var(--line) !important;
  background: var(--surface) !important;
}}
[data-baseweb="select"] > div:focus-within,
.stTextInput > div > div:focus-within {{
  border-color: var(--blue-lt) !important;
  box-shadow: 0 0 0 3px rgba(59,130,246,.15) !important;
}}
[data-testid="stFileUploader"] {{
  background: var(--surface);
  border: 1.5px dashed #CBD5E1;
  border-radius: var(--radius);
  padding: .5rem;
}}
[data-testid="stFileUploader"]:hover {{
  border-color: var(--blue-lt);
  background: var(--blue-soft);
}}

/* ── Chat ── */
[data-testid="stChatMessage"] {{
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 12px;
  box-shadow: var(--shadow);
}}

/* ── Alerts ── */
[data-testid="stAlert"] {{
  border-radius: var(--radius);
  border: 1px solid var(--line);
}}

/* ── Labels / captions ── */
[data-testid="stCaptionContainer"],
.stCaption {{ color: var(--muted) !important; font-size: .82rem !important; }}
[data-testid="stWidgetLabel"] label,
.stSelectbox label,
.stFileUploader label {{
  color: var(--ink2) !important;
  font-weight: 600 !important;
  font-size: .875rem !important;
}}

/* ── Kicker / section labels ── */
.kicker {{
  font-family: 'JetBrains Mono', monospace;
  text-transform: uppercase;
  letter-spacing: .12em;
  font-size: .7rem;
  font-weight: 500;
  color: var(--blue-lt);
  margin-bottom: .2rem;
}}
.section-sub {{
  color: var(--muted);
  font-size: .95rem;
  margin-top: .25rem;
  line-height: 1.55;
}}
.rule {{ height: 1px; background: var(--line); border: 0; margin: 1.2rem 0; }}
.chip {{
  font-family: 'JetBrains Mono', monospace;
  font-size: .7rem;
  font-weight: 500;
  color: var(--blue);
  background: var(--blue-soft);
  border: 1px solid #BFDBFE;
  border-radius: 5px;
  padding: 3px 8px;
}}

/* ── Page-in animation ── */
.main .block-container {{
  animation: dfRise .4s cubic-bezier(.16,.84,.44,1) both;
}}
@keyframes dfRise {{
  from {{ opacity: 0; transform: translateY(6px); }}
  to   {{ opacity: 1; transform: translateY(0); }}
}}

/* ── Scrollbar ── */
::-webkit-scrollbar {{ width: 6px; height: 6px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{ background: #CBD5E1; border-radius: 3px; }}
::-webkit-scrollbar-thumb:hover {{ background: #94A3B8; }}

/* ── Responsive ── */
@media (max-width: 680px) {{
  .block-container {{ padding-left: 1rem !important; padding-right: 1rem !important; }}
  [data-testid="stMetricValue"] {{ font-size: 1.5rem; }}
}}
iframe {{ border: 0 !important; }}
</style>
"""


def inject_theme() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def section(title: str, kicker: str = "", sub: str = "") -> None:
    html = "<div style='margin:.3rem 0 .9rem;'>"
    if kicker:
        html += f"<div class='kicker'>{kicker}</div>"
    html += (
        f"<h2 style='margin:.1rem 0 0;font-family:\"Plus Jakarta Sans\",sans-serif;"
        f"font-weight:700;font-size:1.45rem;letter-spacing:-.025em;color:#0F172A;'>"
        f"{title}</h2>"
    )
    if sub:
        html += f"<div class='section-sub'>{sub}</div>"
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# HERO_STATS (inline markdown injected in landing col1)
# ---------------------------------------------------------------------------
HERO_STATS = """
<div style="display:flex;gap:32px;border-top:1px solid #E2E8F0;padding-top:20px;margin-top:22px;">
  <div>
    <div style="font-family:'Plus Jakarta Sans',sans-serif;font-weight:800;font-size:28px;
                color:#0F172A;letter-spacing:-.03em;">5</div>
    <div style="font-size:12px;color:#64748B;font-weight:500;text-transform:uppercase;
                letter-spacing:.06em;margin-top:2px;">AI Agents</div>
  </div>
  <div>
    <div style="font-family:'Plus Jakarta Sans',sans-serif;font-weight:800;font-size:28px;
                color:#0F172A;letter-spacing:-.03em;">100%</div>
    <div style="font-size:12px;color:#64748B;font-weight:500;text-transform:uppercase;
                letter-spacing:.06em;margin-top:2px;">Reproducible</div>
  </div>
  <div>
    <div style="font-family:'Plus Jakarta Sans',sans-serif;font-weight:800;font-size:28px;
                color:#0F172A;letter-spacing:-.03em;">0</div>
    <div style="font-size:12px;color:#64748B;font-weight:500;text-transform:uppercase;
                letter-spacing:.06em;margin-top:2px;">Lines of code</div>
  </div>
</div>
"""

# ---------------------------------------------------------------------------
# Hero canvas -- animated data visualization (professional blue)
# ---------------------------------------------------------------------------
_HERO_CANVAS = """<!doctype html><html><head><meta charset='utf-8'>
<style>
*{box-sizing:border-box;margin:0;}
html,body{background:transparent;overflow:hidden;width:100%;height:100%;}
canvas{width:100%;height:100%;display:block;}
</style>
</head><body>
<canvas id='cv'></canvas>
<script>
(function(){
  var cv=document.getElementById('cv');
  var ctx=cv.getContext('2d');
  var W,H,nodes=[],edges=[],mx=0,my=0;
  var BLUE='#1D4ED8',CYAN='#0EA5E9',LINE='rgba(29,78,216,0.12)';

  function resize(){
    var r=window.devicePixelRatio||1;
    W=cv.offsetWidth;H=cv.offsetHeight;
    cv.width=W*r;cv.height=H*r;
    ctx.scale(r,r);
    build();
  }

  function build(){
    nodes=[];edges=[];
    var n=Math.floor(W*H/5000)+18;
    for(var i=0;i<n;i++){
      nodes.push({
        x:Math.random()*W, y:Math.random()*H,
        vx:(Math.random()-.5)*.35, vy:(Math.random()-.5)*.35,
        r:Math.random()*2+1.5,
        color:Math.random()>.5?BLUE:CYAN,
        alpha:Math.random()*.5+.4
      });
    }
  }

  function draw(){
    ctx.clearRect(0,0,W,H);

    // connect nearby
    for(var i=0;i<nodes.length;i++){
      for(var j=i+1;j<nodes.length;j++){
        var a=nodes[i],b=nodes[j];
        var d=Math.hypot(a.x-b.x,a.y-b.y);
        if(d<130){
          ctx.beginPath();
          ctx.strokeStyle='rgba(29,78,216,'+(0.12*(1-d/130))+')';
          ctx.lineWidth=.8;
          ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);
          ctx.stroke();
        }
      }
      // mouse connection
      var dx=nodes[i].x-mx,dy=nodes[i].y-my;
      var dm=Math.hypot(dx,dy);
      if(dm<160){
        ctx.beginPath();
        ctx.strokeStyle='rgba(14,165,233,'+(0.22*(1-dm/160))+')';
        ctx.lineWidth=1;
        ctx.moveTo(nodes[i].x,nodes[i].y);ctx.lineTo(mx,my);
        ctx.stroke();
      }
    }

    // draw nodes
    for(var i=0;i<nodes.length;i++){
      var n=nodes[i];
      ctx.beginPath();
      ctx.arc(n.x,n.y,n.r,0,Math.PI*2);
      ctx.fillStyle=n.color.replace(')',','+n.alpha+')').replace('rgb','rgba').replace('#','rgba(').replace('1D4ED8','29,78,216').replace('0EA5E9','14,165,233');

      // simpler approach
      if(n.color===BLUE){
        ctx.fillStyle='rgba(29,78,216,'+n.alpha+')';
      } else {
        ctx.fillStyle='rgba(14,165,233,'+n.alpha+')';
      }
      ctx.fill();
    }

    // mouse dot
    ctx.beginPath();
    ctx.arc(mx,my,4,0,Math.PI*2);
    ctx.fillStyle='rgba(14,165,233,.7)';
    ctx.fill();
  }

  function update(){
    for(var i=0;i<nodes.length;i++){
      var n=nodes[i];
      n.x+=n.vx; n.y+=n.vy;
      if(n.x<0||n.x>W) n.vx*=-1;
      if(n.y<0||n.y>H) n.vy*=-1;
    }
  }

  function loop(){draw();update();requestAnimationFrame(loop);}

  cv.addEventListener('mousemove',function(e){
    var b=cv.getBoundingClientRect();
    mx=(e.clientX-b.left)*(W/b.width);
    my=(e.clientY-b.top)*(H/b.height);
  });

  window.addEventListener('resize',resize);
  resize();
  loop();
})();
</script>
</body></html>"""


def hero_canvas(height: int = 500) -> None:
    components.html(_HERO_CANVAS, height=height, scrolling=False)


def hero(height: int = 460) -> None:
    """Full hero (not used in split layout — kept for API compatibility)."""
    hero_canvas(height)


# ---------------------------------------------------------------------------
# Landing sections
# ---------------------------------------------------------------------------
_PIPE = [
    ("01", "Cleaner", "Handles missing values, duplicates, type coercion and outliers with auditable rules.", "pandas"),
    ("02", "Analyst", "Profiles distributions, correlations and statistical significance across all columns.", "scipy"),
    ("03", "Modeler", "Trains and cross-validates candidate models, picks the best by held-out score.", "scikit-learn"),
    ("04", "Explainer", "Computes SHAP values to show which features drive each prediction.", "shap"),
    ("05", "Reporter", "Assembles every finding into a structured, human-readable report.", "report"),
]


def _pipe_cards() -> str:
    colors = [("#1D4ED8", "#EFF6FF", "#BFDBFE"),
              ("#0EA5E9", "#F0F9FF", "#BAE6FD"),
              ("#1D4ED8", "#EFF6FF", "#BFDBFE"),
              ("#0EA5E9", "#F0F9FF", "#BAE6FD"),
              ("#1D4ED8", "#EFF6FF", "#BFDBFE")]
    out = ""
    for i, (no, title, desc, tech) in enumerate(_PIPE):
        ink, tint, border = colors[i]
        out += (
            f"<div class='pc'>"
            f"<div class='pc-top'>"
            f"<div class='ic' style='background:{tint};border:1px solid {border};'>"
            f"<svg width='16' height='16' viewBox='0 0 16 16' fill='none'>"
            f"<circle cx='8' cy='8' r='5' stroke='{ink}' stroke-width='2'/>"
            f"<circle cx='8' cy='8' r='2' fill='{ink}'/>"
            f"</svg></div>"
            f"<span class='no'>{no}</span></div>"
            f"<div class='pt'>{title}</div>"
            f"<div class='pd'>{desc}</div>"
            f"<div style='margin-top:14px;'>"
            f"<span class='tech' style='background:{tint};border-color:{border};color:{ink};'>{tech}</span>"
            f"</div></div>"
        )
    return out


_LANDING = """<!doctype html><html><head><meta charset='utf-8'>
<link href='https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Plus+Jakarta+Sans:wght@600;700;800&family=JetBrains+Mono:wght@400;500&display=swap' rel='stylesheet'>
<style>
*{{box-sizing:border-box;margin:0;padding:0;}}
html,body{{background:transparent;font-family:'Inter',sans-serif;color:#0F172A;}}
.wrap{{max-width:1500px;margin:0 auto;padding:0 4px;}}

/* 3-step strip */
.steps{{display:grid;grid-template-columns:repeat(3,1fr);background:#fff;
  border:1px solid #E2E8F0;border-radius:12px;
  box-shadow:0 1px 3px rgba(15,23,42,.06),0 8px 24px rgba(15,23,42,.06);
  margin-bottom:40px;overflow:hidden;}}
.step{{display:flex;gap:14px;align-items:flex-start;padding:20px 24px;}}
.step+.step{{border-left:1px solid #E2E8F0;}}
.num{{flex:none;width:36px;height:36px;border-radius:8px;background:#EFF6FF;
  color:#1D4ED8;display:flex;align-items:center;justify-content:center;
  font-family:'Plus Jakarta Sans';font-weight:700;font-size:14px;}}
.st-t{{font-family:'Plus Jakarta Sans';font-weight:700;font-size:15px;
  color:#0F172A;margin-bottom:4px;}}
.st-d{{font-size:13px;color:#64748B;line-height:1.5;}}

/* Pipeline section */
.kick{{font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:500;
  letter-spacing:.12em;text-transform:uppercase;color:#3B82F6;margin-bottom:10px;}}
h2{{font-family:'Plus Jakarta Sans';font-weight:800;
  font-size:clamp(22px,2.8vw,34px);line-height:1.1;
  letter-spacing:-.03em;margin:0 0 10px;color:#0F172A;}}
.lead{{font-size:15px;line-height:1.6;color:#64748B;margin:0 0 30px;max-width:580px;}}
.grid{{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;}}
.pc{{background:#fff;border:1px solid #E2E8F0;border-radius:10px;padding:20px 18px;
  box-shadow:0 1px 3px rgba(15,23,42,.06),0 4px 16px rgba(15,23,42,.06);
  display:flex;flex-direction:column;min-height:200px;
  transition:transform .18s ease,box-shadow .18s ease;}}
.pc:hover{{transform:translateY(-3px);box-shadow:0 8px 28px rgba(29,78,216,.12);
  border-color:#BFDBFE;}}
.pc-top{{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;}}
.ic{{width:38px;height:38px;border-radius:9px;display:flex;align-items:center;justify-content:center;}}
.no{{font-family:'JetBrains Mono',monospace;font-size:11px;color:#94A3B8;}}
.pt{{font-family:'Plus Jakarta Sans';font-weight:700;font-size:15px;
  color:#0F172A;margin-bottom:6px;}}
.pd{{font-size:12.5px;line-height:1.55;color:#64748B;flex:1;}}
.tech{{font-family:'JetBrains Mono',monospace;font-size:10.5px;font-weight:500;
  padding:3px 9px;border-radius:5px;border:1px solid;display:inline-block;}}

/* animation */
[data-rev]{{opacity:0;transform:translateY(14px);
  transition:opacity .6s cubic-bezier(.16,.84,.44,1),transform .6s cubic-bezier(.16,.84,.44,1);}}

@media(max-width:900px){{
  .grid{{grid-template-columns:repeat(2,1fr);}}
  .steps{{grid-template-columns:1fr;}}
  .step+.step{{border-left:0;border-top:1px solid #E2E8F0;}}
}}
</style></head><body>
<div class='wrap'>
  <div class='steps' data-rev>
    <div class='step'>
      <div class='num'>1</div>
      <div><div class='st-t'>Load your data</div>
      <div class='st-d'>Drop in CSV, Excel or JSON — or click the Financial Risk demo to start immediately.</div></div>
    </div>
    <div class='step'>
      <div class='num'>2</div>
      <div><div class='st-t'>Agents analyse it</div>
      <div class='st-d'>Five specialised agents run the full pipeline: clean, explore, model, explain, report.</div></div>
    </div>
    <div class='step'>
      <div class='num'>3</div>
      <div><div class='st-t'>Read the findings</div>
      <div class='st-d'>Every metric, chart and insight is computed live — reproducible and fully auditable.</div></div>
    </div>
  </div>

  <div data-rev>
    <div class='kick'>The pipeline</div>
    <h2>Five agents. One continuous workflow.</h2>
    <p class='lead'>Each stage hands structured, validated output to the next — built on pandas, SciPy, scikit-learn and SHAP.</p>
    <div class='grid'>__CARDS__</div>
  </div>
</div>
<script>
var io=new IntersectionObserver(function(es){{
  es.forEach(function(e){{
    if(e.isIntersecting){{
      e.target.style.opacity='1';
      e.target.style.transform='translateY(0)';
      io.unobserve(e.target);
    }}
  }});
}},{{threshold:.1}});
document.querySelectorAll('[data-rev]').forEach(function(el){{io.observe(el);}});
</script>
</body></html>"""


def landing_sections(height: int = 520) -> None:
    components.html(_LANDING.replace("__CARDS__", _pipe_cards()), height=height, scrolling=False)
