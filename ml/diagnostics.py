"""
Model diagnostics: ROC / precision-recall curves, hyper-parameter tuning, and
learning curves.

These are the tools a data scientist uses to *trust* a model rather than just
quote a single accuracy number. All routines reuse the leakage-safe pipeline
and the same train/test split as ``ml.modeling`` (fixed random_state), so the
diagnostics correspond exactly to the reported model.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from sklearn.metrics import (
    average_precision_score,
    precision_recall_curve,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import GridSearchCV, learning_curve, train_test_split
from sklearn.pipeline import Pipeline

from ml import modeling

RS = modeling.RANDOM_STATE


# ──────────────────────────────────────────────────────────────────────────────
# Shared preparation (mirrors ml.modeling.train_and_evaluate)
# ──────────────────────────────────────────────────────────────────────────────
def _prepare(df: pd.DataFrame, target: str):
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
    stratify = y if (task == "classification" and y.value_counts().min() >= 2) else None
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.2, random_state=RS, stratify=stratify)
    return X, y, X_tr, X_te, y_tr, y_te, task


def _pipe(X, model_name, task):
    models = modeling._candidate_models(task)
    model = models[model_name] if model_name in models else next(iter(models.values()))
    return Pipeline([("pre", modeling.build_preprocessor(X)), ("model", model)])


# ──────────────────────────────────────────────────────────────────────────────
# ROC & precision-recall curves (classification only)
# ──────────────────────────────────────────────────────────────────────────────
def roc_pr_curves(df: pd.DataFrame, target: str, model_name: str) -> dict:
    X, y, X_tr, X_te, y_tr, y_te, task = _prepare(df, target)
    if task != "classification":
        return {"task": task, "available": False}

    pipe = _pipe(X, model_name, task)
    pipe.fit(X_tr, y_tr)
    if not hasattr(pipe[-1], "predict_proba"):
        return {"task": task, "available": False}

    proba = pipe.predict_proba(X_te)
    classes = list(pipe[-1].classes_)
    roc, pr = [], []

    if len(classes) == 2:
        pos = classes[1]
        y_bin = (np.asarray(y_te) == pos).astype(int)
        score = proba[:, 1]
        fpr, tpr, _ = roc_curve(y_bin, score)
        prec, rec, _ = precision_recall_curve(y_bin, score)
        roc.append({"label": f"positive = {pos}", "fpr": fpr.round(4).tolist(),
                    "tpr": tpr.round(4).tolist(), "auc": round(roc_auc_score(y_bin, score), 4)})
        pr.append({"label": f"positive = {pos}", "recall": rec.round(4).tolist(),
                   "precision": prec.round(4).tolist(),
                   "ap": round(average_precision_score(y_bin, score), 4)})
    else:
        for i, c in enumerate(classes[:6]):
            y_bin = (np.asarray(y_te) == c).astype(int)
            if y_bin.sum() == 0:
                continue
            score = proba[:, i]
            fpr, tpr, _ = roc_curve(y_bin, score)
            prec, rec, _ = precision_recall_curve(y_bin, score)
            roc.append({"label": str(c), "fpr": fpr.round(4).tolist(),
                        "tpr": tpr.round(4).tolist(), "auc": round(roc_auc_score(y_bin, score), 4)})
            pr.append({"label": str(c), "recall": rec.round(4).tolist(),
                       "precision": prec.round(4).tolist(),
                       "ap": round(average_precision_score(y_bin, score), 4)})

    return {"task": task, "available": True, "binary": len(classes) == 2, "roc": roc, "pr": pr}


# ──────────────────────────────────────────────────────────────────────────────
# Hyper-parameter tuning (GridSearchCV)
# ──────────────────────────────────────────────────────────────────────────────
_GRIDS = {
    "Logistic Regression": {"model__C": [0.1, 1.0, 10.0]},
    "Random Forest": {"model__n_estimators": [100, 200], "model__max_depth": [None, 5, 10]},
    "Gradient Boosting": {"model__learning_rate": [0.05, 0.1],
                          "model__n_estimators": [100, 200], "model__max_depth": [2, 3]},
}


def tune_hyperparameters(df: pd.DataFrame, target: str, model_name: str) -> dict:
    X, y, X_tr, X_te, y_tr, y_te, task = _prepare(df, target)
    scoring = "f1_weighted" if task == "classification" else "r2"
    grid = _GRIDS.get(model_name)
    pipe = _pipe(X, model_name, task)

    if not grid:
        return {"model": model_name, "tunable": False, "scoring": scoring,
                "note": f"{model_name} has no tunable hyper-parameters in this setup."}

    n_splits = max(2, min(5, int(y_tr.value_counts().min()) if task == "classification" else 5))
    base = pipe.fit(X_tr, y_tr)
    from sklearn.model_selection import cross_val_score
    default_score = float(np.mean(cross_val_score(_pipe(X, model_name, task), X_tr, y_tr,
                                                  cv=n_splits, scoring=scoring)))
    gs = GridSearchCV(pipe, grid, scoring=scoring, cv=n_splits, n_jobs=-1)
    gs.fit(X_tr, y_tr)
    best_params = {k.replace("model__", ""): v for k, v in gs.best_params_.items()}
    return {
        "model": model_name, "tunable": True, "scoring": scoring,
        "default_cv": round(default_score, 4),
        "tuned_cv": round(float(gs.best_score_), 4),
        "improvement": round(float(gs.best_score_) - default_score, 4),
        "best_params": best_params,
        "n_combinations": len(gs.cv_results_["params"]),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Learning curve (over/underfitting diagnosis)
# ──────────────────────────────────────────────────────────────────────────────
def learning_curve_data(df: pd.DataFrame, target: str, model_name: str) -> dict:
    X, y, X_tr, X_te, y_tr, y_te, task = _prepare(df, target)
    scoring = "f1_weighted" if task == "classification" else "r2"
    n_splits = max(2, min(5, int(y.value_counts().min()) if task == "classification" else 5))
    pipe = _pipe(X, model_name, task)

    sizes, train_scores, val_scores = learning_curve(
        pipe, X, y, cv=n_splits, scoring=scoring,
        train_sizes=np.linspace(0.2, 1.0, 5), random_state=RS, shuffle=True)

    return {
        "scoring": scoring,
        "table": pd.DataFrame({
            "train_size": sizes.astype(int),
            "train_score": train_scores.mean(axis=1).round(4),
            "cv_score": val_scores.mean(axis=1).round(4),
        }),
    }
