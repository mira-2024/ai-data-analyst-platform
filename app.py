"""
DataFlow AI -- Streamlit application entry point.

A multi-agent data-science assistant with a premium light design.
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
import research_config

st.set_page_config(page_title="DataFlow AI -- Data Science Assistant",
                   page_icon="diamond", layout="wide")
theme.inject_theme()

SAMPLE_PATH = os.path.join(os.path.dirname(__file__), "sample_data", "sample.csv")
GMSC_PATH   = os.path.join(os.path.dirname(__file__), "sample_data", "cs-training.csv")

# -- Session state -------------------------------------------------------------
for key, default in [
    ("df", None), ("history", []), ("model_results", None),
    ("dataset_name", "sample"), ("shap_result", None), ("fairness_result", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default

if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = Orchestrator()


def _load_df(df: pd.DataFrame, name: str = "sample") -> None:
    st.session_state.df = df
    st.session_state.history = []
    st.session_state.model_results = None
    st.session_state.shap_result = None
    st.session_state.fairness_result = None
    st.session_state.dataset_name = name


# -- Sidebar -------------------------------------------------------------------
with st.sidebar:
    st.markdown("<div class='kicker'>Data Science Studio</div>"
                "<h2 style='margin:.1rem 0 1rem;'>DataFlow&nbsp;AI</h2>",
                unsafe_allow_html=True)

    if not llm.available():
        st.info("Offline mode -- EDA & Modeling work fully without an API key. "
                "Add GEMINI_API_KEY to .env to enable Chat.")

    if st.session_state.df is not None:
        df_ = st.session_state.df
        st.markdown(
            f"<div style='background:#fff;border:1px solid var(--line);border-radius:13px;"
            f"padding:13px;margin-bottom:6px;'>"
            f"<div style='display:flex;gap:9px;align-items:center;'>"
            f"<div style='width:30px;height:30px;border-radius:8px;background:var(--soft);"
            f"color:var(--accent);display:flex;align-items:center;justify-content:center;"
            f"font-family:Space Mono;font-size:10px;font-weight:700;'>CSV</div>"
            f"<div style='font-weight:600;font-size:13px;'>dataset loaded</div></div>"
            f"<div style='display:flex;gap:6px;margin-top:9px;'>"
            f"<div style='flex:1;text-align:center;background:#F7F7F4;border-radius:8px;padding:6px;'>"
            f"<div style='font-family:Space Grotesk;font-weight:700;'>{df_.shape[0]}</div>"
            f"<div style='font-size:10px;color:var(--muted2);'>rows</div></div>"
            f"<div style='flex:1;text-align:center;background:#F7F7F4;border-radius:8px;padding:6px;'>"
            f"<div style='font-family:Space Grotesk;font-weight:700;'>{df_.shape[1]}</div>"
            f"<div style='font-size:10px;color:var(--muted2);'>cols</div></div>"
            f"</div></div>", unsafe_allow_html=True)

        st.markdown("<hr class='rule'>", unsafe_allow_html=True)
        adv = st.toggle("Advanced mode",
                        value=st.session_state.get("advanced", False),
                        help="Reveal clustering, model diagnostics, feature selection "
                             "and deeper statistics.")
        st.session_state.advanced = adv

        if adv:
            st.markdown("<hr class='rule'>", unsafe_allow_html=True)
            st.markdown("<div class='kicker'>Quick actions</div>", unsafe_allow_html=True)
            st.caption("Runs an agent -- the answer appears in the Chat tab.")
            for qp in ["Clean the data", "Analyse the dataset",
                       "Build a predictive model", "Visualize the data",
                       "Generate a full report"]:
                if st.button(qp, width="stretch"):
                    st.session_state["quick_prompt"] = qp
                    st.toast(f"Running '{qp}' -- see the Chat tab.", icon="💬")

        st.markdown("<hr class='rule'>", unsafe_allow_html=True)
        replace = st.file_uploader("Replace dataset", type=["csv", "xlsx", "xls", "json"])
        if replace is not None:
            try:
                stem = replace.name.rsplit(".", 1)[0]
                _load_df(load_file(replace), name=stem)
                st.rerun()
            except Exception as e:
                st.error(f"Error loading file: {e}")
        if st.button("Clear chat", width="stretch"):
            st.session_state.history = []

# -- Landing -------------------------------------------------------------------
if st.session_state.df is None:
    hL, hR = st.columns([1.05, 0.92], gap="large")
    with hL:
        st.markdown("""
<div style="display:inline-flex;align-items:center;gap:8px;padding:5px 12px;
  border-radius:6px;background:#EFF6FF;border:1px solid #BFDBFE;margin-bottom:20px;">
  <span style="width:6px;height:6px;border-radius:50%;background:#0EA5E9;display:inline-block;"></span>
  <span style="font-family:'JetBrains Mono',monospace;font-size:10.5px;font-weight:500;
    letter-spacing:.12em;text-transform:uppercase;color:#1D4ED8;">Automated Data Science</span>
</div>
<div style="font-family:'Plus Jakarta Sans',sans-serif;font-weight:800;
  font-size:clamp(32px,4vw,54px);line-height:1.05;letter-spacing:-.035em;
  color:#0F172A;margin:0 0 16px;">
  Turn raw data into<br>
  <span style="background:linear-gradient(120deg,#1D4ED8,#0EA5E9);
    -webkit-background-clip:text;background-clip:text;color:transparent;">
    clear findings.</span>
</div>
<div style="font-size:16px;line-height:1.6;color:#475569;max-width:460px;">
  Upload a dataset and five specialised agents handle the entire analysis pipeline —
  cleaning, exploration, modeling, explainability and reporting. Every number is
  computed live, reproducible and verifiable.
</div>
""", unsafe_allow_html=True)
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Financial Risk Demo", type="primary", use_container_width=True,
                         help="150,000 borrower records — Give Me Some Credit dataset"):
                with st.spinner("Loading 150,000 records..."):
                    _load_df(pd.read_csv(GMSC_PATH, index_col=0), name="cs-training")
                st.rerun()
        with col2:
            if st.button("Try sample data", use_container_width=True,
                         help="Small dataset to quickly explore the platform"):
                if os.path.exists(SAMPLE_PATH):
                    _load_df(pd.read_csv(SAMPLE_PATH), name="sample")
                else:
                    _load_df(pd.read_csv(GMSC_PATH, index_col=0).head(500), name="sample")
                st.rerun()

        up = st.file_uploader("Or upload your own (CSV / Excel / JSON)",
                              type=["csv", "xlsx", "xls", "json"])
        if up is not None:
            try:
                stem = up.name.rsplit(".", 1)[0]
                _load_df(load_file(up), name=stem)
                st.rerun()
            except Exception as e:
                st.error(f"Error loading file: {e}")
        st.markdown(theme.HERO_STATS, unsafe_allow_html=True)
    with hR:
        theme.hero_canvas(height=640)

    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
    theme.landing_sections(height=560)
    st.stop()

df = st.session_state.df
dataset_name = st.session_state.get("dataset_name", "sample")
ctx = research_config.get_context(dataset_name)

# -- Workspace -----------------------------------------------------------------
theme.section("Workspace", kicker="DataFlow AI",
              sub=f"{df.shape[0]:,} rows x {df.shape[1]} columns loaded.")

for _w in eda.data_health_warnings(df):
    st.warning(_w)

# -- Research context banner ---------------------------------------------------
if ctx and ctx.get("research_question"):
    expanded = (dataset_name in ("cs-training", "cs_training", "heart_disease"))
    with st.expander(f"Research Context -- {ctx.get('title', 'Study')}",
                     expanded=expanded):
        st.markdown(
            f"**Domain:** {ctx.get('domain', '--')}  "
            f"**Dataset:** {ctx.get('dataset', '--')}"
        )
        st.markdown(f"**Research Question:** _{ctx['research_question']}_")
        if ctx.get("hypotheses"):
            st.markdown("**Hypotheses:**")
            for h in ctx["hypotheses"]:
                st.markdown(f"- {h}")

advanced_mode = st.session_state.get("advanced", False)

# -- Tabs ----------------------------------------------------------------------
if advanced_mode:
    tab_over, tab_data, tab_eda, tab_cluster, tab_model, tab_explain, tab_fair, tab_chat = st.tabs(
        ["Overview", "Data", "Explore", "Clustering",
         "Predict", "Explain", "Fairness", "Chat"])
else:
    tab_over, tab_data, tab_eda, tab_model, tab_explain, tab_fair, tab_chat = st.tabs(
        ["Overview", "Data", "Explore", "Predict", "Explain", "Fairness", "Chat"])
    tab_cluster = None

# -- Overview ------------------------------------------------------------------
with tab_over:
    theme.section("Overview", kicker="Start here",
                  sub="One click runs the whole analysis and explains it in plain language.")
    advanced.render_overview(df)

# -- Data preview --------------------------------------------------------------
with tab_data:
    theme.section("Your data", kicker="Step 1",
                  sub="A preview of the dataset, its columns and data quality.")
    render_data_preview(df)

# -- EDA -----------------------------------------------------------------------
with tab_eda:
    theme.section("Explore", kicker="Step 2",
                  sub="Distributions, relationships and key statistics -- computed live.")
    render_eda(df)
    if advanced_mode:
        with st.expander("Deeper inferential statistics -- confidence intervals, "
                         "assumption checks & multiple-testing (FDR) correction"):
            advanced.render_deeper_statistics(df)

# -- Clustering (advanced only) ------------------------------------------------
if advanced_mode and tab_cluster is not None:
    with tab_cluster:
        theme.section("Clustering", kicker="Advanced",
                      sub="Group similar rows automatically with PCA + KMeans.")
        advanced.render_clustering(df)

# -- Predict -------------------------------------------------------------------
with tab_model:
    theme.section("Predict", kicker="Step 3",
                  sub="Train models to predict a column, and see how well they do.")

    ctx_target = ctx.get("target_column") if ctx else None
    suggested = ctx_target or modeling.suggest_target(df)
    cols = list(df.columns)
    default_idx = cols.index(suggested) if (suggested and suggested in cols) else 0
    target = st.selectbox("What do you want to predict?", cols, index=default_idx)
    if target:
        task_label = modeling.detect_task(df, target)
        st.caption(f"This is a **{task_label}** problem.")

    if st.button("Train & evaluate models", type="primary", use_container_width=True):
        with st.spinner("Training models with cross-validation..."):
            out = ModelingAgent().run(df, target=target)
        if out["error"]:
            st.error(out["text"])
        else:
            st.session_state.model_results = out["results"]
            st.session_state.shap_result = None
            st.session_state.fairness_result = None

    res = st.session_state.model_results
    if res is not None:
        render_model_results(res)
        if advanced_mode:
            st.markdown("<hr class='rule'>", unsafe_allow_html=True)
            theme.section("Model diagnostics", kicker="Advanced",
                          sub="ROC / precision-recall curves, hyper-parameter tuning, learning curve.")
            advanced.render_model_diagnostics(df, res["target"], res["best_model"])
            st.markdown("<hr class='rule'>", unsafe_allow_html=True)
            theme.section("Feature engineering & selection", kicker="Advanced",
                          sub="Rank features (F-test + RFE) and measure the impact of selection.")
            advanced.render_feature_lab(df, res["target"])

# -- Explain (SHAP) -----------------------------------------------------------
with tab_explain:
    theme.section("Explain", kicker="Step 4",
                  sub="SHAP values -- understand why the model makes each prediction.")

    res = st.session_state.model_results
    if res is None:
        st.info("Train a model in the **Predict** tab first, then come back here.")
    else:
        from ml import explainability
        import plotly.express as px
        import plotly.graph_objects as go

        st.markdown(
            f"Explaining **{res['best_model']}** trained to predict `{res['target']}`."
        )
        st.caption(
            "SHAP (SHapley Additive exPlanations) measures each feature's contribution "
            "to every individual prediction, providing a mathematically rigorous "
            "attribution grounded in game theory (Lundberg & Lee, 2017)."
        )

        if st.button("Compute SHAP values", type="primary",
                     use_container_width=True, key="btn_shap"):
            try:
                with st.spinner("Computing SHAP values..."):
                    shap_res = explainability.compute_shap(
                        pipeline=res["best_pipeline"],
                        X=res["X_test"],
                        task=res["task"],
                    )
                    st.session_state.shap_result = shap_res
                st.success(
                    f"SHAP values computed using **{shap_res['explainer_type']}** "
                    f"on {len(shap_res['shap_values'])} test samples."
                )
            except ImportError:
                st.error(
                    "SHAP library not installed. "
                    "Run: `pip install shap` in your project folder then restart."
                )
            except Exception as e:
                st.error(f"SHAP computation failed: {e}")

        shap_res = st.session_state.shap_result
        if shap_res is not None:
            st.markdown("#### Global Feature Importance (mean |SHAP|)")
            st.caption(
                "Each bar = average absolute SHAP value across all test samples. "
                "Larger bar = stronger influence on the model output."
            )
            imp_df = explainability.shap_feature_importance(shap_res).head(15)
            fig_imp = px.bar(
                imp_df.iloc[::-1],
                x="mean_abs_shap", y="feature", orientation="h",
                template="plotly_white",
                color="mean_abs_shap", color_continuous_scale="Blues",
                labels={"mean_abs_shap": "Mean |SHAP|", "feature": "Feature"},
                title=f"SHAP Global Feature Importance -- {res['best_model']}",
            )
            fig_imp.update_layout(showlegend=False, coloraxis_showscale=False)
            st.plotly_chart(fig_imp, use_container_width=True)

            st.markdown("#### SHAP Summary -- Feature Impact Direction")
            st.caption(
                "Each dot = one test sample. "
                "Colour = feature value (red=high, blue=low). "
                "X position = SHAP value (right pushes toward positive class)."
            )
            summary_df = explainability.shap_summary_data(shap_res, top_n=12)
            fig_bee = px.scatter(
                summary_df, x="shap_value", y="feature",
                color="feature_value_norm",
                color_continuous_scale="RdBu_r",
                template="plotly_white",
                labels={
                    "shap_value": "SHAP value",
                    "feature": "Feature",
                    "feature_value_norm": "Feature value (norm.)",
                },
                title="SHAP Summary Plot",
            )
            fig_bee.update_traces(marker=dict(size=4, opacity=0.6))
            fig_bee.update_layout(
                coloraxis_colorbar=dict(title="Feature value<br>(norm.)")
            )
            st.plotly_chart(fig_bee, use_container_width=True)

            st.markdown("#### Individual Prediction Breakdown")
            n_test = len(shap_res["shap_values"])
            sample_idx = st.slider(
                "Select a test sample to explain", 0, n_test - 1, 0
            )
            wf = explainability.shap_waterfall_data(shap_res, sample_idx).head(10)
            colors = ["#D9534F" if v > 0 else "#4E79A7" for v in wf["shap_value"]]
            fig_wf = go.Figure(go.Bar(
                x=wf["shap_value"],
                y=wf["feature"],
                orientation="h",
                marker_color=colors,
                text=wf["shap_value"].round(4).astype(str),
                textposition="outside",
            ))
            fig_wf.update_layout(
                title=(
                    f"Waterfall -- Sample #{sample_idx} "
                    f"(base value = {shap_res['expected_value']:.4f})"
                ),
                xaxis_title="SHAP value",
                yaxis_title="Feature",
                template="plotly_white",
            )
            st.plotly_chart(fig_wf, use_container_width=True)
            st.caption(
                "Red bars push the prediction toward the positive class. "
                "Blue bars push it toward the negative class."
            )

# -- Fairness ------------------------------------------------------------------
with tab_fair:
    theme.section("Fairness", kicker="Step 5",
                  sub="Bias analysis -- detect if the model treats demographic groups differently.")

    res = st.session_state.model_results
    if res is None:
        st.info("Train a model in the **Predict** tab first, then come back here.")
    elif res["task"] != "classification":
        st.info("Fairness analysis is available for classification tasks only.")
    else:
        from ml import fairness
        import plotly.express as px

        st.caption(
            "Evaluates demographic parity, equal opportunity, predictive parity, "
            "and disparate impact (Barocas et al., 2019). "
            "No external fairness library required."
        )

        st.markdown("#### Class Imbalance")
        imb = fairness.class_imbalance_report(res["y_test"])
        c1, c2 = st.columns(2)
        with c1:
            for cls, cnt in imb.get("class_counts", {}).items():
                st.metric(f"Class {cls}", int(cnt))
        with c2:
            ratio = imb.get("imbalance_ratio", 1.0)
            color = "normal" if ratio < 1.5 else ("off" if ratio < 3 else "inverse")
            st.metric("Imbalance ratio", f"{ratio:.1f}:1", delta=None)
            if ratio >= 1.5:
                st.caption(
                    f"Imbalance ratio {ratio:.1f}:1 -- class_weight='balanced' applied during training."
                )

        # Sensitive column selector
        ctx_sensitive = ctx.get("sensitive_column") if ctx else None
        candidate_cols = fairness.detect_sensitive_columns(df)
        all_cols = list(df.columns)
        if ctx_sensitive and ctx_sensitive in all_cols:
            default_sensitive = ctx_sensitive
        elif candidate_cols:
            default_sensitive = candidate_cols[0]
        else:
            default_sensitive = all_cols[0]
        sensitive_col = st.selectbox(
            "Sensitive attribute (column to audit for fairness)",
            all_cols,
            index=all_cols.index(default_sensitive),
        )

        positive_label = ctx.get("positive_label", 1) if ctx else 1

        if st.button("Run fairness analysis", type="primary",
                     use_container_width=True, key="btn_fair"):
            try:
                with st.spinner("Analysing fairness across groups..."):
                    fair_res = fairness.run_fairness_analysis(
                        df=df,
                        y_true=res["y_test"],
                        y_pred=res["y_pred"],
                        sensitive_col_name=sensitive_col,
                        positive_label=positive_label,
                    )
                    st.session_state.fairness_result = fair_res
            except Exception as e:
                st.error(f"Fairness analysis failed: {e}")

        fair_res = st.session_state.fairness_result
        if fair_res is not None:
            group_df = fair_res.get("group_metrics")
            if group_df is not None and not group_df.empty:
                st.markdown("#### Per-Group Metrics")
                st.dataframe(group_df.round(4), use_container_width=True)

                st.markdown("#### Selection Rate by Group")
                fig_sel = px.bar(
                    group_df,
                    x=group_df.index if group_df.index.name else group_df.columns[0],
                    y="selection_rate",
                    template="plotly_white",
                    color="selection_rate",
                    color_continuous_scale="Blues",
                    title=f"Selection Rate by {sensitive_col}",
                    labels={"selection_rate": "Selection Rate", "x": sensitive_col},
                )
                st.plotly_chart(fig_sel, use_container_width=True)

            verdicts = fair_res.get("verdicts", {})
            if verdicts:
                st.markdown("#### Fairness Verdicts")
                for criterion, result in verdicts.items():
                    passed = result.get("pass", False)
                    icon = "✓" if passed else "✗"
                    color = "green" if passed else "red"
                    st.markdown(
                        f"**{criterion}**: "
                        f"<span style='color:{color};font-weight:bold;'>{icon} {'PASS' if passed else 'FAIL'}</span> "
                        f"-- {result.get('detail', '')}",
                        unsafe_allow_html=True,
                    )

# -- Chat ----------------------------------------------------------------------
with tab_chat:
    theme.section("Chat", kicker="Step 6",
                  sub="Ask questions about your data -- the agents answer with real computation.")

    orchestrator = st.session_state.orchestrator
    history = st.session_state.history

    # Handle quick prompts from sidebar
    if "quick_prompt" in st.session_state and st.session_state.quick_prompt:
        qp = st.session_state.quick_prompt
        st.session_state.quick_prompt = None
        with st.spinner(f"Running: {qp}"):
            result = orchestrator.process(df, qp, history)
        history.append({"role": "user", "content": qp})
        history.append({"role": "assistant", "content": result["text"],
                        "figures": result.get("figures", [])})
        if result.get("cleaned_df") is not None:
            st.session_state.df = result["cleaned_df"]

    for msg in history:
        render_chat_message(msg)

    if prompt := st.chat_input("Ask about your data..."):
        history.append({"role": "user", "content": prompt})
        render_chat_message({"role": "user", "content": prompt})
        with st.spinner("Analysing..."):
            result = orchestrator.process(df, prompt, history)
        reply = {"role": "assistant", "content": result["text"],
                 "figures": result.get("figures", [])}
        history.append(reply)
        if result.get("cleaned_df") is not None:
            st.session_state.df = result["cleaned_df"]
        render_chat_message(reply)
        st.rerun()
