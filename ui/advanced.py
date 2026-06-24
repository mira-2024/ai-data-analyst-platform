"""
ui/advanced.py — Streamlit render panels for the advanced data-science modules:
unsupervised learning (PCA + clustering), model diagnostics (ROC/PR, tuning,
learning curves), feature engineering/selection, and deeper inferential stats.

Every panel binds to the REAL computed output of the ``ml`` package.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ml import eda, unsupervised, diagnostics, feature_engineering, statistics
from ui import components as C

INDIGO, TEAL, MUTED = C.INDIGO, C.TEAL, C.MUTED


# ──────────────────────────────────────────────────────────────────────────────
# Unsupervised: PCA + clustering
# ──────────────────────────────────────────────────────────────────────────────
def render_clustering(df: pd.DataFrame) -> None:
    usable = [c for c in eda.numeric_columns(df) if df[c].nunique(dropna=True) > 1]
    if len(usable) < 2:
        st.info("Clustering and PCA need at least 2 numeric columns with variance.")
        return
    try:
        cl = unsupervised.run_clustering(df)
        pca = unsupervised.run_pca(df)
    except ValueError as e:
        st.info(str(e))
        return

    C._kpi_cards([
        ("Clusters (auto-k)", cl["k"], INDIGO),
        ("Silhouette score", f"{cl['silhouette']:.3f}", TEAL),
        ("PC1 + PC2 variance", f"{round(pca['pc1_pct'] + pca['pc2_pct'], 1)}%", INDIGO),
        ("Comp. for 90% var", pca["n_components_for_90pct"], INDIGO),
    ])

    left, right = st.columns(2)
    with left:
        st.markdown("##### Cluster map (PCA projection)")
        st.caption("Each point is a row, positioned by its first two principal components.")
        fig = px.scatter(cl["projection"], x="PC1", y="PC2", color="cluster",
                         template="plotly_white",
                         color_discrete_sequence=px.colors.qualitative.Bold)
        fig.update_layout(margin=dict(l=0, r=0, t=6, b=0), height=360, legend_title_text="cluster")
        st.plotly_chart(fig, use_container_width=True)
    with right:
        st.markdown("##### Choosing k — elbow & silhouette")
        st.caption("Elbow (inertia) drop vs silhouette quality; k is chosen at peak silhouette.")
        sel = cl["selection"]
        if not sel.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=sel["k"], y=sel["inertia"], name="inertia (elbow)",
                                     mode="lines+markers", line=dict(color=INDIGO), yaxis="y1"))
            fig.add_trace(go.Scatter(x=sel["k"], y=sel["silhouette"], name="silhouette",
                                     mode="lines+markers", line=dict(color=TEAL), yaxis="y2"))
            fig.update_layout(
                template="plotly_white", height=360, margin=dict(l=0, r=0, t=6, b=0),
                xaxis_title="k",
                yaxis=dict(title="inertia", showgrid=False),
                yaxis2=dict(title="silhouette", overlaying="y", side="right", showgrid=False),
                legend=dict(orientation="h", y=1.12))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption(f"k was set manually to {cl['k']}.")

    st.markdown("##### Cluster profiles")
    st.caption("Mean of each feature per cluster (original units) — how the segments differ.")
    st.dataframe(cl["profiles"], width="stretch")

    with st.expander("PCA detail — explained variance & loadings"):
        var = pca["variance"]
        fig = px.bar(var, x="component", y="explained_variance", template="plotly_white",
                     color_discrete_sequence=[INDIGO], text="explained_variance")
        fig.update_traces(textposition="outside")
        fig.update_layout(margin=dict(l=0, r=0, t=6, b=0), height=300)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Feature loadings on the first two components (direction & weight).")
        st.dataframe(pca["loadings"], width="stretch")


# ──────────────────────────────────────────────────────────────────────────────
# Model diagnostics: ROC / PR, tuning, learning curve
# ──────────────────────────────────────────────────────────────────────────────
def _curve_fig(series_list, x, y, title, diagonal=False):
    fig = go.Figure()
    palette = [INDIGO, TEAL, "#E2683C", "#9A7B12", "#7C7CF6", "#0F9C8C"]
    for i, s in enumerate(series_list):
        label = s["label"]
        metric = s.get("auc", s.get("ap"))
        name = f"{label} ({metric:.3f})" if metric is not None else label
        fig.add_trace(go.Scatter(x=s[x], y=s[y], mode="lines", name=name,
                                 line=dict(color=palette[i % len(palette)], width=2)))
    if diagonal:
        fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", name="chance",
                                 line=dict(color="#C7C9D9", dash="dash")))
    fig.update_layout(template="plotly_white", height=330, margin=dict(l=0, r=0, t=6, b=0),
                      legend=dict(orientation="h", y=-0.2))
    return fig


def render_model_diagnostics(df: pd.DataFrame, target: str, model_name: str) -> None:
    st.caption("Diagnostics for the best model. These recompute on the same train/test split.")

    # ROC & PR curves
    try:
        curves = diagnostics.roc_pr_curves(df, target, model_name)
    except ValueError as e:
        st.info(str(e))
        return

    if curves.get("available"):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("##### ROC curve")
            st.plotly_chart(_curve_fig(curves["roc"], "fpr", "tpr", "ROC", diagonal=True),
                            use_container_width=True)
        with c2:
            st.markdown("##### Precision-recall curve")
            st.plotly_chart(_curve_fig(curves["pr"], "recall", "precision", "PR"),
                            use_container_width=True)
    else:
        st.caption("ROC / PR curves apply to classification only.")

    # Hyper-parameter tuning + learning curve (on demand — they are heavier)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("##### Hyper-parameter tuning")
        if st.button("Run GridSearchCV", key="btn_tune", width="stretch"):
            with st.spinner("Searching the hyper-parameter grid…"):
                t = diagnostics.tune_hyperparameters(df, target, model_name)
            if not t.get("tunable"):
                st.caption(t.get("note", "No tunable parameters."))
            else:
                delta = t["improvement"]
                C._kpi_cards([
                    ("Default CV", f"{t['default_cv']:.3f}", C.INK),
                    ("Tuned CV", f"{t['tuned_cv']:.3f}", TEAL if delta >= 0 else C.INK),
                    ("Improvement", f"{delta:+.3f}", TEAL if delta > 0 else MUTED),
                ])
                st.caption(f"Best params ({t['n_combinations']} combos, {t['scoring']}): "
                           f"`{t['best_params']}`")
    with col2:
        st.markdown("##### Learning curve")
        if st.button("Compute learning curve", key="btn_lc", width="stretch"):
            with st.spinner("Fitting across training sizes…"):
                lc = diagnostics.learning_curve_data(df, target, model_name)
            t = lc["table"]
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=t["train_size"], y=t["train_score"], name="training",
                                     mode="lines+markers", line=dict(color=INDIGO)))
            fig.add_trace(go.Scatter(x=t["train_size"], y=t["cv_score"], name="cross-val",
                                     mode="lines+markers", line=dict(color=TEAL)))
            fig.update_layout(template="plotly_white", height=300, margin=dict(l=0, r=0, t=6, b=0),
                              xaxis_title="training samples", yaxis_title=lc["scoring"],
                              legend=dict(orientation="h", y=-0.25))
            st.plotly_chart(fig, use_container_width=True)
            gap = float(t["train_score"].iloc[-1] - t["cv_score"].iloc[-1])
            st.caption(f"Train–CV gap at full size: {gap:.3f} "
                       f"({'possible overfitting' if gap > 0.1 else 'healthy generalisation'}).")


# ──────────────────────────────────────────────────────────────────────────────
# Feature engineering / selection
# ──────────────────────────────────────────────────────────────────────────────
def render_feature_lab(df: pd.DataFrame, target: str) -> None:
    st.caption("Rank features by their relationship to the target, then measure the "
               "impact of keeping only the strongest ones.")
    try:
        ranking = feature_engineering.feature_ranking(df, target)
    except ValueError as e:
        st.info(str(e))
        return

    st.markdown("##### Feature ranking")
    st.caption("F-test score (univariate strength) and RFE rank (model-based). Lower RFE rank = kept earlier.")
    st.dataframe(ranking, width="stretch")

    if st.button("Measure selection impact & engineered feature", key="btn_fl", width="stretch"):
        with st.spinner("Cross-validating feature subsets…"):
            impact = feature_engineering.selection_impact(df, target)
            inter = feature_engineering.engineered_interaction(df, target)
        d = impact["delta"]
        C._kpi_cards([
            (f"All {impact['n_features_total']} features (CV)", f"{impact['all_features_cv']:.3f}", C.INK),
            (f"Top {impact['k']} features (CV)", f"{impact['topk_cv']:.3f}", TEAL if d >= 0 else C.INK),
            ("Difference", f"{d:+.3f}", TEAL if d >= -0.02 else "#D9534F"),
        ])
        st.caption(f"Top features kept: {', '.join('`'+f+'`' for f in impact['top_features'])}")
        if inter.get("available"):
            di = inter["delta"]
            st.markdown(f"**Engineered interaction** `{inter['interaction']}` → "
                        f"CV {inter['baseline_cv']:.3f} → {inter['with_interaction_cv']:.3f} "
                        f"(**{di:+.3f}**, {inter['scoring']}).")


# ──────────────────────────────────────────────────────────────────────────────
# Deeper inferential statistics
# ──────────────────────────────────────────────────────────────────────────────
def render_deeper_statistics(df: pd.DataFrame) -> None:
    num = eda.numeric_columns(df)
    cat = eda.categorical_columns(df)

    st.markdown("##### 95% confidence intervals for the mean")
    if num:
        rows = []
        for c in num:
            ci = statistics.confidence_interval(df[c])
            rows.append({"feature": c, "mean": ci["mean"], "ci_low": ci["low"],
                         "ci_high": ci["high"], "n": ci["n"]})
        st.dataframe(pd.DataFrame(rows).set_index("feature"), width="stretch")
    else:
        st.caption("No numeric columns.")

    st.markdown("##### Test-assumption check (which test is valid?)")
    if num and cat:
        c1, c2 = st.columns(2)
        ncol = c1.selectbox("Numeric variable", num, key="ac_num")
        gcol = c2.selectbox("Group by", cat, key="ac_grp")
        res = statistics.assumption_checks(df, ncol, gcol)
        if res.get("ok"):
            C._kpi_cards([
                ("Groups normal?", "yes" if res["all_groups_normal"] else "no",
                 TEAL if res["all_groups_normal"] else "#D9534F"),
                ("Equal variance?", "yes" if res["equal_variance"] else "no",
                 TEAL if res["equal_variance"] else "#D9534F"),
                ("Levene p", f"{res['levene_p']:.3f}", C.INK),
            ])
            st.success(f"Recommended test: **{res['recommended_test']}**")
        else:
            st.caption(res.get("note", ""))
    else:
        st.caption("Need at least one numeric and one categorical column.")

    st.markdown("##### Multiple-testing correction (feature → target screen)")
    st.caption("When many features are screened, raw p-values overstate significance. "
               "Benjamini-Hochberg (FDR) correction is applied below.")
    from ml import modeling
    target = modeling.suggest_target(df)
    if target:
        screen = statistics.feature_target_screen(df, target)
        if not screen.empty:
            corrected = statistics.correct_pvalues(screen["p_value"].tolist(), method="fdr_bh")
            screen = screen.reset_index(drop=True)
            screen["p_adjusted (FDR)"] = corrected["p_adjusted"]
            screen["significant (FDR)"] = np.where(corrected["reject"], "yes", "no")
            st.caption(f"Target: `{target}`")
            st.dataframe(C.format_pvalues(screen, ["p_value", "p_adjusted (FDR)"]),
                         width="stretch")
        else:
            st.caption("Not enough data to screen features.")
