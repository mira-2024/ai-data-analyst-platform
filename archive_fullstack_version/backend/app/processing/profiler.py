"""
Dataset profiler.

Generates schema metadata, column statistics, and a row preview
from any pandas DataFrame. Output is used for:
  - UI: schema display, preview table, column sidebar
  - Agents: compact data summary passed to LLMs (never raw DataFrames)
  - DB: stored in dataset.schema_json, statistics_json, preview_json

All functions are pure (no side effects) and synchronous.
Run via asyncio.to_thread() from async service layer.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from app.schemas.dataset import ColumnSchema, ColumnStatistics, DatasetProfile


# Number of preview rows returned to UI
PREVIEW_ROW_COUNT = 10
# Max sample values shown per column in schema view
SAMPLE_VALUE_COUNT = 5


def profile(df: pd.DataFrame) -> DatasetProfile:
    """
    Generate a full profile of a DataFrame.

    Args:
        df: Loaded, sanitized pandas DataFrame

    Returns:
        DatasetProfile with columns, statistics, and preview rows
    """
    columns = [_profile_column(df, col) for col in df.columns]
    statistics = [_column_statistics(df, col) for col in df.columns]
    preview = _preview_rows(df)

    return DatasetProfile(
        row_count=len(df),
        column_count=len(df.columns),
        columns=columns,
        statistics=statistics,
        preview_rows=preview,
    )


def _profile_column(df: pd.DataFrame, col: str) -> ColumnSchema:
    """Extract schema metadata for a single column."""
    series = df[col]
    dtype = _friendly_dtype(series)
    null_count = int(series.isna().sum())
    unique_count = int(series.nunique(dropna=True))

    # Safe sample: non-null, unique-ish values for display
    sample_pool = series.dropna().unique()
    samples = [_safe_scalar(v) for v in sample_pool[:SAMPLE_VALUE_COUNT]]

    return ColumnSchema(
        name=col,
        dtype=dtype,
        nullable=null_count > 0,
        unique_count=unique_count,
        null_count=null_count,
        sample_values=samples,
    )


def _column_statistics(df: pd.DataFrame, col: str) -> ColumnStatistics:
    """Compute descriptive statistics for a single column."""
    series = df[col]
    total = len(series)
    null_count = int(series.isna().sum())
    null_pct = round((null_count / total * 100) if total > 0 else 0.0, 2)
    unique_count = int(series.nunique(dropna=True))

    stats = ColumnStatistics(
        name=col,
        dtype=_friendly_dtype(series),
        null_pct=null_pct,
        unique_count=unique_count,
    )

    numeric_series = pd.to_numeric(series, errors="coerce").dropna()
    if len(numeric_series) > 0:
        stats.min   = _safe_scalar(numeric_series.min())
        stats.max   = _safe_scalar(numeric_series.max())
        stats.mean  = round(float(numeric_series.mean()), 4)
        stats.std   = round(float(numeric_series.std()), 4) if len(numeric_series) > 1 else 0.0
    else:
        # Non-numeric: provide min/max as string for categorical columns
        non_null = series.dropna().astype(str)
        if len(non_null) > 0:
            stats.min = str(non_null.min())
            stats.max = str(non_null.max())

    return stats


def _preview_rows(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Return first N rows as a list of JSON-serializable dicts."""
    preview_df = df.head(PREVIEW_ROW_COUNT)
    records = []
    for _, row in preview_df.iterrows():
        record = {col: _safe_scalar(val) for col, val in row.items()}
        records.append(record)
    return records


def build_agent_summary(df: pd.DataFrame, profile: DatasetProfile) -> dict[str, Any]:
    """
    Build a COMPACT summary of the dataset for passing to LLM agents.

    This is what agents receive — never the raw DataFrame.
    Designed to stay under ~2000 tokens for efficient LLM context usage.

    Returns a dict with:
    - shape, columns with dtypes and null info
    - key statistics per column
    - 5 sample rows
    - data quality signals
    """
    column_summaries = []
    for col_schema, col_stats in zip(profile.columns, profile.statistics):
        summary: dict[str, Any] = {
            "name": col_schema.name,
            "dtype": col_schema.dtype,
            "null_pct": col_stats.null_pct,
            "unique_count": col_stats.unique_count,
        }
        if col_stats.mean is not None:
            summary["mean"] = col_stats.mean
            summary["std"] = col_stats.std
            summary["min"] = col_stats.min
            summary["max"] = col_stats.max
        else:
            summary["sample_values"] = col_schema.sample_values

        column_summaries.append(summary)

    # Overall quality signals
    total_cells = profile.row_count * profile.column_count
    null_cells = sum(
        int((s.null_pct / 100) * profile.row_count)
        for s in profile.statistics
    )
    null_rate = round(null_cells / total_cells * 100, 2) if total_cells > 0 else 0

    # Detect likely categorical columns
    likely_categorical = [
        col.name for col in profile.columns
        if col.unique_count is not None
        and col.unique_count < 30
        and col.dtype in ("object", "string", "category")
    ]

    # Detect likely datetime columns
    likely_datetime = [
        col.name for col in profile.columns
        if "date" in col.name.lower()
        or "time" in col.name.lower()
        or "timestamp" in col.name.lower()
    ]

    return {
        "shape": {"rows": profile.row_count, "columns": profile.column_count},
        "overall_null_rate_pct": null_rate,
        "likely_categorical_columns": likely_categorical,
        "likely_datetime_columns": likely_datetime,
        "columns": column_summaries,
        "sample_rows": profile.preview_rows[:5],
    }


def _friendly_dtype(series: pd.Series) -> str:
    """Convert pandas dtype to a human-readable string."""
    dtype = series.dtype
    if pd.api.types.is_integer_dtype(dtype):
        return "integer"
    if pd.api.types.is_float_dtype(dtype):
        return "float"
    if pd.api.types.is_bool_dtype(dtype):
        return "boolean"
    if pd.api.types.is_datetime64_any_dtype(dtype):
        return "datetime"
    if isinstance(dtype, pd.CategoricalDtype):
        return "category"
    return "string"


def _safe_scalar(value: Any) -> Any:
    """Convert a value to a JSON-safe Python scalar."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        v = float(value)
        return None if math.isnan(v) or math.isinf(v) else v
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, (np.ndarray,)):
        return value.tolist()
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value
