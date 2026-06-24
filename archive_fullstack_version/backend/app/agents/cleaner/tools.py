"""
CleanerAgent tool implementations.

Pure functions that operate on a pandas DataFrame held in a mutable container.
The container pattern allows tools to modify the DataFrame in-place across
multiple tool calls within a single agent run.

All functions are synchronous — called via asyncio.to_thread() by LLMClient.
Each function returns a structured result dict that is serialized and sent
back to Claude as the tool result.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd


class DataFrameContainer:
    """
    Mutable container holding the working DataFrame during a cleaning run.

    The CleanerAgent passes this to each tool function.
    After all tools run, the container holds the cleaned DataFrame.
    """

    def __init__(self, df: pd.DataFrame) -> None:
        self.df = df.copy()
        self.actions: list[dict[str, Any]] = []
        self.warnings: list[str] = []

    def record_action(
        self,
        action_type: str,
        column: str | None,
        description: str,
        rows_affected: int,
        before_value: Any = None,
        after_value: Any = None,
    ) -> None:
        self.actions.append({
            "action_type": action_type,
            "column": column,
            "description": description,
            "rows_affected": rows_affected,
            "before_value": _safe(before_value),
            "after_value": _safe(after_value),
        })


def impute_missing(container: DataFrameContainer, column: str, strategy: str) -> dict:
    """
    Impute missing values in a column.

    Args:
        column:   Column name
        strategy: "mean" | "median" | "mode" | "constant" | "ffill" | "bfill" | "drop"

    Returns: dict with imputed_count, strategy_used, before_null_count, after_null_count
    """
    df = container.df
    if column not in df.columns:
        return {"error": f"Column '{column}' not found"}

    series = df[column]
    null_count_before = int(series.isna().sum())

    if null_count_before == 0:
        return {"message": f"Column '{column}' has no missing values", "imputed": 0}

    null_pct = null_count_before / len(df) * 100

    if null_pct > 60:
        container.warnings.append(
            f"Column '{column}' has {null_pct:.1f}% missing values. "
            f"Imputation may not be reliable."
        )

    if strategy == "mean":
        if not pd.api.types.is_numeric_dtype(series):
            return {"error": f"Cannot apply mean imputation to non-numeric column '{column}'"}
        fill_value = series.mean()
        container.df[column] = series.fillna(fill_value)
    elif strategy == "median":
        if not pd.api.types.is_numeric_dtype(series):
            return {"error": f"Cannot apply median imputation to non-numeric column '{column}'"}
        fill_value = series.median()
        container.df[column] = series.fillna(fill_value)
    elif strategy == "mode":
        mode_vals = series.mode()
        if len(mode_vals) == 0:
            return {"error": f"No mode found for column '{column}'"}
        fill_value = mode_vals.iloc[0]
        container.df[column] = series.fillna(fill_value)
    elif strategy == "ffill":
        container.df[column] = series.ffill()
        fill_value = "forward fill"
    elif strategy == "bfill":
        container.df[column] = series.bfill()
        fill_value = "backward fill"
    elif strategy == "drop":
        container.df = container.df.dropna(subset=[column])
        fill_value = "dropped rows"
    else:
        return {"error": f"Unknown strategy '{strategy}'"}

    null_count_after = int(container.df[column].isna().sum())
    imputed = null_count_before - null_count_after

    container.record_action(
        action_type="impute_missing",
        column=column,
        description=f"Imputed {imputed} missing values in '{column}' using {strategy}",
        rows_affected=imputed,
        before_value=f"{null_count_before} nulls",
        after_value=f"{null_count_after} nulls remaining",
    )

    return {
        "column": column,
        "strategy": strategy,
        "imputed_count": imputed,
        "before_null_count": null_count_before,
        "after_null_count": null_count_after,
        "fill_value": _safe(fill_value),
    }


def drop_duplicates(container: DataFrameContainer, subset: list[str] | None = None) -> dict:
    """
    Remove duplicate rows from the DataFrame.

    Args:
        subset: Columns to consider for duplication check (None = all columns)
    """
    rows_before = len(container.df)
    container.df = container.df.drop_duplicates(subset=subset or None, keep="first")
    rows_after = len(container.df)
    removed = rows_before - rows_after

    if removed > 0:
        container.record_action(
            action_type="drop_duplicates",
            column=None,
            description=f"Removed {removed} duplicate rows"
            + (f" (checking columns: {subset})" if subset else ""),
            rows_affected=removed,
        )

    return {"duplicates_removed": removed, "rows_before": rows_before, "rows_after": rows_after}


def fix_dtype(container: DataFrameContainer, column: str, target_dtype: str) -> dict:
    """
    Convert a column to a specified data type.

    Args:
        column:      Column name
        target_dtype: "numeric" | "datetime" | "string" | "boolean" | "category"
    """
    df = container.df
    if column not in df.columns:
        return {"error": f"Column '{column}' not found"}

    original_dtype = str(df[column].dtype)
    failed_conversions = 0

    try:
        if target_dtype == "numeric":
            container.df[column] = pd.to_numeric(df[column], errors="coerce")
            failed_conversions = int(container.df[column].isna().sum()) - int(df[column].isna().sum())
        elif target_dtype == "datetime":
            container.df[column] = pd.to_datetime(df[column], errors="coerce", infer_datetime_format=True)
            failed_conversions = int(container.df[column].isna().sum()) - int(df[column].isna().sum())
        elif target_dtype == "string":
            container.df[column] = df[column].astype(str).str.strip()
        elif target_dtype == "boolean":
            mapping = {"true": True, "false": False, "1": True, "0": False, "yes": True, "no": False}
            container.df[column] = df[column].astype(str).str.lower().map(mapping)
        elif target_dtype == "category":
            container.df[column] = df[column].astype("category")
        else:
            return {"error": f"Unknown target dtype '{target_dtype}'"}
    except Exception as e:
        return {"error": f"Type conversion failed: {e}"}

    new_dtype = str(container.df[column].dtype)
    container.record_action(
        action_type="fix_dtype",
        column=column,
        description=f"Converted '{column}' from {original_dtype} to {target_dtype}",
        rows_affected=len(df),
        before_value=original_dtype,
        after_value=new_dtype,
    )

    return {
        "column": column,
        "original_dtype": original_dtype,
        "new_dtype": new_dtype,
        "failed_conversions": failed_conversions,
    }


def handle_outliers(
    container: DataFrameContainer,
    column: str,
    method: str,
    action: str,
) -> dict:
    """
    Detect and handle outliers in a numeric column.

    Args:
        column: Numeric column name
        method: "iqr" | "zscore"
        action: "cap" (winsorize) | "drop" | "flag" (add boolean column)
    """
    df = container.df
    if column not in df.columns:
        return {"error": f"Column '{column}' not found"}
    if not pd.api.types.is_numeric_dtype(df[column]):
        return {"error": f"Column '{column}' is not numeric"}

    series = df[column].dropna()

    if method == "iqr":
        q1, q3 = series.quantile(0.25), series.quantile(0.75)
        iqr = q3 - q1
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    elif method == "zscore":
        mean, std = series.mean(), series.std()
        if std == 0:
            return {"message": f"Column '{column}' has zero variance — no outliers detected"}
        lower = mean - 3 * std
        upper = mean + 3 * std
    else:
        return {"error": f"Unknown method '{method}'"}

    outlier_mask = (container.df[column] < lower) | (container.df[column] > upper)
    outlier_count = int(outlier_mask.sum())

    if outlier_count == 0:
        return {"column": column, "outliers_found": 0, "action": "none"}

    if action == "cap":
        container.df[column] = container.df[column].clip(lower=lower, upper=upper)
        action_desc = f"Capped {outlier_count} outliers to [{lower:.2f}, {upper:.2f}]"
    elif action == "drop":
        container.df = container.df[~outlier_mask]
        action_desc = f"Dropped {outlier_count} outlier rows"
    elif action == "flag":
        flag_col = f"{column}_is_outlier"
        container.df[flag_col] = outlier_mask
        action_desc = f"Flagged {outlier_count} outliers in new column '{flag_col}'"
    else:
        return {"error": f"Unknown action '{action}'"}

    container.record_action(
        action_type="handle_outliers",
        column=column,
        description=action_desc,
        rows_affected=outlier_count,
        before_value=f"bounds: [{lower:.2f}, {upper:.2f}]",
    )

    return {
        "column": column,
        "method": method,
        "action": action,
        "outliers_found": outlier_count,
        "lower_bound": _safe(lower),
        "upper_bound": _safe(upper),
        "action_description": action_desc,
    }


def normalize_column(container: DataFrameContainer, column: str, method: str) -> dict:
    """
    Normalize a numeric column.

    Args:
        column: Numeric column name
        method: "minmax" (scale to [0,1]) | "zscore" (standardize to mean=0, std=1)
    """
    df = container.df
    if column not in df.columns:
        return {"error": f"Column '{column}' not found"}
    if not pd.api.types.is_numeric_dtype(df[column]):
        return {"error": f"Column '{column}' is not numeric"}

    series = df[column]

    if method == "minmax":
        col_min, col_max = series.min(), series.max()
        if col_max == col_min:
            return {"message": f"Column '{column}' has constant value — cannot normalize"}
        container.df[column] = (series - col_min) / (col_max - col_min)
        desc = f"Min-max normalized '{column}' to [0, 1]"
    elif method == "zscore":
        mean, std = series.mean(), series.std()
        if std == 0:
            return {"message": f"Column '{column}' has zero variance — cannot standardize"}
        container.df[column] = (series - mean) / std
        desc = f"Z-score standardized '{column}' (mean=0, std=1)"
    else:
        return {"error": f"Unknown method '{method}'"}

    container.record_action(
        action_type="normalize",
        column=column,
        description=desc,
        rows_affected=len(df),
    )

    return {"column": column, "method": method, "description": desc}


def validate_schema(container: DataFrameContainer) -> dict:
    """
    Validate the final cleaned DataFrame and produce a quality report.
    Always call this last.
    """
    df = container.df
    total_cells = df.shape[0] * df.shape[1]
    null_cells = int(df.isna().sum().sum())
    completeness = 1.0 - (null_cells / total_cells) if total_cells > 0 else 0.0

    # Detect columns that are entirely null
    all_null_cols = [col for col in df.columns if df[col].isna().all()]

    # Detect constant columns
    constant_cols = [col for col in df.columns if df[col].nunique() <= 1]

    # Compute quality score
    quality_score = round(completeness * (1 - len(all_null_cols) / max(len(df.columns), 1)), 3)

    column_summary = []
    for col in df.columns:
        null_pct = round(df[col].isna().mean() * 100, 1)
        column_summary.append({
            "name": col,
            "dtype": str(df[col].dtype),
            "null_pct": null_pct,
            "unique_count": int(df[col].nunique()),
        })

    return {
        "rows": len(df),
        "columns": len(df.columns),
        "completeness_pct": round(completeness * 100, 2),
        "quality_score": quality_score,
        "all_null_columns": all_null_cols,
        "constant_columns": constant_cols,
        "column_summary": column_summary,
        "actions_taken": len(container.actions),
        "warnings": container.warnings,
    }


def _safe(value: Any) -> Any:
    """Make a value JSON-serializable."""
    if value is None:
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    return value
