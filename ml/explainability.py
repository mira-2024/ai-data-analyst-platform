"""
ml/explainability.py — SHAP-based model explainability.

Computes SHAP (SHapley Additive exPlanations) values for any sklearn Pipeline
trained by ml.modeling. Provides:

  - Global feature importance (mean |SHAP|)
  - Per-sample SHAP values for beeswarm / dot plots
  - Individual prediction breakdowns

Supports:
  - TreeExplainer   → Random Forest, Gradient Boosting (fast, exact)
  - LinearExplainer → Logistic Regression, Linear Regression (fast, exact)
  - KernelExplainer → any model (slow, approximate fallback)

Reference: Lundberg & Lee (2017) — "A Unified Approach to Interpreting
Model Predictions." NeurIPS.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline


# ──────────────────────────────────────────────────────────────────────────────
# Feature name helpers
# ──────────────────────────────────────────────────────────────────────────────

def _get_feature_names(pipeline: Pipeline, X: pd.DataFrame) -> list[str]:
    """Extract feature names after the preprocessing step."""
    pre = pipeline[:-1]
    try:
        return list(pre.get_feature_names_out())
    except Exception:
        pass
    try:
        ct = list(pre.named_steps.values())[0]
        return list(ct.get_feature_names_out())
    except Exception:
        n = pre.transform(X.iloc[:1]).shape[1]
        return [f"feature_{i}" for i in range(n)]


def _clean_feature_names(names: list[str]) -> list[str]:
    """Strip ColumnTransformer prefixes: 'num__age' → 'age'."""
    cleaned = []
    for n in names:
        for prefix in ("num__", "cat__", "remainder__"):
            if n.startswith(prefix):
                n = n[len(prefix):]
                break
        cleaned.append(n)
    return cleaned


# ──────────────────────────────────────────────────────────────────────────────
# Core SHAP computation
# ──────────────────────────────────────────────────────────────────────────────

_TREE_MODELS = (
    "RandomForestClassifier", "RandomForestRegressor",
    "GradientBoostingClassifier", "GradientBoostingRegressor",
    "ExtraTreesClassifier", "ExtraTreesRegressor",
    "DecisionTreeClassifier", "DecisionTreeRegressor",
    "XGBClassifier", "XGBRegressor",
    "LGBMClassifier", "LGBMRegressor",
)

_LINEAR_MODELS = (
    "LogisticRegression", "LinearRegression",
    "Ridge", "Lasso", "ElasticNet", "SGDClassifier",
)


def compute_shap(
    pipeline: Pipeline,
    X: pd.DataFrame,
    task: str,
    max_samples: int = 200,
) -> dict:
    """
    Compute SHAP values for a fitted sklearn Pipeline on dataset X.

    Parameters
    ----------
    pipeline   : fitted sklearn Pipeline (preprocessor + model)
    X          : original (un-transformed) feature DataFrame
    task       : 'classification' or 'regression'
    max_samples: cap the sample count for speed

    Returns
    -------
    dict with keys:
        shap_values     : np.ndarray  shape (n_samples, n_features)
        feature_names   : list[str]
        X_transformed   : pd.DataFrame  preprocessed features
        expected_value  : float
        explainer_type  : str
    """
    try:
        import shap
    except ImportError as exc:
        raise ImportError(
            "shap is not installed. Run: pip install shap"
        ) from exc

    model = pipeline[-1]
    pre = pipeline[:-1]
    model_type = type(model).__name__

    # Subsample for speed
    if len(X) > max_samples:
        X = X.sample(max_samples, random_state=42)

    X_transformed = pre.transform(X)
    raw_names = _get_feature_names(pipeline, X)
    feature_names = _clean_feature_names(raw_names)

    # ── Tree models ────────────────────────────────────────────────────────
    if model_type in _TREE_MODELS:
        explainer = shap.TreeExplainer(model)
        raw = explainer.shap_values(X_transformed)

        # Binary classification: shap_values is a list [class0, class1]
        if isinstance(raw, list):
            shap_vals = raw[1] if len(raw) == 2 else raw[0]
        else:
            shap_vals = raw

        ev = explainer.expected_value
        if hasattr(ev, "__len__"):
            expected_value = float(ev[1]) if len(ev) == 2 else float(ev[0])
        else:
            expected_value = float(ev)
        explainer_type = "TreeExplainer"

    # ── Linear models ──────────────────────────────────────────────────────
    elif model_type in _LINEAR_MODELS:
        explainer = shap.LinearExplainer(model, X_transformed)
        raw = explainer.shap_values(X_transformed)

        if isinstance(raw, list):
            shap_vals = raw[1] if len(raw) == 2 else raw[0]
        else:
            shap_vals = raw

        ev = explainer.expected_value
        expected_value = float(np.mean(ev) if hasattr(ev, "__len__") else ev)
        explainer_type = "LinearExplainer"

    # ── Fallback: KernelExplainer ──────────────────────────────────────────
    else:
        background = shap.sample(X_transformed, min(50, len(X_transformed)))
        if task == "classification" and hasattr(model, "predict_proba"):
            fn = lambda x: model.predict_proba(x)[:, 1]
        else:
            fn = model.predict
        explainer = shap.KernelExplainer(fn, background)
        sample = X_transformed[: min(50, len(X_transformed))]
        shap_vals = explainer.shap_values(sample, nsamples=100)
        expected_value = float(explainer.expected_value)
        explainer_type = "KernelExplainer"

    return {
        "shap_values": np.asarray(shap_vals),
        "feature_names": feature_names,
        "X_transformed": pd.DataFrame(X_transformed, columns=feature_names),
        "expected_value": expected_value,
        "explainer_type": explainer_type,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Aggregation helpers
# ──────────────────────────────────────────────────────────────────────────────

def shap_feature_importance(shap_result: dict) -> pd.DataFrame:
    """
    Global feature importance = mean |SHAP| across all samples.
    Returns DataFrame with columns ['feature', 'mean_abs_shap'].
    """
    vals = np.abs(shap_result["shap_values"]).mean(axis=0)
    df = pd.DataFrame({
        "feature": shap_result["feature_names"],
        "mean_abs_shap": vals.round(5),
    })
    return df.sort_values("mean_abs_shap", ascending=False).reset_index(drop=True)


def shap_summary_data(shap_result: dict, top_n: int = 15) -> pd.DataFrame:
    """
    Tidy long-format DataFrame for a SHAP beeswarm / dot plot.

    Columns: feature, shap_value, feature_value_norm
    Top N features selected by mean |SHAP|.
    """
    sv = shap_result["shap_values"]
    X_df = shap_result["X_transformed"]
    names = shap_result["feature_names"]

    importance = np.abs(sv).mean(axis=0)
    top_idx = np.argsort(importance)[::-1][:top_n]

    rows = []
    for i in top_idx:
        col_vals = X_df.iloc[:, i].values.astype(float)
        col_min, col_max = col_vals.min(), col_vals.max()
        norm = (col_vals - col_min) / (col_max - col_min + 1e-9)
        for j in range(len(sv)):
            rows.append({
                "feature": names[i],
                "shap_value": float(sv[j, i]),
                "feature_value_norm": float(norm[j]),
            })

    return pd.DataFrame(rows)


def shap_waterfall_data(shap_result: dict, sample_idx: int = 0) -> pd.DataFrame:
    """
    SHAP waterfall data for a single prediction (sample_idx).
    Returns DataFrame sorted by |SHAP| descending.
    Columns: feature, shap_value, feature_value
    """
    sv = shap_result["shap_values"]
    X_df = shap_result["X_transformed"]
    names = shap_result["feature_names"]

    if sample_idx >= len(sv):
        sample_idx = 0

    row_shap = sv[sample_idx]
    row_feat = X_df.iloc[sample_idx].values

    df = pd.DataFrame({
        "feature": names,
        "shap_value": row_shap.round(5),
        "feature_value": row_feat,
    })
    df["abs_shap"] = df["shap_value"].abs()
    return df.sort_values("abs_shap", ascending=False).drop(columns="abs_shap").reset_index(drop=True)
