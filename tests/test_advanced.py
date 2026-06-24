"""Tests for the advanced data-science modules: unsupervised learning,
model diagnostics, feature engineering, and the extended statistics."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ml import unsupervised, diagnostics, feature_engineering, statistics


# ── Unsupervised ─────────────────────────────────────────────────────────────
def test_pca(clean_df):
    res = unsupervised.run_pca(clean_df)
    var = res["variance"]
    assert abs(var["explained_variance"].sum() - 1.0) < 0.05
    assert var["cumulative"].is_monotonic_increasing
    assert res["pc1_pct"] >= res["pc2_pct"]
    assert {"PC1", "PC2"}.issubset(res["projection"].columns)


def test_clustering_auto_k(clean_df):
    res = unsupervised.run_clustering(clean_df)
    assert 2 <= res["k"] <= 8
    assert -1.0 <= res["silhouette"] <= 1.0
    assert "size" in res["profiles"].columns
    assert res["profiles"]["size"].sum() == len(clean_df)
    assert "cluster" in res["projection"].columns


# ── Diagnostics ──────────────────────────────────────────────────────────────
def test_roc_pr_curves(clean_df):
    res = diagnostics.roc_pr_curves(clean_df, "promoted", "Random Forest")
    assert res["available"] is True
    assert res["binary"] is True
    auc = res["roc"][0]["auc"]
    assert 0.0 <= auc <= 1.0
    assert 0.0 <= res["pr"][0]["ap"] <= 1.0


def test_tune_hyperparameters(clean_df):
    res = diagnostics.tune_hyperparameters(clean_df, "promoted", "Logistic Regression")
    assert res["tunable"] is True
    assert "best_params" in res and isinstance(res["best_params"], dict)
    assert -1.0 <= res["tuned_cv"] <= 1.0


def test_learning_curve(clean_df):
    res = diagnostics.learning_curve_data(clean_df, "promoted", "Random Forest")
    t = res["table"]
    assert {"train_size", "train_score", "cv_score"}.issubset(t.columns)
    assert t["train_size"].is_monotonic_increasing


# ── Feature engineering ──────────────────────────────────────────────────────
def test_feature_ranking(clean_df):
    rank = feature_engineering.feature_ranking(clean_df, "promoted")
    feats = set(rank["feature"])
    assert "emp_id" not in feats            # identifier excluded
    assert "promoted" not in feats          # target excluded
    assert {"f_score", "f_pvalue", "rfe_rank"}.issubset(rank.columns)
    # performance_score drives the target → should rank highly
    assert "performance_score" in rank["feature"].head(3).tolist()


def test_selection_impact(clean_df):
    res = feature_engineering.selection_impact(clean_df, "promoted")
    assert "all_features_cv" in res and "topk_cv" in res
    assert res["k"] <= res["n_features_total"]


def test_engineered_interaction(clean_df):
    res = feature_engineering.engineered_interaction(clean_df, "promoted")
    assert res["available"] is True
    assert "×" in res["interaction"]


# ── Extended statistics ──────────────────────────────────────────────────────
def test_multiple_testing_correction():
    pvals = [0.001, 0.02, 0.03, 0.04, 0.5]
    bonf = statistics.correct_pvalues(pvals, method="bonferroni")
    fdr = statistics.correct_pvalues(pvals, method="fdr_bh")
    # adjusted p-values are never smaller than the raw ones
    assert (bonf["p_adjusted"] >= bonf["p_value"] - 1e-9).all()
    assert (fdr["p_adjusted"] >= fdr["p_value"] - 1e-9).all()
    # bonferroni is at least as conservative as BH-FDR
    assert (bonf["p_adjusted"] >= fdr["p_adjusted"] - 1e-9).all()


def test_cohens_d_large_for_separated_groups():
    rng = np.random.default_rng(0)
    a = rng.normal(0, 1, 100)
    b = rng.normal(3, 1, 100)
    assert abs(statistics.cohens_d(a, b)) > 0.8


def test_eta_squared_range(clean_df):
    e = statistics.eta_squared(clean_df, "salary", "department")
    assert 0.0 <= e <= 1.0


def test_confidence_interval(clean_df):
    ci = statistics.confidence_interval(clean_df["salary"])
    assert ci["low"] < ci["mean"] < ci["high"]


def test_assumption_checks(clean_df):
    res = statistics.assumption_checks(clean_df, "salary", "department")
    assert res["ok"] is True
    assert "recommended_test" in res
