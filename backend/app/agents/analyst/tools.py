"""
AnalystAgent tool implementations.

Pure statistical analysis functions that operate on a cleaned DataFrame.
All functions are synchronous and return JSON-serializable dicts.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd


def statistical_summary(df: pd.DataFrame, columns: list[str] | None = None) -> dict:
    """
    Compute comprehensive descriptive statistics for numeric columns.

    Args:
        columns: Specific columns to summarize (None = all numeric)
    """
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if columns:
        numeric_cols = [c for c in columns if c in df.columns and pd.api.types.is_numeric_dtype(df[c])]

    if not numeric_cols:
        return {"error": "No numeric columns found for statistical summary"}

    result = {}
    for col in numeric_cols:
        series = df[col].dropna()
        if len(series) == 0:
            continue
        result[col] = {
            "count": int(series.count()),
            "mean": _safe(series.mean()),
            "median": _safe(series.median()),
            "std": _safe(series.std()),
            "min": _safe(series.min()),
            "max": _safe(series.max()),
            "q25": _safe(series.quantile(0.25)),
            "q75": _safe(series.quantile(0.75)),
            "skewness": _safe(series.skew()),
            "kurtosis": _safe(series.kurtosis()),
            "null_pct": round(df[col].isna().mean() * 100, 2),
        }

    return {"statistics": result, "columns_analyzed": len(result)}


def correlation_analysis(df: pd.DataFrame, threshold: float = 0.3) -> dict:
    """
    Compute pairwise correlations between all numeric columns.

    Args:
        threshold: Minimum absolute correlation to include in results (0.0-1.0)
    """
    numeric_df = df.select_dtypes(include="number")
    if numeric_df.shape[1] < 2:
        return {"error": "Need at least 2 numeric columns for correlation analysis"}

    corr_matrix = numeric_df.corr(method="pearson")
    cols = corr_matrix.columns.tolist()

    significant = []
    for i, col_a in enumerate(cols):
        for col_b in cols[i + 1:]:
            corr_val = corr_matrix.loc[col_a, col_b]
            if math.isnan(corr_val):
                continue
            if abs(corr_val) >= threshold:
                strength = (
                    "very strong" if abs(corr_val) >= 0.9 else
                    "strong" if abs(corr_val) >= 0.7 else
                    "moderate" if abs(corr_val) >= 0.5 else
                    "weak"
                )
                direction = "positive" if corr_val > 0 else "negative"
                significant.append({
                    "column_a": col_a,
                    "column_b": col_b,
                    "correlation": round(corr_val, 4),
                    "strength": strength,
                    "direction": direction,
                    "interpretation": (
                        f"'{col_a}' and '{col_b}' have a {strength} {direction} "
                        f"correlation (r={corr_val:.3f})"
                    ),
                })

    # Sort by absolute correlation descending
    significant.sort(key=lambda x: abs(x["correlation"]), reverse=True)

    # Also return full matrix as a compact dict for heatmap generation
    matrix = {}
    for col in cols:
        matrix[col] = {
            c: round(corr_matrix.loc[col, c], 3)
            for c in cols
            if not math.isnan(corr_matrix.loc[col, c])
        }

    return {
        "significant_pairs": significant,
        "total_pairs_analyzed": len(cols) * (len(cols) - 1) // 2,
        "significant_count": len(significant),
        "correlation_matrix": matrix,
    }


def frequency_distribution(df: pd.DataFrame, column: str, top_n: int = 20) -> dict:
    """
    Analyze the value distribution of a categorical column.

    Args:
        column: Column name (works best for categorical/string/low-cardinality)
        top_n:  Number of top values to return
    """
    if column not in df.columns:
        return {"error": f"Column '{column}' not found"}

    series = df[column].dropna()
    total = len(series)
    value_counts = series.value_counts()

    top = []
    for val, count in value_counts.head(top_n).items():
        top.append({
            "value": str(val),
            "count": int(count),
            "pct": round(count / total * 100, 2),
        })

    return {
        "column": column,
        "unique_values": int(series.nunique()),
        "total_non_null": total,
        "null_count": int(df[column].isna().sum()),
        "top_values": top,
        "is_high_cardinality": series.nunique() > 50,
        "most_common": str(value_counts.index[0]) if len(value_counts) > 0 else None,
        "least_common": str(value_counts.index[-1]) if len(value_counts) > 0 else None,
    }


def detect_anomalies(df: pd.DataFrame, column: str) -> dict:
    """
    Detect anomalies in a numeric column using IQR and Z-score methods.

    Args:
        column: Numeric column name
    """
    if column not in df.columns:
        return {"error": f"Column '{column}' not found"}
    if not pd.api.types.is_numeric_dtype(df[column]):
        return {"error": f"Column '{column}' is not numeric"}

    series = df[column].dropna()
    mean, std = series.mean(), series.std()

    q1, q3 = series.quantile(0.25), series.quantile(0.75)
    iqr = q3 - q1
    iqr_lower, iqr_upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr

    iqr_outliers = series[(series < iqr_lower) | (series > iqr_upper)]
    zscore_outliers = series[(series - mean).abs() > 3 * std] if std > 0 else pd.Series([], dtype=float)

    examples = iqr_outliers.head(5).tolist()

    return {
        "column": column,
        "iqr_outliers_count": int(len(iqr_outliers)),
        "zscore_outliers_count": int(len(zscore_outliers)),
        "iqr_bounds": {"lower": _safe(iqr_lower), "upper": _safe(iqr_upper)},
        "zscore_bounds": {
            "lower": _safe(mean - 3 * std),
            "upper": _safe(mean + 3 * std),
        },
        "anomaly_pct": round(len(iqr_outliers) / len(series) * 100, 2),
        "example_anomalies": [_safe(v) for v in examples],
        "severity": (
            "high" if len(iqr_outliers) / max(len(series), 1) > 0.1 else
            "medium" if len(iqr_outliers) > 0 else "none"
        ),
    }


def trend_analysis(df: pd.DataFrame, date_column: str, value_column: str) -> dict:
    """
    Analyze trend in a numeric column over a datetime axis.

    Args:
        date_column:  Datetime column name
        value_column: Numeric value column
    """
    if date_column not in df.columns:
        return {"error": f"Date column '{date_column}' not found"}
    if value_column not in df.columns:
        return {"error": f"Value column '{value_column}' not found"}

    temp = df[[date_column, value_column]].dropna()
    try:
        temp[date_column] = pd.to_datetime(temp[date_column])
    except Exception:
        return {"error": f"Could not parse '{date_column}' as datetime"}

    temp = temp.sort_values(date_column)
    monthly = temp.resample("ME", on=date_column)[value_column].mean()

    if len(monthly) < 2:
        return {"error": "Not enough data points for trend analysis"}

    # Linear trend
    x = np.arange(len(monthly))
    y = monthly.values
    valid = ~np.isnan(y)
    slope = float(np.polyfit(x[valid], y[valid], 1)[0]) if valid.sum() > 1 else 0

    trend_direction = "upward" if slope > 0 else "downward" if slope < 0 else "flat"
    pct_change = float((y[valid][-1] - y[valid][0]) / abs(y[valid][0]) * 100) if y[valid][0] != 0 else 0

    data_points = [
        {"period": str(idx.date()), "value": _safe(val)}
        for idx, val in monthly.items()
    ]

    return {
        "date_column": date_column,
        "value_column": value_column,
        "trend_direction": trend_direction,
        "slope": round(slope, 4),
        "pct_change_overall": round(pct_change, 2),
        "start_value": _safe(float(y[valid][0])),
        "end_value": _safe(float(y[valid][-1])),
        "period_count": len(monthly),
        "monthly_averages": data_points,
    }


def group_comparison(df: pd.DataFrame, group_column: str, value_column: str) -> dict:
    """
    Compare a numeric value across groups defined by a categorical column.

    Args:
        group_column:  Categorical column to group by
        value_column:  Numeric column to compare
    """
    if group_column not in df.columns or value_column not in df.columns:
        return {"error": "Column not found"}
    if not pd.api.types.is_numeric_dtype(df[value_column]):
        return {"error": f"'{value_column}' must be numeric"}

    grouped = df.groupby(group_column)[value_column].agg(["mean", "median", "count", "std"])
    overall_mean = df[value_column].mean()

    groups = []
    for name, row in grouped.iterrows():
        groups.append({
            "group": str(name),
            "count": int(row["count"]),
            "mean": _safe(row["mean"]),
            "median": _safe(row["median"]),
            "std": _safe(row["std"]),
            "vs_overall_pct": round(
                (row["mean"] - overall_mean) / overall_mean * 100, 2
            ) if overall_mean != 0 else 0,
        })

    groups.sort(key=lambda x: x["mean"] or 0, reverse=True)

    return {
        "group_column": group_column,
        "value_column": value_column,
        "overall_mean": _safe(overall_mean),
        "group_count": len(groups),
        "groups": groups,
        "highest_group": groups[0] if groups else None,
        "lowest_group": groups[-1] if groups else None,
    }


def _safe(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        v = float(value)
        return None if (math.isnan(v) or math.isinf(v)) else v
    return value
