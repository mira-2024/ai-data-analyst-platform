"""
DataFlow AI — Streamlit application entry point.

A multi-agent data-science assistant with a premium light design and a 3D hero.
The Data Preview, EDA and Modeling tabs run entirely on real computation
(pandas / SciPy / scikit-learn) and need no API key. The Chat tab uses an
optional Gemini LLM to route requests and narrate the computed results.
"""

import os

import pandas as pd
import streamlit as st

from utils.file_handler import load_file
from utils import llm
from orchestrator.orchestrator import Orchestrator
from agents.modeling_agent import ModelingAgent
from ml import modeling, eda
from ui import theme
from ui import advanced
from ui.components import (
    render_data_preview,
    render_eda,
    render_figures,
    render_chat_message,
    render_model_results,
)

st.set_page_config(page_title="DataFlow AI — Data Science Assistant",
                   page_icon="◆", layout="wide")
theme.inject_theme()

SAMPLE_PATH = os.path.join(os.path.dirname(__file__), "sample_data", "sample.csv")

# ── Session state ──────────────────────────────────────────────────────────────
for key, default in [("df", None), ("history", []), ("model_results", None)]:
    if key not in st.session_state:
        st.session_state[key] = default
if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = Orchestrator()


def _load_df(df: pd.DataFrame) -> None:
    st.session_state.df = df
    st.session_state.history = []
    st.session_state.model_results = None


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("<div class='kicker'>Data Science Studio</div>"
                "<h2 style='margin:.1rem 0 1rem;'>DataFlow&nbsp;AI</h2>", unsafe_allow_html=True)

    if not llm.available():
        st.info("Offline mode — EDA & Modeling work fully without an API key. "
                "Add `GEMINI_API_KEY` to `.env` to enable Chat.")

    if st.session_state.df is not None:
        df_ = st.session_state.df
        st.markdown(
            f"<div style='background:#fff;border:1px solid var(--line);border-radius:13px;padding:13px;margin-bottom:6px;'>"
            f"<div style='display:flex;gap:9px;align-items:center;'>"
            f"<div style='width:30px;height:30px;border-radius:8px;background:var(--soft);color:var(--accent);"
            f"display:flex;align-items:center;justify-content:center;font-family:Space Mono;font-size:10px;font-weight:700;'>CSV</div>"
            f"<div style='font-weight:600;font-size:13px;'>dataset loaded</div></div>"
            f"<div style='display:flex;gap:6px;margin-top:9px;'>"
            f"<div style='flex:1;text-align:center;background:#F7F7F4;border-radius:8px;padding:6px;'>"
            f"<div style='font-family:Space Grotesk;font-weight:700;'>{df_.shape[0]}</div><div style='font-size:10px;color:var(--muted2);'>rows</div></div>"
            f"<div style='flex:1;text-align:center;background:#F7F7F4;border-radius:8px;padding:6px;'>"
            f"<div style='font-family:Space Grotesk;font-weight:700;'>{df_.shape[1]}</div><div style='font-size:10px;color:var(--muted2);'>cols</div></div>"
            f"</div></div>", unsafe_allow_html=True)

        st.markdown("<hr class='rule'>", unsafe_allow_html=True)
        adv = st.toggle("Advanced mode", value=st.session_state.get("advanced", False),
                        help="Reveal clustering, model diagnostics, feature selection "
                             "and deeper statistics. Off by default for a simpler view.")
        st.session_state.advanced = adv

        if adv:
            st.markdown("<hr class='rule'>", unsafe_allow_html=True)
            st.markdown("<div class='kicker'>Quick actions</div>", unsafe_allow_html=True)
            st.caption("Runs an agent — the answer appears in the **Chat** tab.")
            for qp in ["Clean the data", "Analyse the dataset", "Build a predictive model",
                       "Visualize the data", "Generate a full report"]:
                if st.button(qp, width="stretch"):
                    st.session_state["quick_prompt"] = qp
                    st.toast(f"Running “{qp}” — see the Chat tab.", icon="💬")
        st.markdown("<hr class='rule'>", unsafe_allow_html=True)
        replace = st.file_uploader("Replace dataset", type=["csv", "xlsx", "xls", "json"])
        if replace is not None:
            try:
                _load_df(load_file(replace)); st.rerun()
            except Exception as e:
                st.error(f"Error loading file: {e}")
        if st.button("Clear chat", width="stretch"):
            st.session_state.history = []

# ── Landing ────────────────────────────────────────────────────────────────────
if st.session_state.df is None:
    theme.hero(height=560)

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    mid, _ = st.columns([1.25, 1.75])
    with mid:
        if st.button("🚀  Try with sample data", type="primary", width="stretch"):
            _load_df(pd.read_csv(SAMPLE_PATH)); st.rerun()
        up = st.file_uploader("…or upload your own (CSV / Excel / JSON)",
                              type=["csv", "xlsx", "xls", "json"])
        if up is not None:
            try:
                _load_df(load_file(up)); st.rerun()
            except Exception as e:
                st.error(f"Error loading file: {e}")

    st.markdown("<div style='height:26px'></div>", unsafe_allow_html=True)
    theme.landing_sections(height=560)
    st.stop()

df = st.session_state.df

# ── Workspace ────────────────────────────────────────────────────────────────
theme.section("Workspace", kicker="DataFlow AI",
              sub=f"{df.shape[0]:,} rows · {df.shape[1]} columns loaded.")

# Warn early if the uploaded file looks malformed (e.g. missing header row).
for _w in eda.data_health_warnings(df):
    st.warning(_w)

advanced_mode = st.session_state.get("advanced", False)

if advanced_mode:
    tab_over, tab_data, tab_eda, tab_cluster, tab_model, tab_chat = st.tabs(
        ["Overview", "Data", "Explore", "Clustering", "Predict", "Chat"])
else:
    tab_over, tab_data, tab_eda, tab_model, tab_chat = st.tabs(
        ["Overview", "Data", "Explore", "Predict", "Chat"])
    tab_cluster = None

with tab_over:
    theme.section("Overview", kicker="Start here",
                  sub="One click runs the whole analysis and explains it in plain language.")
    advanced.render_overview(df)

with tab_data:
    theme.section("Your data", kicker="Step 1",
                  sub="A preview of the dataset, its columns and data quality.")
    render_data_preview(df)

with tab_eda:
    theme.section("Explore", kicker="Step 2",
                  sub="Distributions, relationships and key statistics — computed live.")
    render_eda(df)
    if advanced_mode:
        with st.expander("Deeper inferential statistics — confidence intervals, "
                         "assumption checks & multiple-testing (FDR) correction"):
            advanced.render_deeper_statistics(df)

if advanced_mode and tab_cluster is not None:
    with tab_cluster:
        theme.section("Clustering", kicker="Advanced",
                      sub="Group similar rows automatically with PCA + KMeans — no labels needed.")
        advanced.render_clustering(df)

with tab_model:
    theme.section("Predict", kicker="Step 3",
                  sub="Train models to predict a column, and see how well they do.")
    suggested = modeling.suggest_target(df)
    cols = list(df.columns)
    default_idx = cols.index(suggested) if suggested in cols else 0
    target = st.selectbox("What do you want to predict?", cols, index=default_idx)
    if target:
        st.caption(f"This is a **{modeling.detect_task(df, target)}** problem.")
    if st.button("Train & evaluate models", type="primary", width="stretch"):
        with st.spinner("Training models with cross-validation…"):
            out = ModelingAgent().run(df, target=target)
        if out["error"]:
            st.error(out["text"])
        else:
            st.session_state.model_results = out["results"]

    res = st.session_state.model_results
    if res is not None:
        render_model_results(res)
        if advanced_mode:
            st.markdown("<hr class='rule'>", unsafe_allow_html=True)
            theme.section("Model diagnostics", kicker="Advanced",
                          sub="ROC / precision-recall curves, hyper-parameter tuning, learning curve.")
            