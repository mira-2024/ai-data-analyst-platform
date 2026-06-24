"""
ui/components.py — Streamlit render helpers, styled to match the approved
"DataFlow AI" design.

The showcase panels (correlation heatmap, distribution, model leaderboard,
feature importance, confusion matrix) are rendered as custom editorial HTML/CSS
so they look like the approved mockup — but every value is bound to the REAL
computed pandas / scikit-learn output passed in. Dense numeric tables
(descriptive stats, categorical summary, outliers, significance) stay as
interactive ``st.dataframe`` widgets inside the themed bordered cards.
"""

from __future__ import annotations

import html

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from ml import eda

# ── Brand tokens (kept in sync with ui/theme.py) ────────────────────────────────
INK = "#0F1222"
INK2 = "#33364d"
MUTED = "#6B7280"
MUTED2 = "#9CA0AE"
LINE = "#ECECE6"
INDIGO = "#5B5BF0"
INDIGO_LT = "#7C7CF6"
TEAL = "#15B8A6"
TEAL_DK = "#0F9C8C"
RED = "#D9534F"

GROTESK = "'Space Grotesk',sans-serif"
MONO = "'Space Mono',monospace"

INTENT_LABELS = {
    "clean": "🧹 Cleaning", "analyze": "📊 Analysis", "model": "🤖 Modeling",
    "visualize": "📈 Visualization", "report": "📄 Report", "chat": "💬 Chat",
}


# ──────────────────────────────────────────────────────────────────────────────
# Small formatting / escaping helpers
# ──────────────────────────────────────────────────────────────────────────────
def _esc(x) -> str:
    return html.escape("" if x is None else str(x))


def _fmt(x) -> str:
    """Human-friendly number formatting for editorial tables."""
    if x is None:
        return "—"
    if isinstance(x, (int, np.integer)):
        return f"{int(x):,}"
    if isinstance(x, (float, np.floating)):
        if np.isnan(x):
            return "—"
        ax = abs(x)
        if ax != 0 and (ax >= 100000 or ax < 0.001):
            return f"{x:,.0f}" if ax >= 100000 else f"{x:.2e}"
        if ax >= 1000:
            return f"{x:,.0f}"
        # trim trailing zeros on small decimals
        s = f"{x:,.3f}".rstrip("0").rstrip(".")
        return s
    return _esc(x)


def format_pvalues(frame: pd.DataFrame, cols) -> pd.DataFrame:
    """Display tiny p-values as scientific notation instead of long 0.000...0 strings."""
    def fp(p):
        if not isinstance(p, (int, float, np.integer, np.floating)) or pd.isna(p):
            return p
        p = float(p)
        return f"{p:.2e}" if 0 < p < 1e-3 else f"{p:.4f}"
    out = frame.copy()
    for c in cols:
        if c in out.columns:
            out[c] = out[c].map(fp)
    return out


def _card_open(title: str, meta: str = "") -> str:
    head = (
        f"<div style='display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;'>"
        f"<div style='font-family:{GROTESK};font-weight:600;font-size:15px;color:{INK};'>{_esc(title)}</div>"
    )
    if meta:
        head += f"<span style='font-family:{MONO};font-size:11px;color:{MUTED2};'>{_esc(meta)}</span>"
    head += "</div>"
    return (
        f"<div style='background:#fff;border:1px solid {LINE};border-radius:16px;padding:18px;"
        f"box-shadow:0 6px 18px rgba(15,18,34,.04);margin-bottom:16px;'>{head}"
    )


_CARD_CLOSE = "</div>"


# ──────────────────────────────────────────────────────────────────────────────
# KPI cards
# ──────────────────────────────────────────────────────────────────────────────
def _kpi_cards(items: list[tuple]) -> None:
    """items = [(label, value, color)]"""
    cells = ""
    for label, value, color in items:
        cells += (
            f"<div style='flex:1;min-width:120px;background:#fff;border:1px solid {LINE};"
            f"border-radius:14px;padding:15px 16px;box-shadow:0 6px 18px rgba(15,18,34,.04);'>"
            f"<div style='font-size:12px;color:{MUTED};margin-bottom:8px;'>{_esc(label)}</div>"
            f"<div style='font-family:{GROTESK};font-weight:700;font-size:28px;"
            f"letter-spacing:-.02em;color:{color};'>{_esc(value)}</div></div>"
        )
    st.markdown(
        f"<div style='display:flex;flex-wrap:wrap;gap:12px;margin-bottom:16px;'>{cells}</div>",
        unsafe_allow_html=True,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Editorial HTML table (mono headers, hairline rows, horizontal scroll)
# ──────────────────────────────────────────────────────────────────────────────
def _editorial_table(df: pd.DataFrame, index_label: str = "", max_rows: int = 60) -> str:
    if df is None or df.empty:
        return ""
    show = df.head(max_rows)
    cols = list(show.columns)

    def th(label, align="left", pad="11px 14px"):
        return (
            f"<th style='text-align:{align};font-family:{MONO};font-weight:700;font-size:11px;"
            f"letter-spacing:.04em;text-transform:uppercase;color:{MUTED2};padding:{pad};"
            f"border-bottom:1px solid {LINE};white-space:nowrap;'>{_esc(label)}</th>"
        )

    head = "<tr style='background:#FAFAF8;'>"
    if index_label or show.index.name:
        head += th(index_label or show.index.name)
    for c in cols:
        head += th(c, align="right")
    head += "</tr>"

    body = ""
    for idx, row in show.iterrows():
        body += f"<tr style='border-bottom:1px solid #F2F2EE;'>"
        if index_label or show.index.name:
            body += (
                f"<td style='padding:11px 14px;font-weight:600;color:{INK};white-space:nowrap;'>"
                f"{_esc(idx)}</td>"
            )
        for c in cols:
            body += (
                f"<td style='padding:11px 14px;text-align:right;font-family:{MONO};font-size:12.5px;"
                f"color:{INK2};white-space:nowrap;'>{_fmt(row[c])}</td>"
            )
        body += "</tr>"

    return (
        f"<div style='border:1px solid {LINE};border-radius:14px;overflow:hidden;margin-bottom:16px;'>"
        f"<div style='overflow-x:auto;'>"
        f"<table style='border-collapse:collapse;width:100%;font-size:13px;'>"
        f"<thead>{head}</thead><tbody>{body}</tbody></table></div></div>"
    )


# ──────────────────────────────────────────────────────────────────────────────
# Correlation heatmap (rounded cells, indigo=+ / teal=−, opacity=magnitude)
# ──────────────────────────────────────────────────────────────────────────────
def _corr_color(v: float):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "#FAFAF8", MUTED2
    a = 0.12 + 0.80 * min(abs(float(v)), 1.0)
    rgb = "91,91,240" if v >= 0 else "21,184,166"
    ink = "#fff" if a > 0.52 else INK2
    return f"rgba({rgb},{a:.2f})", ink


def _corr_heatmap(corr: pd.DataFrame, cap: int = 8) -> str:
    cols = list(corr.columns)[:cap]
    sub = corr.loc[cols, cols]
    n = len(cols)
    short = [c if len(str(c)) <= 7 else str(c)[:6] + "…" for c in cols]

    grid = f"display:grid;grid-template-columns:72px repeat({n},1fr);gap:5px;align-items:center;"
    out = f"<div style='{grid}'>"
    out += "<div></div>"
    for s in short:
        out += f"<div style='font-family:{MONO};font-size:10px;color:{MUTED2};text-align:center;'>{_esc(s)}</div>"
    for ri, c in enumerate(cols):
        out += (
            f"<div style='font-family:{MONO};font-size:10px;color:{MUTED2};text-align:right;"
            f"padding-right:4px;white-space:nowrap;'>{_esc(short[ri])}</div>"
        )
        for cj in cols:
            v = sub.loc[c, cj]
            bg, ink = _corr_color(v)
            txt = f"{v:.2f}" if not (isinstance(v, float) and np.isnan(v)) else "—"
            out += (
                f"<div style='aspect-ratio:1.7;border-radius:6px;background:{bg};display:flex;"
                f"align-items:center;justify-content:center;font-family:{MONO};font-size:12px;"
                f"font-weight:700;color:{ink};'>{txt}</div>"
            )
    out += "</div>"
    if len(corr.columns) > cap:
        out += (
            f"<div style='font-size:11.5px;color:{MUTED2};margin-top:12px;'>"
            f"Showing the first {cap} of {len(corr.columns)} numeric features.</div>"
        )
    return out


# ──────────────────────────────────────────────────────────────────────────────
# Distribution histogram (gradient teal bars)
# ──────────────────────────────────────────────────────────────────────────────
def _histogram(series: pd.Series, bins: int = 6) -> str:
    s = pd.to_numeric(series, errors="coerce").dropna()
    if s.empty:
        return f"<div style='color:{MUTED2};font-size:13px;'>No numeric data.</div>"
    counts, edges = np.histogram(s, bins=min(bins, max(3, s.nunique())))
    mx = counts.max() or 1

    def lbl(a, b):
        def f(v):
            av = abs(v)
            if av >= 1000:
                return f"{v/1000:.0f}k" if av >= 10000 else f"{v/1000:.1f}k"
            return f"{v:.0f}" if float(v).is_integer() else f"{v:.1f}"
        return f"{f(a)}–{f(b)}"

    bars = ""
    for i, c in enumerate(counts):
        h = max(4, round(100 * c / mx))
        bars += (
            f"<div style='flex:1;display:flex;flex-direction:column;align-items:center;gap:8px;"
            f"height:100%;justify-content:flex-end;'>"
            f"<div style='font-family:{MONO};font-size:11px;font-weight:700;color:{INK2};'>{int(c)}</div>"
            f"<div style='width:100%;height:{h}%;border-radius:7px 7px 3px 3px;"
            f"background:linear-gradient(180deg,{TEAL},{TEAL_DK});'></div>"
            f"<div style='font-family:{MONO};font-size:9.5px;color:{MUTED2};text-align:center;"
            f"line-height:1.2;'>{lbl(edges[i], edges[i+1])}</div></div>"
        )
    return (
        f"<div style='display:flex;align-items:flex-end;gap:10px;height:188px;padding-top:8px;'>"
        f"{bars}</div>"
    )


# ──────────────────────────────────────────────────────────────────────────────
# Public: Data preview
# ──────────────────────────────────────────────────────────────────────────────
def render_data_preview(df: pd.DataFrame):
    n_missing = int(df.isnull().sum().sum())
    n_dupes = int(df.duplicated().sum())
    _kpi_cards([
        ("Rows", f"{df.shape[0]:,}", INK),
        ("Columns", df.shape[1], INK),
        ("Missing values", n_missing, TEAL if n_missing == 0 else INK),
        ("Duplicate rows", n_dupes, TEAL if n_dupes == 0 else INK),
    ])

    st.markdown(
        f"<div style='font-family:{GROTESK};font-weight:600;font-size:16px;color:{INK};"
        f"margin:4px 0 2px;'>Data preview</div>"
        f"<div style='font-size:13px;color:{MUTED};margin-bottom:12px;'>"
        f"First {min(10, len(df))} of {len(df):,} rows · cleaned, typed and validated.</div>",
        unsafe_allow_html=True,
    )
    st.markdown(_editorial_table(df.head(10)), unsafe_allow_html=True)

    with st.expander("Column details & full table"):
        info = pd.DataFrame({
            "Type": df.dtypes.astype(str),
            "Non-Null": df.count(),
            "Null": df.isnull().sum(),
            "Unique": df.nunique(),
        })
        st.dataframe(info, width="stretch")
        st.dataframe(df, width="stretch")


# ──────────────────────────────────────────────────────────────────────────────
# Public: EDA
# ──────────────────────────────────────────────────────────────────────────────
def render_eda(df: pd.DataFrame):
    from ml import statistics

    p = eda.profile_dataset(df)
    _kpi_cards([
        ("Rows", f"{p['n_rows']:,}", INK),
        ("Columns", p["n_cols"], INK),
        ("Missing", f"{p['missing_pct']}%", TEAL if p["missing_pct"] == 0 else INK),
        ("Duplicates", p["duplicate_rows"], TEAL if p["duplicate_rows"] == 0 else INK),
    ])

    num_cols = eda.numeric_columns(df)
    corr = eda.correlation_matrix(df)

    # Two-up: correlation heatmap + distribution
    left, right = st.columns(2)
    with left:
        if not corr.empty:
            st.markdown(_card_open("Correlation matrix", "pearson") + _corr_heatmap(corr)
                        + _CARD_CLOSE, unsafe_allow_html=True)
        else:
            st.markdown(_card_open("Correlation matrix")
                        + f"<div style='color:{MUTED2};font-size:13px;'>Needs ≥ 2 numeric columns.</div>"
                        + _CARD_CLOSE, unsafe_allow_html=True)
    with right:
        if num_cols:
            sel = st.selectbox("Distribution of", num_cols, key="eda_hist_col",
                               label_visibility="collapsed")
            st.markdown(_card_open(f"Distribution · {sel}", f"n={int(df[sel].notna().sum())}")
                        + _histogram(df[sel]) + _CARD_CLOSE, unsafe_allow_html=True)
        else:
            st.markdown(_card_open("Distribution")
                        + f"<div style='color:{MUTED2};font-size:13px;'>No numeric columns.</div>"
                        + _CARD_CLOSE, unsafe_allow_html=True)

    # Descriptive statistics — editorial table
    desc = eda.descriptive_stats(df)
    if not desc.empty:
        st.markdown(
            f"<div style='font-family:{GROTESK};font-weight:600;font-size:16px;color:{INK};"
            f"margin:6px 0 2px;'>Descriptive statistics</div>"
            f"<div style='font-size:13px;color:{MUTED};margin-bottom:12px;'>"
            f"Includes skewness, excess kurtosis and coefficient of variation.</div>",
            unsafe_allow_html=True,
        )
        st.markdown(_editorial_table(desc, index_label="feature"), unsafe_allow_html=True)

    # Strongest correlations as significance chips
    sig = statistics.correlation_significance(df) if not corr.empty else pd.DataFrame()
    if isinstance(sig, pd.DataFrame) and not sig.empty:
        with st.expander("Correlation significance (Pearson, with p-values)"):
            st.dataframe(format_pvalues(sig.head(15), ["p_value"]), width="stretch")

    # Secondary dense tables stay as interactive dataframes inside styled cards
    cats = eda.categorical_summary(df)
    if not cats.empty:
        with st.expander("Categorical summary"):
            st.dataframe(cats, width="stretch")

    miss = eda.missing_analysis(df)
    if not miss.empty:
        with st.expander("Missing values"):
            st.dataframe(miss, width="stretch")

    out = eda.outlier_summary(df)
    if not out.empty:
        with st.expander("Outlier summary (IQR & z-score)"):
            st.dataframe(out, width="stretch")


# ──────────────────────────────────────────────────────────────────────────────
# Public: Chat helpers
# ──────────────────────────────────────────────────────────────────────────────
def render_figures(figures: list[dict]):
    if not figures:
        return
    cols = st.columns(2)
    for i, item in enumerate(figures):
        with cols[i % 2]:
            fig = item["figure"]
            try:
                fig.update_layout(font=dict(family="Inter, sans-serif", color=INK2),
                                  paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            except Exception:
                pass
            st.plotly_chart(fig, use_container_width=True)
            if item.get("description"):
                st.caption(item["description"])


def render_chat_message(role: str, content: str, intent: str = ""):
    with st.chat_message(role):
        if intent and role == "assistant":
            label = INTENT_LABELS.get(intent, "")
            if label:
                st.caption(label)
        st.markdown(content)


# ──────────────────────────────────────────────────────────────────────────────
# Public: Modeling
# ──────────────────────────────────────────────────────────────────────────────
def _leaderboard(res: dict) -> str:
    results = res["results"].copy()
    pm = res["primary_metric"]
    if pm not in results.columns:
        pm = results.columns[0]
    ranked = results.sort_values(pm, ascending=False)
    vals = ranked[pm].astype(float)
    vmax = max(vals.max(), 1e-9)

    rows = ""
    for i, (name, r) in enumerate(ranked.iterrows()):
        best = i == 0
        v = float(r[pm])
        bar_w = max(3, min(100, round(100 * (v if 0 <= v <= 1 else v / vmax))))
        cv = ""
        if "cv_mean" in r and not pd.isna(r["cv_mean"]):
            std = r.get("cv_std", np.nan)
            cv = f"CV {r['cv_mean']:.3f}" + (f" ± {std:.3f}" if not pd.isna(std) else "")
        border = "#D7D7FB" if best else LINE
        bg = "#F6F6FF" if best else "#fff"
        rank_bg = INDIGO if best else "#F2F2EE"
        rank_ink = "#fff" if best else MUTED
        bar_c = f"linear-gradient(90deg,{INDIGO},{INDIGO_LT})" if best else "#C7C9D9"
        tag = (f"<span style='font-size:10px;font-weight:700;color:{INDIGO};background:#EEF0FF;"
               f"padding:2px 7px;border-radius:999px;margin-left:8px;'>best</span>") if best else ""
        rows += (
            f"<div style='display:flex;align-items:center;gap:13px;padding:12px 14px;"
            f"border:1px solid {border};background:{bg};border-radius:12px;margin-bottom:8px;'>"
            f"<div style='flex:none;width:24px;height:24px;border-radius:7px;background:{rank_bg};"
            f"color:{rank_ink};display:flex;align-items:center;justify-content:center;"
            f"font-family:{MONO};font-size:12px;font-weight:700;'>{i+1}</div>"
            f"<div style='flex:1;min-width:0;'>"
            f"<div style='font-size:14px;font-weight:600;color:{INK};'>{_esc(name)}{tag}</div>"
            f"<div style='height:5px;border-radius:999px;background:#EFEFEA;margin-top:7px;overflow:hidden;'>"
            f"<div style='height:100%;width:{bar_w}%;border-radius:999px;background:{bar_c};'></div></div>"
            + (f"<div style='font-family:{MONO};font-size:10px;color:{MUTED2};margin-top:5px;'>{cv}</div>" if cv else "")
            + f"</div>"
            f"<div style='text-align:right;'>"
            f"<div style='font-family:{MONO};font-size:15px;font-weight:700;color:{INK};'>{v:.3f}</div>"
            f"<div style='font-family:{MONO};font-size:10px;color:{MUTED2};text-transform:uppercase;'>{_esc(pm)}</div>"
            f"</div></div>"
        )
    return rows


def _importance_bars(imp: pd.DataFrame, top_n: int = 8) -> str:
    sub = imp.head(top_n)
    vmax = max(float(sub["importance"].max()), 1e-9)
    rows = ""
    for _, r in sub.iterrows():
        w = max(3, round(100 * float(r["importance"]) / vmax))
        rows += (
            f"<div style='display:grid;grid-template-columns:130px 1fr 52px;align-items:center;"
            f"gap:11px;margin-bottom:13px;'>"
            f"<div style='font-size:13px;color:{INK2};white-space:nowrap;overflow:hidden;"
            f"text-overflow:ellipsis;'>{_esc(r['feature'])}</div>"
            f"<div style='height:9px;border-radius:999px;background:#F2F2EE;overflow:hidden;'>"
            f"<div style='height:100%;width:{w}%;border-radius:999px;"
            f"background:linear-gradient(90deg,{INDIGO},{INDIGO_LT});'></div></div>"
            f"<div style='font-family:{MONO};font-size:12px;font-weight:700;color:{INK2};"
            f"text-align:right;'>{float(r['importance']):.3f}</div></div>"
        )
    return rows


def _confusion(cm: pd.DataFrame) -> str:
    labels = [str(c).replace("pred ", "").replace("actual ", "") for c in cm.columns]
    n = len(labels)
    mx = max(int(cm.values.max()), 1)

    grid = f"display:grid;grid-template-columns:64px repeat({n},1fr);gap:6px;"
    out = f"<div style='{grid}'>"
    out += "<div></div>"
    for l in labels:
        out += (f"<div style='font-family:{MONO};font-size:10.5px;color:{MUTED2};text-align:center;"
                f"padding-bottom:2px;'>pred {_esc(l)}</div>")
    for ri in range(n):
        out += (f"<div style='font-family:{MONO};font-size:10.5px;color:{MUTED2};display:flex;"
                f"align-items:center;justify-content:flex-end;padding-right:6px;'>act {_esc(labels[ri])}</div>")
        for cj in range(n):
            v = int(cm.iloc[ri, cj])
            if ri == cj:
                a = 0.30 + 0.62 * (v / mx)
                bg, ink, sub = f"rgba(21,184,166,{a:.2f})", "#fff", "correct"
            elif v == 0:
                bg, ink, sub = "#FAFAF8", MUTED2, ""
            else:
                a = 0.18 + 0.55 * (v / mx)
                bg, ink, sub = f"rgba(217,83,79,{a:.2f})", "#7a2c2a", "error"
            out += (
                f"<div style='aspect-ratio:1.5;border-radius:10px;background:{bg};"
                f"border:1px solid {'transparent' if v else LINE};display:flex;flex-direction:column;"
                f"align-items:center;justify-content:center;color:{ink};'>"
                f"<span style='font-family:{GROTESK};font-weight:700;font-size:24px;'>{v}</span>"
                + (f"<span style='font-size:9px;opacity:.85;'>{sub}</span>" if sub else "")
                + "</div>"
            )
    out += "</div>"
    return out


def render_model_results(res: dict):
    metric = res["primary_metric"].upper()
    score = res["best_score"]

    # secondary metrics for the headline card
    best_row = res["results"].loc[res["best_model"]]
    chips = []
    for k in ("accuracy", "roc_auc", "r2", "rmse", "mae"):
        if k == res["primary_metric"]:
            continue
        if k in best_row and not pd.isna(best_row[k]):
            chips.append((k.replace("_", "-").upper(), f"{best_row[k]:.3f}"))
    chips.append(("TRAIN / TEST", f"{res['n_train']} / {res['n_test']}"))
    chips_html = ""
    for lbl, val in chips[:3]:
        chips_html += (
            f"<div><div style='font-family:{GROTESK};font-weight:700;font-size:18px;'>{_esc(val)}</div>"
            f"<div style='font-size:11px;color:rgba(255,255,255,.72);'>{_esc(lbl)}</div></div>"
        )

    headline = (
        f"<div style='background:linear-gradient(150deg,{INDIGO},#4646d6);border-radius:16px;"
        f"padding:22px 24px;color:#fff;box-shadow:0 14px 36px rgba(91,91,240,.28);"
        f"display:flex;flex-direction:column;gap:14px;height:100%;'>"
        f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
        f"<span style='font-family:{MONO};font-size:11px;letter-spacing:.08em;text-transform:uppercase;"
        f"color:rgba(255,255,255,.72);'>Best model · {_esc(metric)}</span>"
        f"<span style='font-size:11px;font-weight:600;background:rgba(255,255,255,.18);"
        f"padding:4px 10px;border-radius:999px;'>{_esc(res['task'])}</span></div>"
        f"<div><div style='font-family:{GROTESK};font-weight:700;font-size:54px;line-height:1;"
        f"letter-spacing:-.03em;'>{score:.3f}</div>"
        f"<div style='font-size:13.5px;color:rgba(255,255,255,.85);margin-top:8px;'>"
        f"{_esc(res['best_model'])} · target <b>{_esc(res['target'])}</b> · {res['cv_folds']}-fold CV</div></div>"
        f"<div style='display:flex;gap:18px;padding-top:14px;border-top:1px solid rgba(255,255,255,.18);'>"
        f"{chips_html}</div></div>"
    )

    leaderboard = (
        _card_open("Model leaderboard", f"ranked by {res['primary_metric']}")
        + _leaderboard(res) + _CARD_CLOSE
    )

    c1, c2 = st.columns([1, 1.25])
    with c1:
        st.markdown(headline, unsafe_allow_html=True)
    with c2:
        st.markdown(leaderboard, unsafe_allow_html=True)

    imp = res.get("feature_importance")
    cm = res.get("confusion_matrix")
    has_imp = isinstance(imp, pd.DataFrame) and not imp.empty
    has_cm = isinstance(cm, pd.DataFrame) and not cm.empty

    if has_imp and has_cm:
        d1, d2 = st.columns([1.25, 1])
        with d1:
            st.markdown(_card_open("Feature importance", "permutation") + _importance_bars(imp)
                        + _CARD_CLOSE, unsafe_allow_html=True)
        with d2:
            st.markdown(_card_open("Confusion matrix", f"test n={res['n_test']}") + _confusion(cm)
                        + _CARD_CLOSE, unsafe_allow_html=True)
    elif has_imp:
        st.markdown(_card_open("Feature importance", "permutation") + _importance_bars(imp)
                    + _CARD_CLOSE, unsafe_allow_html=True)
