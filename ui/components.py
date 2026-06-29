"""
ui/components.py -- Streamlit render helpers for DataFlow AI.

Exports:
    render_data_preview   -- Dataset overview + quality table
    render_eda            -- Distributions, correlations, outliers
    render_figures        -- Plotly figure list from agent output
    render_chat_message   -- Styled chat bubble with optional charts
    render_model_results  -- Leaderboard, confusion matrix, feature importance
"""

from __future__ import annotations

import html
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ml import eda

# -- Brand tokens ---------------------------------------------------------------
INK      = "#0F1222"
MUTED    = "#6B7280"
LINE     = "#ECEDE6"
INDIGO   = "#5B5BF0"
TEAL     = "#15B8A6"
RED      = "#D9534F"
AMBER    = "#F59E0B"

INTENT_LABELS = {
    "clean":     "Cleaning",
    "analyze":   "Analysis",
    "model":     "Modeling",
    "visualize": "Visualization",
    "report":    "Report",
    "chat":      "Chat",
}


# -- helpers -------------------------------------------------------------------

def _metric_row(metrics: dict):
    cols = st.columns(len(metrics))
    for col, (label, value) in zip(cols, metrics.items()):
        col.metric(label, value)


# -- render_data_preview -------------------------------------------------------

def render_data_preview(df: pd.DataFrame):
    """Show shape, dtypes, missing values, and a scrollable preview."""
    n_rows, n_cols = df.shape
    n_missing = int(df.isna().sum().sum())
    n_dupes = int(df.duplicated().sum())
    pct_missing = f"{n_missing / max(df.size, 1) * 100:.1f}%"

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rows", f"{n_rows:,}")
    c2.metric("Columns", f"{n_cols:,}")
    c3.metric("Missing cells", f"{n_missing:,} ({pct_missing})")
    c4.metric("Duplicate rows", f"{n_dupes:,}")

    st.markdown("#### Column overview")
    info_rows = []
    for col in df.columns:
        n_null = int(df[col].isna().sum())
        n_unique = int(df[col].nunique(dropna=True))
        sample = str(df[col].dropna().iloc[0]) if n_null < n_rows else "N/A"
        info_rows.append({
            "Column": col,
            "Type": str(df[col].dtype),
            "Missing": n_null,
            "Missing %": f"{n_null / n_rows * 100:.1f}%",
            "Unique": n_unique,
            "Sample": sample,
        })
    st.dataframe(pd.DataFrame(info_rows), use_container_width=True, hide_index=True)

    st.markdown("#### Data preview")
    st.dataframe(df.head(100), use_container_width=True)


# -- render_eda ----------------------------------------------------------------

def render_eda(df: pd.DataFrame):
    """Distributions, correlation heatmap, outlier summary."""
    num_cols = df.select_dtypes(include="number").columns.tolist()
    cat_cols = df.select_dtypes(exclude="number").columns.tolist()

    tab_dist, tab_corr, tab_outlier = st.tabs(["Distributions", "Correlations", "Outliers"])

    with tab_dist:
        if num_cols:
            sel = st.selectbox("Select numeric column", num_cols, key="eda_dist_sel")
            col_data = df[sel].dropna()
            fig = px.histogram(
                col_data, x=sel, nbins=50,
                template="plotly_white",
                color_discrete_sequence=[INDIGO],
                title=f"Distribution of {sel}",
            )
            fig.update_layout(bargap=0.05)
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df[sel].describe().round(4).to_frame().T,
                         use_container_width=True, hide_index=True)
        else:
            st.info("No numeric columns found.")

        if cat_cols:
            st.markdown("#### Categorical columns")
            sel_cat = st.selectbox("Select categorical column", cat_cols, key="eda_cat_sel")
            vc = df[sel_cat].value_counts().head(20).reset_index()
            vc.columns = [sel_cat, "count"]
            fig_bar = px.bar(
                vc, x=sel_cat, y="count",
                template="plotly_white",
                color_discrete_sequence=[TEAL],
                title=f"Value counts -- {sel_cat}",
            )
            st.plotly_chart(fig_bar, use_container_width=True)

    with tab_corr:
        if len(num_cols) >= 2:
            top_n = min(len(num_cols), 15)
            corr = df[num_cols[:top_n]].corr(numeric_only=True).round(3)
            fig_heat = px.imshow(
                corr,
                text_auto=True,
                color_continuous_scale="RdBu_r",
                zmin=-1, zmax=1,
                template="plotly_white",
                title="Pearson Correlation Heatmap",
                aspect="auto",
            )
            fig_heat.update_layout(height=max(400, top_n * 35))
            st.plotly_chart(fig_heat, use_container_width=True)
        else:
            st.info("Need at least 2 numeric columns for a correlation heatmap.")

    with tab_outlier:
        if num_cols:
            try:
                outlier_df = eda.outlier_summary(df)
                if not outlier_df.empty:
                    st.dataframe(outlier_df, use_container_width=True, hide_index=True)
                    sel_box = st.selectbox("Box plot", num_cols, key="eda_box_sel")
                    fig_box = px.box(
                        df, y=sel_box,
                        template="plotly_white",
                        color_discrete_sequence=[INDIGO],
                        title=f"Box plot -- {sel_box}",
                    )
                    st.plotly_chart(fig_box, use_container_width=True)
                else:
                    st.success("No significant outliers detected (IQR method).")
            except Exception as e:
                st.warning(f"Could not compute outlier summary: {e}")
        else:
            st.info("No numeric columns to check for outliers.")


# -- render_figures ------------------------------------------------------------

def render_figures(figures: list):
    """Render a list of Plotly figures returned by agents."""
    if not figures:
        return
    for fig in figures:
        try:
            st.plotly_chart(fig, use_container_width=True)
        except Exception:
            st.json(fig)


# -- render_chat_message -------------------------------------------------------

def render_chat_message(msg: dict):
    """Render a single chat message with role styling."""
    role = msg.get("role", "assistant")
    content = msg.get("content", "")
    figures = msg.get("figures", [])

    with st.chat_message(role):
        st.markdown(content)
        if figures:
            render_figures(figures)


# -- render_model_results ------------------------------------------------------

def render_model_results(res: dict):
    """Render leaderboard, best-model metrics, confusion matrix, feature importance."""
    if not res:
        return

    task = res.get("task", "classification")
    target = res.get("target", "target")
    best_model = res.get("best_model", "")
    leaderboard = res.get("leaderboard")
    metrics = res.get("metrics", {})
    conf_matrix = res.get("confusion_matrix")
    feature_importance = res.get("feature_importance")
    cv_results = res.get("cv_results")

    st.success(f"Best model: **{best_model}** predicting `{target}`")

    if leaderboard is not None and not leaderboard.empty:
        st.markdown("#### Model leaderboard")
        st.dataframe(leaderboard.round(4), use_container_width=True, hide_index=True)

    if metrics:
        st.markdown("#### Best model metrics")
        primary_metrics = {}
        for k in ["f1_weighted", "mcc", "roc_auc", "pr_auc", "r2", "rmse", "mae"]:
            if k in metrics:
                v = metrics[k]
                label = k.upper().replace("_", " ")
                primary_metrics[label] = f"{v:.4f}" if isinstance(v, float) else str(v)
        if primary_metrics:
            _metric_row(primary_metrics)

    if cv_results:
        mean = cv_results.get("mean", 0)
        std = cv_results.get("std", 0)
        metric_name = cv_results.get("metric", "F1")
        st.caption(f"5-fold CV {metric_name}: **{mean:.4f}** +/- {std:.4f}")

    if conf_matrix is not None and task == "classification":
        st.markdown("#### Confusion matrix")
        try:
            cm = np.array(conf_matrix)
            labels = res.get("class_labels", [str(i) for i in range(cm.shape[0])])
            fig_cm = px.imshow(
                cm,
                text_auto=True,
                x=[f"Pred {l}" for l in labels],
                y=[f"True {l}" for l in labels],
                color_continuous_scale="Blues",
                template="plotly_white",
                title="Confusion Matrix",
                aspect="equal",
            )
            fig_cm.update_layout(height=350)
            st.plotly_chart(fig_cm, use_container_width=True)
        except Exception as e:
            st.caption(f"Could not render confusion matrix: {e}")

    if feature_importance is not None:
        st.markdown("#### Feature importance")
        try:
            if isinstance(feature_importance, pd.DataFrame):
                fi_df = feature_importance.copy()
            else:
                fi_df = pd.DataFrame(feature_importance)

            fi_df.columns = [c.lower() for c in fi_df.columns]
            feat_col = next((c for c in fi_df.columns if "feat" in c), fi_df.columns[0])
            imp_col = next((c for c in fi_df.columns if c != feat_col), fi_df.columns[1])
            fi_df = (
                fi_df[[feat_col, imp_col]]
                .head(15)
                .rename(columns={feat_col: "Feature", imp_col: "Importance"})
                .sort_values("Importance")
            )
            fig_fi = px.bar(
                fi_df, x="Importance", y="Feature", orientation="h",
                template="plotly_white",
                color="Importance",
                color_continuous_scale="Blues",
                title="Feature Importance",
            )
            fig_fi.update_layout(
                showlegend=False,
                coloraxis_showscale=False,
                height=max(300, len(fi_df) * 28),
            )
            st.plotly_chart(fig_fi, use_container_width=True)
        except Exception as e:
            st.caption(f"Could not render feature importance: {e}")


# -- format_pvalues ------------------------------------------------------------

def format_pvalues(df: pd.DataFrame, p_cols: list[str]) -> pd.DataFrame:
    """Return a copy of df with p-value columns formatted as strings (e.g. '<0.001')."""
    out = df.copy()
    for col in p_cols:
        if col in out.columns:
            def _fmt(v):
                try:
                    v = float(v)
                    if v < 0.001:
                        return "<0.001"
                    return f"{v:.3f}"
                except Exception:
                    return str(v)
            out[col] = out[col].apply(_fmt)
    return out
