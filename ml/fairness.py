"""
ml/fairness.py — Algorithmic fairness & bias analysis.

Computes group-level performance metrics to surface potential bias in model
predictions across sensitive demographic attributes.

Criteria evaluated
------------------
* Class imbalance        — is the target distribution skewed?
* Demographic parity     — do groups receive positive predictions at similar rates?
* Equal opportunity      — do groups have similar true positive rates (TPR)?
* Predictive parity      — do groups have similar precision?
* Disparate impact       — is the minimum group selection rate ≥ 80% of the overall
                           rate? (US EEOC 4/5 rule)

No external fairness library required — implemented with sklearn + pandas.

Reference: Barocas, Hardt & Narayanan (2019) — "Fairness and Machine Learning:
Limitations and Opportunities." MIT Press.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)


# ──────────────────────────────────────────────────────────────────────────────
# Sensitive attribute detection
# ──────────────────────────────────────────────────────────────────────────────

SENSITIVE_KEYWORDS = (
    "sex", "gender", "race", "ethnicity", "age_group", "age_cat",
    "nationality", "religion", "marital", "education_level", "income_group",
)


def detect_sensitive_columns(df: pd.DataFrame) -> list[str]:
    """
    Heuristic: return columns whose name contains a sensitive keyword and
    that have ≤ 10 unique values (i.e. they encode a group, not a continuous var).
    """
    return [
        col for col in df.columns
        if any(kw in col.lower() for kw in SENSITIVE_KEYWORDS)
        and df[col].nunique() <= 10
    ]


# ──────────────────────────────────────────────────────────────────────────────
# Class imbalance
# ──────────────────────────────────────────────────────────────────────────────

def class_imbalance_report(y: pd.Series) -> dict:
    """
    Analyse target class distribution and flag imbalance.

    Returns a structured dict with counts, imbalance ratio, and a plain-
    language note. An imbalance ratio ≥ 3.0 is considered severe.
    """
    vc = y.value_counts()
    if len(vc) < 2:
        return {
            "balanced": True,
            "note": "Only one class present — cannot assess imbalance.",
            "class_counts": vc.to_dict(),
        }

    majority = int(vc.iloc[0])
    minority = int(vc.iloc[-1])
    ratio = round(majority / minority, 2) if minority > 0 else float("inf")

    if ratio < 1.5:
        note = "Dataset is well balanced."
        severity = "balanced"
    elif ratio < 3.0:
        note = (
            f"Moderate imbalance (ratio {ratio:.1f}:1). "
            "Models may be slightly biased toward the majority class."
        )
        severity = "moderate"
    else:
        note = (
            f"Severe imbalance (ratio {ratio:.1f}:1). "
            "High risk of biased predictions toward the majority class. "
            "Class-weighted training (class_weight='balanced') was applied automatically."
        )
        severity = "severe"

    return {
        "class_counts": vc.to_dict(),
        "majority_class": str(vc.index[0]),
        "minority_class": str(vc.index[-1]),
        "imbalance_ratio": ratio,
        "balanced": ratio < 1.5,
        "severe_imbalance": ratio >= 3.0,
        "severity": severity,
        "note": note,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Per-group metrics
# ──────────────────────────────────────────────────────────────────────────────

def group_metrics(
    y_true: pd.Series,
    y_pred: np.ndarray,
    sensitive_col: pd.Series,
    positive_label=1,
) -> pd.DataFrame:
    """
    Compute per-group classification metrics for binary predictions.

    Parameters
    ----------
    y_true         : ground-truth labels
    y_pred         : model predictions (class labels, not probabilities)
    sensitive_col  : Series of group membership (same index as y_true)
    positive_label : which class is the "positive" / "favourable" outcome

    Returns
    -------
    DataFrame indexed by group value with columns:
        n, selection_rate, accuracy, tpr, fpr, precision, f1, disparate_impact
    """
    overall_selection = (np.asarray(y_pred) == positive_label).mean()
    rows = []

    for g in sorted(sensitive_col.unique(), key=str):
        mask = (sensitive_col == g).values
        if mask.sum() < 5:
            continue

        yt = np.asarray(y_true)[mask]
        yp = np.asarray(y_pred)[mask]
        n = int(mask.sum())

        selection_rate = float((yp == positive_label).mean())
        acc = float(accuracy_score(yt, yp))

        tpr = fpr = prec = f1 = None
        unique_classes = np.unique(yt)
        if len(unique_classes) == 2:
            cm = confusion_matrix(yt, yp, labels=[
                x for x in [0, positive_label] if x in unique_classes
            ])
            if cm.shape == (2, 2):
                tn, fp, fn, tp = cm.ravel()
                tpr = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
                fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0
                prec = float(precision_score(yt, yp, pos_label=positive_label, zero_division=0))
                f1 = float(f1_score(yt, yp, pos_label=positive_label, zero_division=0))

        di = (selection_rate / overall_selection) if overall_selection > 0 else None

        rows.append({
            "group": str(g),
            "n": n,
            "selection_rate": round(selection_rate, 4),
            "accuracy": round(acc, 4),
            "tpr_recall": round(tpr, 4) if tpr is not None else None,
            "fpr": round(fpr, 4) if fpr is not None else None,
            "precision": round(prec, 4) if prec is not None else None,
            "f1": round(f1, 4) if f1 is not None else None,
            "disparate_impact": round(di, 4) if di is not None else None,
        })

    return pd.DataFrame(rows).set_index("group") if rows else pd.DataFrame()


# ──────────────────────────────────────────────────────────────────────────────
# Fairness verdicts
# ──────────────────────────────────────────────────────────────────────────────

def fairness_verdict(group_df: pd.DataFrame) -> dict[str, dict]:
    """
    Assess standard fairness criteria given the per-group metrics DataFrame.

    Returns a dict mapping criterion name → {metric, value, pass, threshold, note}.
    """
    verdicts: dict[str, dict] = {}

    # 1) Demographic parity — selection rate gap ≤ 10%
    if "selection_rate" in group_df.columns:
        sr = group_df["selection_rate"].dropna()
        if len(sr) >= 2:
            gap = float(sr.max() - sr.min())
            verdicts["demographic_parity"] = {
                "metric": "Selection rate gap",
                "value": round(gap, 4),
                "pass": gap <= 0.10,
                "threshold": 0.10,
                "note": (
                    f"Max selection rate gap: {gap:.3f}. "
                    + ("✓ Within 10% tolerance." if gap <= 0.10
                       else "✗ Exceeds 10% — possible demographic disparity.")
                ),
            }

    # 2) Disparate impact ≥ 0.8 (EEOC 4/5 rule)
    if "disparate_impact" in group_df.columns:
        di_vals = group_df["disparate_impact"].dropna()
        if len(di_vals) >= 1:
            min_di = float(di_vals.min())
            verdicts["disparate_impact"] = {
                "metric": "Disparate impact (minimum)",
                "value": round(min_di, 4),
                "pass": min_di >= 0.80,
                "threshold": 0.80,
                "note": (
                    f"Minimum disparate impact ratio: {min_di:.3f}. "
                    + ("✓ Meets the EEOC 4/5 (80%) rule." if min_di >= 0.80
                       else "✗ Below 0.8 threshold — potential adverse impact.")
                ),
            }

    # 3) Equal opportunity — TPR gap ≤ 10%
    if "tpr_recall" in group_df.columns:
        tpr_vals = group_df["tpr_recall"].dropna()
        if len(tpr_vals) >= 2:
            gap = float(tpr_vals.max() - tpr_vals.min())
            verdicts["equal_opportunity"] = {
                "metric": "True positive rate gap",
                "value": round(gap, 4),
                "pass": gap <= 0.10,
                "threshold": 0.10,
                "note": (
                    f"TPR gap across groups: {gap:.3f}. "
                    + ("✓ Within 10% tolerance." if gap <= 0.10
                       else "✗ Unequal recall — some groups are under-served.")
                ),
            }

    # 4) Predictive parity — precision gap ≤ 10%
    if "precision" in group_df.columns:
        prec_vals = group_df["precision"].dropna()
        if len(prec_vals) >= 2:
            gap = float(prec_vals.max() - prec_vals.min())
            verdicts["predictive_parity"] = {
                "metric": "Precision gap",
                "value": round(gap, 4),
                "pass": gap <= 0.10,
                "threshold": 0.10,
                "note": (
                    f"Precision gap across groups: {gap:.3f}. "
                    + ("✓ Within 10% tolerance." if gap <= 0.10
                       else "✗ Unequal precision — some groups have more false positives.")
                ),
            }

    return verdicts


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

def run_fairness_analysis(
    df: pd.DataFrame,
    y_true: pd.Series,
    y_pred: np.ndarray,
    sensitive_col_name: str | None = None,
    positive_label=1,
) -> dict:
    """
    Full fairness pipeline.

    Parameters
    ----------
    df                  : the original feature DataFrame (same rows as y_true)
    y_true              : ground-truth target labels
    y_pred              : model predicted labels
    sensitive_col_name  : column in df to use as sensitive attribute.
                          Auto-detected if None.
    positive_label      : the "favourable" outcome label

    Returns
    -------
    {
        imbalance       : dict from class_imbalance_report
        sensitive_column: str | None
        group_metrics   : pd.DataFrame | None
        verdicts        : dict
        has_sensitive   : bool
        overall_pass    : bool   (True if all criteria pass)
        n_criteria_pass : int
        n_criteria_total: int
    }
    """
    imbalance = class_imbalance_report(y_true)

    if sensitive_col_name is None:
        candidates = detect_sensitive_columns(df)
        sensitive_col_name = candidates[0] if candidates else None

    result: dict = {
        "imbalance": imbalance,
        "sensitive_column": sensitive_col_name,
        "group_metrics": None,
        "verdicts": {},
        "has_sensitive": sensitive_col_name is not None,
        "overall_pass": True,
        "n_criteria_pass": 0,
        "n_criteria_total": 0,
    }

    if sensitive_col_name and sensitive_col_name in df.columns:
        sensitive_series = df[sensitive_col_name].reset_index(drop=True)
        y_true_r = y_true.reset_index(drop=True)
        y_pred_arr = np.asarray(y_pred)

        min_len = min(len(sensitive_series), len(y_true_r), len(y_pred_arr))
        sensitive_series = sensitive_series.iloc[:min_len]
        y_true_r = y_true_r.iloc[:min_len]
        y_pred_arr = y_pred_arr[:min_len]

        gm = group_metrics(y_true_r, y_pred_arr, sensitive_series, positive_label)
        verdicts = fairness_verdict(gm)

        n_pass = sum(1 for v in verdicts.values() if v.get("pass", False))
        n_total = len(verdicts)

        result.update({
            "group_metrics": gm,
            "verdicts": verdicts,
            "overall_pass": n_pass == n_total,
            "n_criteria_pass": n_pass,
            "n_criteria_total": n_total,
        })

    return result
