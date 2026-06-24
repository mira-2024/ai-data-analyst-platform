"""
Unit tests for CleanerAgent tool functions.

Tests cover all 6 tools:
    impute_missing, drop_duplicates, fix_dtype,
    handle_outliers, normalize_column, validate_schema

Run:
    cd backend && pytest tests/unit/test_cleaner_tools.py -v
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.agents.cleaner.tools import (
    DataFrameContainer,
    drop_duplicates,
    fix_dtype,
    handle_outliers,
    impute_missing,
    normalize_column,
    validate_schema,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def numeric_df() -> pd.DataFrame:
    """DataFrame with numeric columns, some nulls, and an outlier."""
    return pd.DataFrame(
        {
            "age": [25.0, 30.0, np.nan, 28.0, 1000.0, 32.0],  # 1000 is outlier
            "salary": [50_000.0, 60_000.0, 55_000.0, np.nan, 70_000.0, 65_000.0],
        }
    )


@pytest.fixture
def mixed_df() -> pd.DataFrame:
    """DataFrame with numeric, string, and boolean columns."""
    return pd.DataFrame(
        {
            "name": ["Alice", "Bob", None, "Dave"],
            "score": [90.0, 85.0, np.nan, 92.0],
            "active": ["true", "false", "true", "0"],
        }
    )


@pytest.fixture
def dup_df() -> pd.DataFrame:
    """DataFrame with duplicate rows."""
    return pd.DataFrame(
        {
            "id": [1, 2, 2, 3, 3],
            "val": ["a", "b", "b", "c", "c"],
        }
    )


def container(df: pd.DataFrame) -> DataFrameContainer:
    return DataFrameContainer(df)


# ── impute_missing ────────────────────────────────────────────────────────────

class TestImputeMissing:
    def test_mean_strategy(self, numeric_df):
        c = container(numeric_df)
        result = impute_missing(c, "salary", "mean")
        assert result["imputed_count"] == 1
        assert c.df["salary"].isna().sum() == 0
        assert result["strategy"] == "mean"

    def test_median_strategy(self, numeric_df):
        c = container(numeric_df)
        result = impute_missing(c, "age", "median")
        assert result["imputed_count"] == 1
        assert c.df["age"].isna().sum() == 0

    def test_mode_strategy(self, mixed_df):
        c = container(mixed_df)
        result = impute_missing(c, "name", "mode")
        assert result["imputed_count"] == 1
        assert c.df["name"].isna().sum() == 0

    def test_drop_strategy(self, numeric_df):
        c = container(numeric_df)
        rows_before = len(c.df)
        result = impute_missing(c, "age", "drop")
        assert len(c.df) < rows_before
        assert result["imputed_count"] >= 1

    def test_ffill_strategy(self, numeric_df):
        c = container(numeric_df)
        impute_missing(c, "age", "ffill")
        # ffill propagates previous value — nulls at start may remain
        # but this specific fixture has null at index 2, so forward fill works
        assert c.df["age"].iloc[2] == pytest.approx(30.0)

    def test_column_not_found(self, numeric_df):
        c = container(numeric_df)
        result = impute_missing(c, "nonexistent", "mean")
        assert "error" in result

    def test_mean_on_string_column_returns_error(self, mixed_df):
        c = container(mixed_df)
        result = impute_missing(c, "name", "mean")
        assert "error" in result

    def test_no_missing_returns_early(self, numeric_df):
        df = numeric_df.fillna(0)
        c = container(df)
        result = impute_missing(c, "age", "mean")
        assert result.get("imputed", result.get("imputed_count")) == 0

    def test_unknown_strategy_returns_error(self, numeric_df):
        c = container(numeric_df)
        result = impute_missing(c, "age", "unknown_strategy")
        assert "error" in result

    def test_action_recorded(self, numeric_df):
        c = container(numeric_df)
        impute_missing(c, "salary", "median")
        assert len(c.actions) == 1
        assert c.actions[0]["action_type"] == "impute_missing"

    def test_high_null_pct_warning(self):
        """Columns with >60% nulls should produce a warning."""
        df = pd.DataFrame({"x": [1.0, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan]})
        c = container(df)
        impute_missing(c, "x", "mean")
        assert len(c.warnings) > 0


# ── drop_duplicates ───────────────────────────────────────────────────────────

class TestDropDuplicates:
    def test_removes_duplicates(self, dup_df):
        c = container(dup_df)
        result = drop_duplicates(c)
        assert result["duplicates_removed"] == 2
        assert result["rows_after"] == 3

    def test_subset_duplicates(self, dup_df):
        c = container(dup_df)
        result = drop_duplicates(c, subset=["id"])
        assert result["duplicates_removed"] == 2

    def test_no_duplicates(self, numeric_df):
        c = container(numeric_df)
        result = drop_duplicates(c)
        assert result["duplicates_removed"] == 0

    def test_action_recorded_only_when_removed(self, dup_df):
        c = container(dup_df)
        drop_duplicates(c)
        assert len(c.actions) == 1

    def test_no_action_recorded_when_none_removed(self, numeric_df):
        c = container(numeric_df)
        drop_duplicates(c)
        assert len(c.actions) == 0


# ── fix_dtype ─────────────────────────────────────────────────────────────────

class TestFixDtype:
    def test_convert_to_numeric(self, mixed_df):
        c = container(mixed_df)
        result = fix_dtype(c, "score", "numeric")
        assert "error" not in result
        assert pd.api.types.is_numeric_dtype(c.df["score"])

    def test_convert_to_string(self, numeric_df):
        c = container(numeric_df)
        result = fix_dtype(c, "age", "string")
        assert "error" not in result
        assert c.df["age"].dtype == object

    def test_convert_to_boolean(self, mixed_df):
        c = container(mixed_df)
        result = fix_dtype(c, "active", "boolean")
        assert "error" not in result
        # "true" → True, "false" → False, "0" → False
        assert c.df["active"].iloc[0] is True or c.df["active"].iloc[0] == True

    def test_convert_to_category(self, mixed_df):
        c = container(mixed_df)
        result = fix_dtype(c, "name", "category")
        assert "error" not in result
        assert hasattr(c.df["name"], "cat")

    def test_column_not_found(self, numeric_df):
        c = container(numeric_df)
        result = fix_dtype(c, "missing_col", "numeric")
        assert "error" in result

    def test_unknown_dtype_returns_error(self, numeric_df):
        c = container(numeric_df)
        result = fix_dtype(c, "age", "hexadecimal")
        assert "error" in result

    def test_action_recorded(self, mixed_df):
        c = container(mixed_df)
        fix_dtype(c, "score", "string")
        assert len(c.actions) == 1
        assert c.actions[0]["column"] == "score"


# ── handle_outliers ───────────────────────────────────────────────────────────

class TestHandleOutliers:
    def test_iqr_cap(self, numeric_df):
        c = container(numeric_df)
        result = handle_outliers(c, "age", method="iqr", action="cap")
        assert result["outliers_found"] >= 1
        # 1000 should have been capped
        assert c.df["age"].max() < 1000

    def test_iqr_drop(self, numeric_df):
        c = container(numeric_df)
        rows_before = len(c.df)
        result = handle_outliers(c, "age", method="iqr", action="drop")
        assert len(c.df) < rows_before

    def test_iqr_flag(self, numeric_df):
        c = container(numeric_df)
        result = handle_outliers(c, "age", method="iqr", action="flag")
        assert "age_is_outlier" in c.df.columns
        assert result["outliers_found"] >= 1

    def test_zscore_cap(self, numeric_df):
        c = container(numeric_df)
        result = handle_outliers(c, "age", method="zscore", action="cap")
        assert "error" not in result

    def test_non_numeric_returns_error(self, mixed_df):
        c = container(mixed_df)
        result = handle_outliers(c, "name", method="iqr", action="cap")
        assert "error" in result

    def test_column_not_found(self, numeric_df):
        c = container(numeric_df)
        result = handle_outliers(c, "ghost", method="iqr", action="cap")
        assert "error" in result

    def test_no_outliers_returns_zero_count(self):
        df = pd.DataFrame({"x": [1.0, 2.0, 3.0, 4.0, 5.0]})
        c = container(df)
        result = handle_outliers(c, "x", method="iqr", action="cap")
        assert result["outliers_found"] == 0

    def test_unknown_method_returns_error(self, numeric_df):
        c = container(numeric_df)
        result = handle_outliers(c, "age", method="magic", action="cap")
        assert "error" in result

    def test_unknown_action_returns_error(self, numeric_df):
        c = container(numeric_df)
        result = handle_outliers(c, "age", method="iqr", action="ignore")
        assert "error" in result


# ── normalize_column ──────────────────────────────────────────────────────────

class TestNormalizeColumn:
    def test_minmax_range(self, numeric_df):
        c = container(numeric_df.dropna())
        normalize_column(c, "salary", "minmax")
        assert c.df["salary"].min() == pytest.approx(0.0)
        assert c.df["salary"].max() == pytest.approx(1.0)

    def test_zscore_mean_std(self, numeric_df):
        c = container(numeric_df.dropna())
        normalize_column(c, "salary", "zscore")
        assert c.df["salary"].mean() == pytest.approx(0.0, abs=1e-10)
        assert c.df["salary"].std() == pytest.approx(1.0, abs=0.1)

    def test_constant_column_minmax_returns_message(self):
        df = pd.DataFrame({"x": [5.0, 5.0, 5.0]})
        c = container(df)
        result = normalize_column(c, "x", "minmax")
        assert "message" in result

    def test_zero_variance_zscore_returns_message(self):
        df = pd.DataFrame({"x": [3.0, 3.0, 3.0]})
        c = container(df)
        result = normalize_column(c, "x", "zscore")
        assert "message" in result

    def test_non_numeric_returns_error(self, mixed_df):
        c = container(mixed_df)
        result = normalize_column(c, "name", "minmax")
        assert "error" in result

    def test_column_not_found(self, numeric_df):
        c = container(numeric_df)
        result = normalize_column(c, "missing", "zscore")
        assert "error" in result

    def test_unknown_method_returns_error(self, numeric_df):
        c = container(numeric_df.dropna())
        result = normalize_column(c, "salary", "log")
        assert "error" in result


# ── validate_schema ───────────────────────────────────────────────────────────

class TestValidateSchema:
    def test_basic_report(self, numeric_df):
        c = container(numeric_df)
        result = validate_schema(c)
        assert result["rows"] == len(numeric_df)
        assert result["columns"] == 2
        assert 0 <= result["completeness_pct"] <= 100
        assert 0.0 <= result["quality_score"] <= 1.0

    def test_detects_all_null_column(self):
        df = pd.DataFrame({"a": [1, 2, 3], "b": [np.nan, np.nan, np.nan]})
        c = container(df)
        result = validate_schema(c)
        assert "b" in result["all_null_columns"]

    def test_detects_constant_column(self):
        df = pd.DataFrame({"a": [1, 1, 1], "b": [2.0, 3.0, 4.0]})
        c = container(df)
        result = validate_schema(c)
        assert "a" in result["constant_columns"]

    def test_column_summary_correct_count(self, numeric_df):
        c = container(numeric_df)
        result = validate_schema(c)
        assert len(result["column_summary"]) == 2

    def test_perfect_dataset_completeness(self):
        df = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
        c = container(df)
        result = validate_schema(c)
        assert result["completeness_pct"] == 100.0

    def test_actions_taken_count(self, numeric_df):
        c = container(numeric_df)
        impute_missing(c, "age", "mean")
        impute_missing(c, "salary", "mean")
        result = validate_schema(c)
        assert result["actions_taken"] == 2
