"""
Feature engineering & selection.

Implements the classic data-science workflow of ranking features by their
statistical relationship to the target (univariate F-test), confirming with a
model-based wrapper method (Recursive Feature Elimination), and quantifying the
*impact* of selection by comparing cross-validated model performance using all
features versus the top-k. Also demonstrates a simple engineered interaction
feature and its effect. Pure scikit-learn.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.feature_selection import RFE, f_classif, f_regression
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.model_selection import cross_val_score
from sklearn.pipeline import Pipeline

from ml import modeling

RS = modeling.RANDOM_STATE


def _prep(df: pd.DataFrame, target: str):
    if target not in df.columns:
        raise ValueError(f"target '{target}' not found")
    data = df.dropna(subset=[target]).copy()
    if len(data) < 20:
        raise ValueError("need >= 20 rows with a known target")
    drop_cols = [c for c in data.columns if c != target and modeling._looks_like_id(data, c)]
    X = data.drop(columns=[target] + drop_cols)
    y = data[target]
    if X.shape[1] == 0:
        raise ValueError("no usable feature columns")
    task = modeling.detect_task(df, target)
    return X, y, task


def _orig_feature_map(X: pd.DataFrame, pre) -> list[str]:
    """Original feature owning each transformed (one-hot expanded) column."""
    num_cols = X.select_dtypes(include=np.number).columns.tolist()
    cat_cols = [c for c in X.columns if c not in num_cols]
    owners = list(num_cols)
    if cat_cols:
        ohe = pre.named_transformers_["cat"].named_steps["encode"]
        for ci, _cat in enumerate(cat_cols):
            owners += [cat_cols[ci]] * len(ohe.categories_[ci])
    return owners


def _scoring(task: str) -> str:
    return "f1_weighted" if task == "classification" else "r2"


# ──────────────────────────────────────────────────────────────────────────────
# Univariate ranking (F-test) + model-based ranking (RFE)
# ──────────────────────────────────────────────────────────────────────────────
def feature_ranking(df: pd.DataFrame, target: str) -> pd.DataFrame:
    """
    Rank original features by univariate F-test strength and by RFE order.
    Returns one row per original feature with f_score, f_pvalue and rfe_rank.
    """
    X, y, task = _prep(df, target)
    pre = modeling.build_preprocessor(X)
    Xt = pre.fit_transform(X)
    owners = _orig_feature_map(X, pre)

    f_fn = f_classif if task == "classification" else f_regression
    f_scores, f_pvals = f_fn(Xt, y)

    estimator = (LogisticRegression(max_iter=1000) if task == "classification"
                 else LinearRegression())
    n_keep = max(1, Xt.shape[1] // 2)
    rfe = RFE(estimator, n_features_to_select=n_keep)
    rfe.fit(Xt, y)

    df_t = pd.DataFrame({"feature": owners, "f_score": f_scores,
                         "f_pvalue": f_pvals, "rfe_rank": rfe.ranking_})
    # aggregate transformed columns back to the original feature
    agg = df_t.groupby("feature").agg(
        f_score=("f_score", "max"), f_pvalue=("f_pvalue", "min"),
        rfe_rank=("rfe_rank", "min")).reset_index()
    agg["f_score"] = agg["f_score"].round(3)
    agg["f_pvalue"] = agg["f_pvalue"].round(5)
    return agg.sort_values("f_score", ascending=False).reset_index(drop=True)


# ──────────────────────────────────────────────────────────────────────────────
# Selection impact: all features vs top-k
# ──────────────────────────────────────────────────────────────────────────────
def selection_impact(df: pd.DataFrame, target: str, k: int | None = None) -> dict:
    """Compare CV performance using all features vs the top-k ranked features."""
    X, y, task = _prep(df, target)
    ranking = feature_ranking(df, target)
    total = len(ranking)
    k = k or max(1, total // 2)
    top = ranking["feature"].head(k).tolist()

    scoring = _scoring(task)
    n_splits = max(2, min(5, int(y.value_counts().min()) if task == "classification" else 5))

    def cv(cols):
        sub = X[cols]
        pipe = Pipeline([("pre", modeling.build_preprocessor(sub)),
                         ("model", list(modeling._candidate_models(task).values())[1])])  # RF
        return float(np.mean(cross_val_score(pipe, sub, y, cv=n_splits, scoring=scoring)))

    all_score = cv(list(X.columns))
    top_score = cv(top)
    return {
        "scoring": scoring, "n_features_total": total, "k": k,
        "top_features": top,
        "all_features_cv": round(all_score, 4),
        "topk_cv": round(top_score, 4),
        "delta": round(top_score - all_score, 4),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Engineered interaction feature
# ──────────────────────────────────────────────────────────────────────────────
def engineered_interaction(df: pd.DataFrame, target: str) -> dict:
    """
    Add an interaction term (product of the two strongest numeric features) and
    measure the change in cross-validated score. Illustrates feature engineering.
    """
    X, y, task = _prep(df, target)
    num_cols = X.select_dtypes(include=np.number).columns.tolist()
    if len(num_cols) < 2:
        return {"available": False, "note": "need >= 2 numeric features for an interaction"}

    ranking = feature_ranking(df, target)
    num_ranked = [f for f in ranking["feature"] if f in num_cols][:2]
    if len(num_ranked) < 2:
        return {"available": False, "note": "not enough numeric features after ranking"}
    a, b = num_ranked

    scoring = _scoring(task)
    n_splits = max(2, min(5, int(y.value_counts().min()) if task == "classification" else 5))
    model = list(modeling._candidate_models(task).values())[1]  # Random Forest

    def cv(frame):
        pipe = Pipeline([("pre", modeling.build_preprocessor(frame)), ("model", model)])
        return float(np.mean(cross_val_score(pipe, frame, y, cv=n_splits, scoring=scoring)))

    base = cv(X)
    X2 = X.copy()
    X2[f"{a}_x_{b}"] = X2[a] * X2[b]
    enriched = cv(X2)
    return {
        "available": True, "scoring": scoring,
        "interaction": f"{a} × {b}",
        "baseline_cv": round(base, 4),
        "with_interaction_cv": round(enriched, 4),
        "delta": round(enriched - base, 4),
    }
