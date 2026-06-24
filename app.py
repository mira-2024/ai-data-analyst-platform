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
from ml import modeling
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
        st.markdown("<div class='kicker'>Quick actions</div>", unsafe_allow_html=True)
        for qp in ["Clean the data", "Analyse the dataset", "Build a predictive model",
                   "Visualize the data", "Generate a full report"]:
            if st.button(qp, width="stretch"):
                st.session_state["quick_prompt"] = qp
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
    theme.hero(height=470)

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    _, mid, _ = st.columns([1.45, 1.1, 1.45])
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
              sub=f"Sample run · {df.shape[0]:,} rows · {df.shape[1]} columns loaded.")

tab_data, tab_eda, tab_cluster, tab_model, tab_chat = st.tabs(
    ["Data Preview", "EDA", "Clustering", "Modeling", "Chat"])

with tab_data:
    render_data_preview(df)

with tab_eda:
    theme.section("Exploratory Data Analysis", kicker="Stage 02 · 03",
                  sub="Descriptive + inferential statistics, computed live with pandas & SciPy.")
    render_eda(df)
    with st.expander("Deeper inferential statistics — confidence intervals, "
                     "assumption checks & multiple-testing (FDR) correction"):
        advanced.render_deeper_statistics(df)

with tab_cluster:
    theme.section("Unsupervised Learning", kicker="Stage 02b",
                  sub="PCA dimensionality reduction and KMeans clustering with automatic k "
                      "(silhouette + elbow) — finds structure with no labels.")
    advanced.render_clustering(df)

with tab_model:
    theme.section("Predictive Modeling", kicker="Stage 04",
                  sub="Cross-validated Logistic/Linear Regression, Random Forest and "
                      "Gradient Boosting, evaluated on a held-out test set. No API key required.")
    suggested = modeling.suggest_target(df)
    cols = list(df.columns)
    default_idx = cols.index(suggested) if suggested in cols else 0
    target = st.selectbox("Target column to predict", cols, index=default_idx)
    if target:
        st.caption(f"Detected task type: **{modeling.detect_task(df, target)}**")
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
        st.markdown("<hr class='rule'>", unsafe_allow_html=True)
        theme.section("Model diagnostics", kicker="Stage 04b",
                      sub="ROC / precision-recall curves, hyper-parameter tuning, learning curve.")
        advanced.render_model_diagnostics(df, res["target"], res["best_model"])
        st.markdown("<hr class='rule'>", unsafe_allow_html=True)
        theme.section("Feature engineering & selection", kicker="Stage 04c",
                      sub="Rank features (F-test + RFE) and measure the impact of selection.")
        advanced.render_feature_lab(df, res["target"])

with tab_chat:
    theme.section("Chat with your data", kicker="Stage 05",
                  sub="Ask questions in natural language — routed to the right agent.")
    if not llm.available():
        st.warning("Chat needs a Gemini API key. Use the **EDA** and **Modeling** tabs "
                   "for the full data-science workflow without one.")

    for msg in st.session_state.history:
        render_chat_message(msg["role"], msg["content"], intent=msg.get("intent", ""))
        if msg.get("figures"):
            render_figures(msg["figures"])

    quick = st.session_state.pop("quick_prompt", None)
    user_input = st.chat_input("Ask anything about your data…") or quick

    if user_input:
        render_chat_message("user", user_input)
        st.session_state.history.append({"role": "user", "content": user_input})
        with st.spinner("Working…"):
            try:
                result = st.session_state.orchestrator.process(
                    df=df, user_message=user_input, history=st.session_state.history)
            except Exception as e:
                err = str(e)
                if "429" in err or "RESOURCE_EXHAUSTED" in err:
                    st.error("Gemini API quota exceeded. EDA/Modeling work without the LLM.")
                else:
                    st.error(f"An error occurred: {err}")
                st.session_state.history.pop()
                st.stop()
        if result["cleaned_df"] is not None:
            st.session_state.df = result["cleaned_df"]
        render_chat_message("assistant", result["text"], intent=result["intent"])
        if result["figures"]:
            render_figures(result["figures"])
        st.session_state.history.append({
            "role": "assistant", "content": result["text"],
            "intent": result["intent"], "figures": result["figures"]})
        st.rerun()
