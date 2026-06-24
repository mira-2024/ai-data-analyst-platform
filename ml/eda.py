"""
Exploratory Data Analysis (EDA).

Pure, deterministic data-science computations on a pandas DataFrame. Every
function returns plain Python / pandas objects so the results can be rendered
in the UI, fed to a report, or unit-tested without any external service.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# Maximum unique values for a column to be treated as categorical when its
# dtype is numeric (e.g. an encoded category stored as 0/1/2).
LOW_CARDINALITY_THRESHOLD = 20


# ──────────────────────────────────────────────────────────────────────────────
# Column typing
# ──────────────────────────────────────────────────────────────────────────────
def numeric_columns(df: pd.DataFrame) -> list[str]:
    """Continuous / numeric columns."""
    return df.select_dtypes(include=np.number).columns.tolist()


def categorical_columns(df: pd.DataFrame) -> list[str]:
    """Object / category / boolean columns."""
    return df.select_dtypes(include=["object", "category", "bool"]).columns.tolist()


def datetime_columns(df: pd.DataFrame) -> list[str]:
    return df.select_dtypes(include=["datetime", "datetimetz"]).columns.tolist()


# ──────────────────────────────────────────────────────────────────────────────
# Dataset-level profile
# ──────────────────────────────────────────────────────────────────────────────
def profile_dataset(df: pd.DataFrame) -> dict:
    """High-level structural profile of the dataset."""
    n_rows, n_cols = df.shape
    total_cells = n_rows * n_cols
    missing_cells = int(df.isna().sum().sum())
    return {
        "n_rows": int(n_rows),
        "n_cols": int(n_cols),
        "memory_kb": round(df.memory_usage(deep=True).sum() / 1024, 2),
        "n_numeric": len(numeric_columns(df)),
        "n_categorical": len(categorical_columns(df)),
        "n_datetime": len(datetime_columns(df)),
        "missing_cells": missing_cells,
        "missing_pct": round(100 * missing_cells / total_cells, 2) if total_cells else 0.0,
        "duplicate_rows": int(df.duplicated().sum()),
        "duplicate_pct": round(100 * df.duplicated().sum() / n_rows, 2) if n_rows else 0.0,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Descriptive statistics (numeric)
# ──────────────────────────────────────────────────────────────────────────────
def descriptive_stats(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rich descriptive statistics for every numeric column, including the moments
    (skewness, excess kurtosis) and the coefficient of variation that a basic
    ``df.describe()`` omits.
    """
    num = df[numeric_columns(df)]
    if num.empty:
        return pd.DataFrame()

    rows = []
    for col in num.columns:
        s = num[col].dropna()
        if s.empty:
            continue
        mean = s.mean()
        std = s.std()
        rows.append(
            {
                "feature": col,
                "count": int(s.count()),
                "missing": int(df[col].isna().sum()),
                "mean": mean,
                "std": std,
                "min": s.min(),
                "q1": s.quantile(0.25),
                "median": s.median(),
                "q3": s.quantile(0.75),
                "max": s.max(),
                "iqr": s.quantile(0.75) - s.quantile(0.25),
                # Coefficient of variation — relative dispersion.
                "cv": (std / mean) if mean not in (0, np.nan) else np.nan,
                "skewness": s.skew(),
                "kurtosis": s.kurtosis(),  # excess kurtosis (normal = 0)
            }
        )
    return pd.DataFrame(rows).set_index("feature").round(4)


# ──────────────────────────────────────────────────────────────────────────────
# Categorical summary
# ──────────────────────────────────────────────────────────────────────────────
def _shannon_entropy(counts: pd.Series) -> float:
    """Shannon entropy (bits) of a categorical distribution."""
    p = counts / counts.sum()
    p = p[p > 0]
    return float(-(p * np.log2(p)).sum())


def categorical_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Cardinality, mode, mode frequency and entropy for categorical columns."""
    cats = categorical_columns(df)
    if not cats:
        return pd.DataFrame()

    rows = []
    for col in cats:
        s = df[col].dropna()
        if s.empty:
            continue
        vc = s.value_counts()
        rows.append(
            {
                "feature": col,
                "n_unique": int(s.nunique()),
                "missing": int(df[col].isna().sum()),
                "mode": vc.index[0],
                "mode_freq": int(vc.iloc[0]),
                "mode_pct": round(100 * vc.iloc[0] / len(s), 2),
                "entropy_bits": round(_shannon_entropy(vc), 3),
            }
        )
    return pd.DataFrame(rows).set_index("feature")


# ──────────────────────────────────────────────────────────────────────────────
# Missing-value analysis
# ──────────────────────────────────────────────────────────────────────────────
def missing_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """Per-column missing counts and percentages, sorted worst-first."""
    miss = df.isna().sum()
    out = pd.DataFrame(
        {
            "missing": miss.astype(int),
            "missing_pct": (100 * miss / len(df)).round(2),
            "dtype": df.dtypes.astype(str),
        }
    )
    return out[out["missing"] > 0].sort_values("missing", ascending=False)


# ──────────────────────────────────────────────────────────────────────────────
# Outlier detection
# ──────────────────────────────────────────────────────────────────────────────
def outlier_summary(df: pd.DataFrame, z_thresh: float = 3.0) -> pd.DataFrame:
    """
    Outlier counts per numeric column using two complementary methods:

    * IQR rule    — values outside [Q1 - 1.5·IQR, Q3 + 1.5·IQR]
    * Z-score     — |z| > ``z_thresh`` standard deviations from the mean
    """
    num = df[numeric_columns(df)]
    if num.empty:
        return pd.DataFrame()

    rows = []
    for col in num.columns:
        s = num[col].dropna()
        if s.empty:
            continue
        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        iqr = q3 - q1
        low, high = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        iqr_out = int(((s < low) | (s > high)).sum())

        std = s.std()
        if std and not np.isnan(std):
            z = (s - s.mean()) / std
            z_out = int((z.abs() > z_thresh).sum())
        else:
            z_out = 0

        rows.append(
            {
                "feature": col,
                "iqr_outliers": iqr_out,
                "iqr_outlier_pct": round(100 * iqr_out / len(s), 2),
                "zscore_outliers": z_out,
                "lower_bound": round(low, 4),
                "upper_bound": round(high, 4),
            }
        )
    return pd.DataFrame(rows).set_index("feature")


# ──────────────────────────────────────────────────────────────────────────────
# Correlation
# ──────────────────────────────────────────────────────────────────────────────
def correlation_matrix(df: pd.DataFrame, method: str = "pearson") -> pd.DataFrame:
    """Correlation matrix over numeric columns (method: pearson|spearman|kendall)."""
    num = df[numeric_columns(df)]
    if num.shape[1] < 2:
        return pd.DataFrame()
    return num.corr(method=method).round(4)


def top_correlations(df: pd.DataFrame, method: str = "pearson", n: int = 10) -> pd.DataFrame:
    """The ``n`` strongest pairwise correlations (by absolute value)."""
    corr = correlation_matrix(df, method=method)
    if corr.empty:
        return pd.DataFrame()

    pairs = []
    cols = corr.columns
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            pairs.append(
                {
                    "feature_a": cols[i],
                    "feature_b": cols[j],
                    "correlation": corr.iloc[i, j],
                    "abs_correlation": abs(corr.iloc[i, j]),
                }
            )
    if not pairs:
        return pd.DataFrame()
    out = pd.DataFrame(pairs).sort_values("abs_correlation", ascending=False)
    return out.drop(columns="abs_correlation").head(n).reset_index(drop=True)
