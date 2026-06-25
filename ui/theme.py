"""
ui/theme.py — Design system ported from the approved "DataFlow AI" design.

Light, premium, editorial. Indigo (#5B5BF0) + teal (#15B8A6) on warm paper,
Space Grotesk / Inter / Space Mono, ambient gradient blooms, a gradient
headline, and a 3D "data manifold" hero (twin wireframes + dual-colour additive
point clouds) with count-up stats and floating glass cards.

Public API
----------
inject_theme()        global CSS (call once at top of app.py)
hero()                full hero: copy + 3D manifold + stats + floating cards
landing_sections()    the 3-step "getting started" strip + 5-card pipeline
section(title, …)     editorial section header (kicker / title / subtitle)
"""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

PALETTE = {
    "paper": "#FBFBF9", "surface": "#FFFFFF", "ink": "#0F1222", "ink2": "#33364d",
    "muted": "#6B7280", "muted2": "#9CA0AE", "line": "#ECECE6",
    "accent": "#5B5BF0", "accent_lt": "#7C7CF6", "accent_soft": "#EEF0FF",
    "teal": "#15B8A6", "teal_soft": "#E7F7F4",
}

_FONTS = ("https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700"
          "&family=Space+Grotesk:wght@500;600;700&family=Space+Mono:wght@400;700&display=swap")

_CSS = f"""
<style>
@import url('{_FONTS}');
:root{{
  --paper:#FBFBF9; --surface:#FFFFFF; --ink:#0F1222; --ink2:#33364d;
  --muted:#6B7280; --muted2:#9CA0AE; --line:#ECECE6;
  --accent:#5B5BF0; --accent-lt:#7C7CF6; --soft:#EEF0FF;
  --teal:#15B8A6; --teal-soft:#E7F7F4;
  --radius:18px; --shadow:0 1px 2px rgba(15,18,34,.04), 0 10px 30px rgba(15,18,34,.05);
}}
@keyframes dfBloom{{0%,100%{{transform:translate(0,0) scale(1);opacity:.85;}}50%{{transform:translate(2%,3%) scale(1.06);opacity:1;}}}}

.stApp{{ background:
  radial-gradient(760px 760px at 92% -10%, rgba(91,91,240,.16) 0%, rgba(91,91,240,0) 60%),
  radial-gradient(680px 680px at -8% 12%, rgba(21,184,166,.13) 0%, rgba(21,184,166,0) 60%),
  var(--paper); }}
html, body, [class*="css"]{{ font-family:'Inter',system-ui,sans-serif; color:var(--ink); }}
.block-container{{ padding:1.3rem clamp(1.25rem,3vw,3.25rem) 3rem; max-width:100%; }}
[data-testid="stHeader"]{{ background:transparent; }}
#MainMenu, footer{{ visibility:hidden; }}

h1,h2,h3,h4{{ font-family:'Space Grotesk','Inter',sans-serif; letter-spacing:-.025em; color:var(--ink); }}
h2{{ font-weight:600; font-size:1.7rem; }} h3{{ font-weight:600; font-size:1.2rem; }}
p, li, .stMarkdown{{ color:var(--ink2); }}
a{{ color:var(--accent); text-decoration:none; }}

.kicker{{ font-family:'Space Grotesk'; text-transform:uppercase; letter-spacing:.18em;
  font-size:.72rem; font-weight:600; color:var(--accent); }}
.section-sub{{ color:var(--muted); font-size:1rem; margin-top:.2rem; }}
.rule{{ height:1px; background:var(--line); border:0; margin:1.1rem 0; }}

/* sidebar */
section[data-testid="stSidebar"]{{ background:linear-gradient(180deg,#FCFCFB,#FBFBF9); border-right:1px solid var(--line); }}

/* buttons — pill, default ghost, primary indigo */
.stButton>button{{
  width:100%; border-radius:999px; border:1px solid var(--line); background:var(--surface);
  color:var(--ink); font-weight:600; font-size:.92rem; padding:.6rem 1.1rem; transition:all .16s ease; }}
.stButton>button:hover{{ border-color:var(--accent); color:var(--accent); background:var(--soft); transform:translateY(-1px); }}
.stButton>button[kind="primary"]{{ background:var(--accent); color:#fff; border-color:var(--accent);
  box-shadow:0 10px 26px rgba(91,91,240,.32); }}
.stButton>button[kind="primary"]:hover{{ background:#4a4ae0; color:#fff; box-shadow:0 16px 34px rgba(91,91,240,.42); }}

/* metrics as cards */
[data-testid="stMetric"]{{ background:var(--surface); border:1px solid var(--line); border-radius:14px;
  padding:1rem 1.1rem; box-shadow:var(--shadow); }}
[data-testid="stMetricLabel"]{{ color:var(--muted); font-weight:500; }}
[data-testid="stMetricValue"]{{ font-family:'Space Grotesk'; font-weight:700; color:var(--ink); }}

/* tabs */
.stTabs [data-baseweb="tab-list"]{{ gap:4px; border-bottom:1px solid var(--line); }}
.stTabs [data-baseweb="tab"]{{ background:transparent; border:0; color:var(--muted2);
  font-weight:600; font-size:.95rem; padding:.6rem 1rem; }}
.stTabs [aria-selected="true"]{{ color:var(--ink) !important; border-bottom:2px solid var(--accent) !important; }}

/* dataframes & inputs */
[data-testid="stDataFrame"], [data-testid="stTable"]{{ border:1px solid var(--line); border-radius:14px; overflow:hidden; box-shadow:var(--shadow); }}
[data-baseweb="select"]>div, .stTextInput>div>div{{ border-radius:12px !important; }}
[data-testid="stFileUploader"]{{ background:var(--surface); border:1px dashed var(--line); border-radius:14px; padding:.4rem; }}
[data-testid="stChatMessage"]{{ background:var(--surface); border:1px solid var(--line); border-radius:16px; box-shadow:var(--shadow); }}
[data-testid="stAlert"]{{ border-radius:12px; border:1px solid var(--line); }}
.chip{{ font-family:'Space Mono',monospace; font-size:.72rem; font-weight:700; color:var(--accent);
  background:var(--soft); border:1px solid #E0E1FB; border-radius:7px; padding:4px 9px; }}

/* polish + responsiveness */
html{{ scroll-behavior:smooth; }}
.main .block-container{{ animation:dfRise .5s cubic-bezier(.16,.84,.44,1); }}
@keyframes dfRise{{ from{{ opacity:0; transform:translateY(8px); }} to{{ opacity:1; transform:translateY(0); }} }}
[data-testid="stCaptionContainer"], .stCaption{{ color:var(--muted) !important; }}
[data-testid="stWidgetLabel"] label, .stSelectbox label, .stFileUploader label{{ color:var(--ink2) !important; font-weight:500; }}
[data-baseweb="tab-highlight"]{{ background:var(--accent) !important; }}
iframe{{ border:0 !important; }}
hr{{ border-color:var(--line); }}
/* let Streamlit columns stack cleanly on narrow screens */
@media (max-width:680px){{
  .block-container{{ padding-left:1rem !important; padding-right:1rem !important; }}
  [data-testid="stMetricValue"]{{ font-size:1.4rem; }}
}}
</style>
"""


def inject_theme() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def section(title: str, kicker: str = "", sub: str = "") -> None:
    html = "<div style='margin:.2rem 0 .7rem;'>"
    if kicker:
        html += f"<div class='kicker'>{kicker}</div>"
    html += f"<h2 style='margin:.15rem 0 0;'>{title}</h2>"
    if sub:
        html += f"<div class='section-sub'>{sub}</div>"
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


# ── 3D hero (Three.js, isolated iframe) ──────────────────────────────────────
_HERO = """
<!doctype html><html><head><meta charset='utf-8'>
<link href='https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&family=Space+Mono:wght@400;700&display=swap' rel='stylesheet'>
<script src='https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js'></script>
<style>
 *{box-sizing:border-box;} html,body{margin:0;background:transparent;overflow:hidden;font-family:'Inter',sans-serif;color:#0F1222;}
 .wrap{display:grid;grid-template-columns:1.05fr .95fr;gap:32px;align-items:center;max-width:1500px;margin:0 auto;padding:6px 4px;}
 .badge{display:inline-flex;align-items:center;gap:9px;padding:6px 13px;border-radius:999px;background:#EEF0FF;border:1px solid #E0E1FB;margin-bottom:20px;}
 .badge span{font-family:'Space Grotesk';font-size:11.5px;font-weight:600;letter-spacing:.14em;text-transform:uppercase;color:#5B5BF0;}
 .dot{width:7px;height:7px;border-radius:50%;background:#15B8A6;}
 h1{font-family:'Space Grotesk';font-weight:700;font-size:clamp(36px,5vw,60px);line-height:1.03;letter-spacing:-.03em;margin:0 0 18px;}
 .grad{background:linear-gradient(120deg,#5B5BF0,#15B8A6);-webkit-background-clip:text;background-clip:text;color:transparent;}
 p.sub{font-size:17px;line-height:1.55;color:#4b4f63;margin:0 0 26px;max-width:480px;}
 .stats{display:flex;gap:30px;border-top:1px solid #ECECE6;padding-top:18px;}
 .stat .v{font-family:'Space Grotesk';font-weight:700;font-size:28px;letter-spacing:-.02em;}
 .stat .l{font-size:13px;color:#6B7280;margin-top:2px;}
 .r{position:relative;height:clamp(380px,50vw,580px);min-width:0;}
 canvas{position:absolute;inset:0;width:100%;height:100%;display:block;}
 .card{position:absolute;padding:10px 14px;background:rgba(255,255,255,.82);backdrop-filter:blur(8px);
   border:1px solid #ECECE6;border-radius:13px;box-shadow:0 10px 30px rgba(15,18,34,.08);}
 .card .k{font-family:'Space Mono',monospace;font-size:11px;color:#6B7280;}
 .card .b{font-family:'Space Grotesk';font-weight:700;font-size:16px;}
 @keyframes fl{0%,100%{transform:translateY(0);}50%{transform:translateY(-7px);}}
 @media(max-width:760px){.wrap{grid-template-columns:1fr;}.r{height:320px;}}
</style></head><body>
<div class='wrap'>
  <div>
    <div class='badge'><span class='dot'></span><span>Automated Data Science</span></div>
    <h1>Your data,<br>fully<span class='grad'> understood.</span></h1>
    <p class='sub'>Upload a spreadsheet and a team of specialised agents runs the whole workflow — cleaning, exploration, statistical testing, modeling and reporting. Every number computed and reproducible. Not a chatbot — a real pipeline.</p>
    <div class='stats'>
      <div class='stat'><div class='v' data-cu='5'>0</div><div class='l'>pipeline agents</div></div>
      <div class='stat'><div class='v' data-cu='100' data-suf='%'>0</div><div class='l'>reproducible</div></div>
      <div class='stat'><div class='v'>0</div><div class='l'>lines of code</div></div>
    </div>
  </div>
  <div class='r'>
    <canvas id='cv'></canvas>
  </div>
</div>
<script>
document.querySelectorAll('[data-cu]').forEach(function(el){
  var tgt=parseFloat(el.dataset.cu),suf=el.dataset.suf||'',s=performance.now(),d=1100,e=function(x){return 1-Math.pow(1-x,3);};
  (function tick(n){var k=Math.min(1,(n-s)/d);el.textContent=Math.round(tgt*e(k))+suf;if(k<1)requestAnimationFrame(tick);else el.textContent=Math.round(tgt)+suf;})(s);
});
var mx=0,my=0,hover=0,hoverT=0;
function init(t){t=t||0;var THREE=window.THREE,cv=document.getElementById('cv');
 if(!THREE||!cv){if(t<60)setTimeout(function(){init(t+1);},100);return;}
 var r=new THREE.WebGLRenderer({canvas:cv,antialias:true,alpha:true});r.setPixelRatio(Math.min(window.devicePixelRatio,2));
 var sc=new THREE.Scene();sc.fog=new THREE.FogExp2(0xFBFBF9,0.022);
 var cam=new THREE.PerspectiveCamera(45,1,0.1,100);cam.position.set(0,0,5.7);
 var g=new THREE.Group();sc.add(g);
 g.add(new THREE.Mesh(new THREE.IcosahedronGeometry(2.0,1),new THREE.MeshBasicMaterial({color:0x5B5BF0,wireframe:true,transparent:true,opacity:0.24})));
 var inner=new THREE.Mesh(new THREE.IcosahedronGeometry(1.2,0),new THREE.MeshBasicMaterial({color:0x15B8A6,wireframe:true,transparent:true,opacity:0.22}));g.add(inner);
 // interactive clouds: each point has a "home" on a sphere; the field slowly
 // spins, and points rush toward the cursor then spring back when it leaves.
 function cloud(n,c,sz,op,rmin,rsp){
   var home=new Float32Array(n*3),pos=new Float32Array(n*3);
   for(var i=0;i<n;i++){var rr=rmin+Math.random()*rsp,th=Math.random()*Math.PI*2,ph=Math.acos(2*Math.random()-1);
     home[i*3]=rr*Math.sin(ph)*Math.cos(th);home[i*3+1]=rr*Math.sin(ph)*Math.sin(th)*0.74;home[i*3+2]=rr*Math.cos(ph);
     pos[i*3]=home[i*3];pos[i*3+1]=home[i*3+1];pos[i*3+2]=home[i*3+2];}
   var gg=new THREE.BufferGeometry();gg.setAttribute('position',new THREE.BufferAttribute(pos,3));
   var pt=new THREE.Points(gg,new THREE.PointsMaterial({color:c,size:sz,transparent:true,opacity:op,sizeAttenuation:true,blending:THREE.AdditiveBlending,depthWrite:false}));
   sc.add(pt);return {pt:pt,home:home,pos:pos,n:n,geo:gg};}
 var clouds=[cloud(1300,0x5B5BF0,0.05,0.9,2.3,1.7),cloud(640,0x15B8A6,0.055,0.78,1.5,1.1)];
 var wrap=cv.parentElement;function size(){var w=wrap.clientWidth,h=wrap.clientHeight;if(!w||!h)return;r.setSize(w,h,false);cam.aspect=w/h;cam.updateProjectionMatrix();}
 size();window.addEventListener('resize',size);
 function setM(e){var b=cv.getBoundingClientRect();mx=((e.clientX-b.left)/b.width)*2-1;my=-(((e.clientY-b.top)/b.height)*2-1);}
 cv.addEventListener('pointermove',function(e){setM(e);hoverT=1;});
 cv.addEventListener('pointerenter',function(){hoverT=1;});
 cv.addEventListener('pointerleave',function(){hoverT=0;});
 var tmp=new THREE.Vector3();
 function mouseWorld(){tmp.set(mx,my,0.5).unproject(cam);tmp.sub(cam.position).normalize();var dz=(0-cam.position.z)/tmp.z;return cam.position.clone().add(tmp.multiplyScalar(dz));}
 (function loop(t){
   hover+=(hoverT-hover)*0.07;
   g.rotation.y+=0.0026;g.rotation.x=Math.sin(t*0.0002)*0.16;inner.rotation.y-=0.0045;
   g.position.x+=(mx*0.5-g.position.x)*0.05;g.position.y+=(my*0.4-g.position.y)*0.05;
   var yaw=t*0.00018,cy=Math.cos(yaw),sy=Math.sin(yaw),M=mouseWorld();
   for(var ci=0;ci<clouds.length;ci++){var c=clouds[ci],home=c.home,pos=c.pos,n=c.n;
     for(var i=0;i<n;i++){var hx=home[i*3],hy=home[i*3+1],hz=home[i*3+2];
       var rx=hx*cy-hz*sy, rz=hx*sy+hz*cy;
       var dx=M.x-rx, dy=M.y-hy, d2=dx*dx+dy*dy;
       var pull=hover*Math.min(0.92,1.5/(1+d2*1.1));
       var tx=rx+dx*pull, ty=hy+dy*pull;
       pos[i*3]+=(tx-pos[i*3])*0.12;pos[i*3+1]+=(ty-pos[i*3+1])*0.12;pos[i*3+2]+=(rz-pos[i*3+2])*0.12;}
     c.geo.attributes.position.needsUpdate=true;}
   r.render(sc,cam);requestAnimationFrame(loop);})(0);
}
init();
</script></body></html>
"""


def hero(height: int = 460) -> None:
    components.html(_HERO, height=height, scrolling=False)


# ── landing sections: 3-step strip + pipeline (isolated iframe) ──────────────
_PIPE = [
    ("01", "Cleaning", "Types, missing values, duplicates and outliers resolved with auditable rules.", "pandas", "#EEF0FF", "#5B5BF0", "4px"),
    ("02", "EDA", "Profiles every column — distributions, correlations and structure.", "pandas", "#E7F7F4", "#15B8A6", "50%"),
    ("03", "Testing", "Hypothesis tests pick the right method and report effect sizes.", "SciPy", "#EEF0FF", "#5B5BF0", "2px"),
    ("04", "Modeling", "Trains and cross-validates candidates, then ranks by held-out score.", "scikit-learn", "#E7F7F4", "#15B8A6", "4px"),
    ("05", "Reporting", "Assembles a clear, reproducible narrative of every finding.", "report", "#EEF0FF", "#5B5BF0", "50%"),
]


def _pipe_cards() -> str:
    out = ""
    for no, title, desc, tech, tint, ink, shape in _PIPE:
        out += (
            f"<div class='pc'>"
            f"<div class='pc-top'><div class='ic' style='background:{tint};'>"
            f"<div style='width:14px;height:14px;border:2.5px solid {ink};border-radius:{shape};'></div></div>"
            f"<span class='no'>{no}</span></div>"
            f"<div class='pt'>{title}</div><div class='pd'>{desc}</div>"
            f"<div style='margin-top:14px;'><span class='tech'>{tech}</span></div></div>"
        )
    return out


_LANDING = """
<!doctype html><html><head><meta charset='utf-8'>
<link href='https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&family=Space+Mono:wght@400;700&display=swap' rel='stylesheet'>
<style>
 *{box-sizing:border-box;} html,body{margin:0;background:transparent;font-family:'Inter',sans-serif;color:#0F1222;}
 .wrap{max-width:1500px;margin:0 auto;padding:4px 4px;}
 .steps{display:grid;grid-template-columns:repeat(3,1fr);gap:0;background:#fff;border:1px solid #ECECE6;border-radius:20px;padding:10px;box-shadow:0 1px 2px rgba(15,18,34,.04),0 14px 40px rgba(15,18,34,.05);margin-bottom:46px;}
 .step{display:flex;gap:14px;align-items:flex-start;padding:18px 20px;}
 .step+.step{border-left:1px solid #ECECE6;}
 .num{flex:none;width:36px;height:36px;border-radius:10px;background:#EEF0FF;color:#5B5BF0;display:flex;align-items:center;justify-content:center;font-family:'Space Grotesk';font-weight:700;font-size:15px;}
 .st-t{font-family:'Space Grotesk';font-weight:600;font-size:16px;margin-bottom:3px;}
 .st-d{font-size:13.5px;color:#6B7280;line-height:1.5;}
 .kick{font-family:'Space Grotesk';font-size:12px;font-weight:600;letter-spacing:.18em;text-transform:uppercase;color:#5B5BF0;margin-bottom:12px;}
 h2{font-family:'Space Grotesk';font-weight:600;font-size:clamp(26px,3.2vw,38px);line-height:1.08;letter-spacing:-.025em;margin:0 0 12px;}
 .lead{font-size:16px;line-height:1.55;color:#6B7280;margin:0 0 34px;max-width:620px;}
 .grid{display:grid;grid-template-columns:repeat(5,1fr);gap:14px;}
 .pc{background:#fff;border:1px solid #ECECE6;border-radius:18px;padding:22px 20px;box-shadow:0 1px 2px rgba(15,18,34,.04),0 10px 30px rgba(15,18,34,.05);display:flex;flex-direction:column;min-height:214px;transition:transform .18s ease,box-shadow .18s ease;}
 .pc:hover{transform:translateY(-4px);box-shadow:0 18px 44px rgba(15,18,34,.10);}
 .pc-top{display:flex;align-items:center;justify-content:space-between;margin-bottom:18px;}
 .ic{width:40px;height:40px;border-radius:12px;display:flex;align-items:center;justify-content:center;}
 .no{font-family:'Space Mono',monospace;font-size:12px;color:#9CA0AE;}
 .pt{font-family:'Space Grotesk';font-weight:600;font-size:17px;margin-bottom:7px;}
 .pd{font-size:13px;line-height:1.5;color:#6B7280;flex:1;}
 .tech{font-family:'Space Mono',monospace;font-size:11px;font-weight:700;color:#5B5BF0;background:#EEF0FF;border:1px solid #E0E1FB;padding:4px 9px;border-radius:7px;}
 [data-rev]{opacity:0;transform:translateY(18px);transition:opacity .7s cubic-bezier(.16,.84,.44,1),transform .7s cubic-bezier(.16,.84,.44,1);}
 @media(max-width:900px){.grid{grid-template-columns:repeat(2,1fr);}.steps{grid-template-columns:1fr;}.step+.step{border-left:0;border-top:1px solid #ECECE6;}}
</style></head><body>
<div class='wrap'>
  <div class='steps' data-rev>
    <div class='step'><div class='num'>1</div><div><div class='st-t'>Load data</div><div class='st-d'>Drop in a CSV or Excel file, or start instantly with the sample dataset.</div></div></div>
    <div class='step'><div class='num'>2</div><div><div class='st-t'>Explore</div><div class='st-d'>Agents profile, clean and test your data — stats, correlations, distributions.</div></div></div>
    <div class='step'><div class='num'>3</div><div><div class='st-t'>Model</div><div class='st-d'>Train and compare models, then read a clear, reproducible report.</div></div></div>
  </div>
  <div data-rev>
    <div class='kick'>The pipeline</div>
    <h2>Five specialised agents, one continuous flow.</h2>
    <p class='lead'>Each stage hands clean, structured output to the next — built on pandas, SciPy and scikit-learn.</p>
    <div class='grid'>__CARDS__</div>
  </div>
</div>
<script>
var io=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting){e.target.style.opacity='1';e.target.style.transform='translateY(0)';io.unobserve(e.target);}});},{threshold:.15});
document.querySelectorAll('[data-rev]').forEach(function(el){io.observe(el);});
</script></body></html>
"""


def landing_sections(height: int = 560) -> None:
    components.html(_LANDING.replace("__CARDS__", _pipe_cards()), height=height, scrolling=False)
