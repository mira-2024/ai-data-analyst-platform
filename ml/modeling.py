"""
Supervised machine-learning pipeline.

Given a DataFrame and a target column, this module:

  1. detects whether the problem is classification or regression,
  2. builds a leakage-safe preprocessing pipeline (impute + scale numeric,
     impute + one-hot encode categorical),
  3. trains several candidate models with k-fold cross-validation,
  4. evaluates them on a held-out test set with the appropriate metrics,
  5. estimates feature importance for the best model.

Everything is implemented with scikit-learn. No language model is involved, so
results are deterministic (fixed ``random_state``) and fully reproducible.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import (
    GradientBoostingClassifier,
    GradientBoostingRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
    confusion_matrix,
)
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from ml import eda

RANDOM_STATE = 42
MAX_CLASS_CARDINALITY = 20  # numeric target with <= this many classes => classification


# ──────────────────────────────────────────────────────────────────────────────
# Task & target detection
# ──────────────────────────────────────────────────────────────────────────────
def detect_task(df: pd.DataFrame, target: str) -> str:
    """Return 'classification' or 'regression' for the given target column."""
    y = df[target].dropna()
    if y.dtype == object or str(y.dtype) in ("category", "bool"):
        return "classification"
    # Numeric but few distinct values → treat as class labels.
    if y.nunique() <= MAX_CLASS_CARDINALITY:
        return "classification"
    return "regression"


def suggest_target(df: pd.DataFrame) -> str | None:
    """
    Heuristic for the most plausible target column when the user doesn't pick
    one: prefer a low-cardinality categorical/boolean column (a label), else the
    last numeric column. ID-like columns are skipped.
    """
    candidates = [c for c in df.columns if not _looks_like_id(df, c)]
    if not candidates:
        candidates = list(df.columns)

    # 0) columns whose name suggests they are the target/label.
    target_words = ("target", "label", "outcome", "class", "result", "churn",
                    "promoted", "converted", "default", "survived", "approved", "y")
    for col in candidates:
        if col.lower() in target_words or any(w in col.lower() for w in target_words):
            if 2 <= df[col].nunique(dropna=True) <= MAX_CLASS_CARDINALITY:
                return col

    # 1) binary / low-cardinality categorical labels (prefer the last such column,
    #    as targets are conventionally placed at the end of a dataset).
    for col in reversed(candidates):
        nun = df[col].nunique(dropna=True)
        if df[col].dtype == object or str(df[col].dtype) in ("category", "bool"):
            if 2 <= nun <= MAX_CLASS_CARDINALITY:
                return col
    # 2) low-cardinality numeric (encoded labels)
    for col in reversed(candidates):
        if col in eda.numeric_columns(df) and 2 <= df[col].nunique(dropna=True) <= MAX_CLASS_CARDINALITY:
            return col
    # 3) fall back to last numeric column
    num = [c for c in eda.numeric_columns(df) if c in candidates]
    return num[-1] if num else (candidates[-1] if candidates else None)


def _looks_like_id(df: pd.DataFrame, col: str) -> bool:
    name = col.lower()
    if name in ("id", "index", "uuid") or name.endswith("_id") or name.endswith("id"):
        if df[col].nunique() > 0.9 * len(df):
            return True
    # A near-unique *non-numeric* column (names, codes, UUIDs) is an identifier.
    # Continuous numeric columns are legitimately near-unique (every float differs)
    # and are real features, so they must NEVER be treated as IDs.
    return (
        df[col].nunique() >= 0.98 * len(df)
        and len(df) > 10
        and not pd.api.types.is_numeric_dtype(df[col])
    )


# ──────────────────────────────────────────────────────────────────────────────
# Preprocessing
# ──────────────────────────────────────────────────────────────────────────────
def build_preprocessor(X: pd.DataFrame) -> ColumnTransformer:
    """Impute + scale numeric features; impute + one-hot encode categoricals."""
    num_cols = X.select_dtypes(include=np.number).columns.tolist()
    cat_cols = [c for c in X.columns if c not in num_cols]

    numeric_pipe = Pipeline(
        [("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]
    )
    # handle_unknown='ignore' keeps test-time categories the model never saw safe.
    try:
        ohe = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:  # older sklearn
        ohe = OneHotEncoder(handle_unknown="ignore", sparse=False)
    categorical_pipe = Pipeline(
        [("impute", SimpleImputer(strategy="most_frequent")), ("encode", ohe)]
    )

    return ColumnTransformer(
        [("num", numeric_pipe, num_cols), ("cat", categorical_pipe, cat_cols)],
        remainder="drop",
    )


def _candidate_models(task: str) -> dict:
    if task == "classification":
        return {
            "Logistic Regression": LogisticRegression(max_iter=1000),
            "Random Forest": RandomForestClassifier(
                n_estimators=200, random_state=RANDOM_STATE, n_jobs=-1
            ),
            "Gradient Boosting": GradientBoostingClassifier(random_state=RANDOM_STATE),
        }
    return {
        "Linear Regression": LinearRegression(),
        "Random Forest": RandomForestRegressor(
            n_estimators=200, random_state=RANDOM_STATE, n_jobs=-1
        ),
        "Gradient Boosting": GradientBoostingRegressor(random_state=RANDOM_STATE),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Metrics
# ──────────────────────────────────────────────────────────────────────────────
def _classification_metrics(y_true, y_pred, y_proba=None) -> dict:
    # "weighted" averaging works for any label dtype (string or numeric) and any
    # number of classes, avoiding the pos_label ambiguity of "binary".
    classes = np.unique(y_true)
    m = {
        "accuracy": round(accuracy_score(y_true, y_pred), 4),
        "precision": round(precision_score(y_true, y_pred, average="weighted", zero_division=0), 4),
        "recall": round(recall_score(y_true, y_pred, average="weighted", zero_division=0), 4),
        "f1": round(f1_score(y_true, y_pred, average="weighted", zero_division=0), 4),
    }
    if y_proba is not None:
        try:
            if len(classes) == 2:
                # Binarise against the second (sorted) class = positive class.
                y_bin = (np.asarray(y_true) == classes[1]).astype(int)
                m["roc_auc"] = round(roc_auc_score(y_bin, y_proba[:, 1]), 4)
            else:
                m["roc_auc"] = round(
                    roc_auc_score(y_true, y_proba, multi_class="ovr", average="weighted"), 4
                )
        except Exception:
            pass
    return m


def _regression_metrics(y_true, y_pred) -> dict:
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    return {
        "r2": round(r2_score(y_true, y_pred), 4),
        "rmse": round(rmse, 4),
        "mae": round(mean_absolute_error(y_true, y_pred), 4),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Main entry point
# ──────────────────────────────────────────────────────────────────────────────
def train_and_evaluate(
    df: pd.DataFrame,
    target: str,
    test_size: float = 0.2,
    cv_folds: int = 5,
) -> dict:
    """
    Train and evaluate candidate models for ``target``.

    Returns a dict with the detected task, per-model metrics, the chosen best
    model, cross-validation scores, feature importances, and (for
    classification) the confusion matrix. Raises ValueError on unusable input.
    """
    if target not in df.columns:
        raise ValueError(f"target column '{target}' not found")

    data = df.dropna(subset=[target]).copy()
    if len(data) < 20:
        raise ValueError("not enough rows with a known target (need >= 20)")

    # Drop obvious identifier columns from the feature set.
    drop_cols = [c for c in data.columns if c != target and _looks_like_id(data, c)]
    X = data.drop(columns=[target] + drop_cols)
    y = data[target]
    if X.shape[1] == 0:
        raise ValueError("no usable feature columns after removing identifiers")

    task = detect_task(df, target)
    primary_metric = "f1" if task == "classification" else "r2"
    scoring = "f1_weighted" if task == "classification" else "r2"

    # Stratify classification splits when each class has enough samples.
    stratify = y if (task == "classification" and y.value_counts().min() >= 2) else None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=RANDOM_STATE, stratify=stratify
    )

    pre = build_preprocessor(X)
    results = []
    fitted = {}
    n_splits = max(2, min(cv_folds, int(y_train.value_counts().min()) if task == "classification"
                          else cv_folds))

    for name, model in _candidate_models(task).items():
        pipe = Pipeline([("pre", pre), ("model", model)])
        try:
            cv_scores = cross_val_score(pipe, X_train, y_train, cv=n_splits, scoring=scoring)
        except Exception:
            cv_scores = np.array([np.nan])

        pipe.fit(X_train, y_train)
        y_pred = pipe.predict(X_test)

        if task == "classification":
            proba = pipe.predict_proba(X_test) if hasattr(pipe[-1], "predict_proba") else None
            metrics = _classification_metrics(y_test, y_pred, proba)
        else:
            metrics = _regression_metrics(y_test, y_pred)

        metrics["cv_mean"] = round(float(np.nanmean(cv_scores)), 4)
        metrics["cv_std"] = round(float(np.nanstd(cv_scores)), 4)
        metrics["model"] = name
        results.append(metrics)
        fitted[name] = pipe

    results_df = pd.DataFrame(results).set_index("model")
    # Best by held-out primary metric (higher is better for r2/f1).
    best_name = results_df[primary_metric].idxmax()
    best_pipe = fitted[best_name]

    importances = _feature_importance(best_pipe, X_test, y_test, task)

    out = {
        "task": task,
        "target": target,
        "primary_metric": primary_metric,
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "n_features": int(X.shape[1]),
        "dropped_id_columns": drop_cols,
        "cv_folds": n_splits,
        "results": results_df.round(4),
        "best_model": best_name,
        "best_score": float(results_df.loc[best_name, primary_metric]),
        "feature_importance": importances,
    }

    if task == "classification":
        y_pred_best = best_pipe.predict(X_test)
        labels = sorted(pd.unique(y_test))
        cm = confusion_matrix(y_test, y_pred_best, labels=labels)
        out["confusion_matrix"] = pd.DataFrame(
            cm, index=[f"actual {l}" for l in labels], columns=[f"pred {l}" for l in labels]
        )
        out["class_labels"] = [str(l) for l in labels]

    return out


# ──────────────────────────────────────────────────────────────────────────────
# Feature importance
# ──────────────────────────────────────────────────────────────────────────────
def _feature_importance(pipe: Pipeline, X_test, y_test, task: str) -> pd.DataFrame:
    """
    Permutation importance on the held-out set — model-agnostic and measured on
    data the model has not seen, so it reflects genuine predictive value.
    """
    try:
        scoring = "f1_weighted" if task == "classification" else "r2"
        r = permutation_importance(
            pipe, X_test, y_test, n_repeats=10, random_state=RANDOM_STATE, scoring=scoring
        )
        imp = pd.DataFrame(
            {
                "feature": X_test.columns,
                "importance": r.importances_mean.round(4),
                "std": r.importances_std.round(4),
            }
        )
        return imp.sort_values("importance", ascending=False).reset_index(drop=True)
    except Exception:
        return pd.DataFrame()
