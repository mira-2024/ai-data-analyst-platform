"""
Unit tests for the dataset profiler.

Tests cover:
    profile()           — full DataFrame profiling
    build_agent_summary() — compact LLM-ready summary

Run:
    cd backend && pytest tests/unit/test_profiler.py -v
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.processing.profiler import build_agent_summary, profile


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def simple_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "id": [1, 2, 3, 4, 5],
            "name": ["Alice", "Bob", "Carol", None, "Eve"],
            "age": [25.0, 30.0, np.nan, 28.0, 35.0],
            "salary": [50_000.0, 60_000.0, 55_000.0, 70_000.0, 65_000.0],
            "active": [True, False, True, True, False],
        }
    )


@pytest.fixture
def datetime_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "created_at": pd.date_range("2024-01-01", periods=5, freq="D"),
            "value": [10.0, 20.0, 30.0, 40.0, 50.0],
        }
    )


@pytest.fixture
def wide_df() -> pd.DataFrame:
    """Wide DataFrame (many columns) to stress-test token budget."""
    data = {f"col_{i}": np.random.randn(100) for i in range(30)}
    return pd.DataFrame(data)


# ── profile() ────────────────────────────────────────────────────────────────

class TestProfile:
    def test_returns_dataset_profile(self, simple_df):
        result = profile(simple_df)
        assert result.row_count == 5
        assert result.column_count == 5

    def test_column_count_matches(self, simple_df):
        result = profile(simple_df)
        assert len(result.columns) == simple_df.shape[1]

    def test_statistics_count_matches(self, simple_df):
        result = profile(simple_df)
        assert len(result.statistics) == simple_df.shape[1]

    def test_preview_rows_returned(self, simple_df):
        result = profile(simple_df)
        # Preview should be <= 10 rows (PREVIEW_ROW_COUNT constant)
        assert len(result.preview_rows) <= 10

    def test_null_counts_correct(self, simple_df):
        result = profile(simple_df)
        name_schema = next(c for c in result.columns if c.name == "name")
        age_schema = next(c for c in result.columns if c.name == "age")
        assert name_schema.null_count == 1
        assert age_schema.null_count == 1

    def test_nullable_flag(self, simple_df):
        result = profile(simple_df)
        name_schema = next(c for c in result.columns if c.name == "name")
        id_schema = next(c for c in result.columns if c.name == "id")
        assert name_schema.nullable is True
        assert id_schema.nullable is False

    def test_unique_count(self, simple_df):
        result = profile(simple_df)
        active_schema = next(c for c in result.columns if c.name == "active")
        # True and False → 2 unique values
        assert active_schema.unique_count == 2

    def test_numeric_statistics_populated(self, simple_df):
        result = profile(simple_df)
        salary_stats = next(s for s in result.statistics if s.name == "salary")
        assert salary_stats.mean is not None
        assert salary_stats.min is not None
        assert salary_stats.max is not None

    def test_non_numeric_statistics_have_no_mean(self, simple_df):
        result = profile(simple_df)
        name_stats = next(s for s in result.statistics if s.name == "name")
        # String columns should not have mean
        assert name_stats.mean is None

    def test_datetime_column_type_detected(self, datetime_df):
        result = profile(datetime_df)
        date_schema = next(c for c in result.columns if c.name == "created_at")
        # Should detect as datetime type
        assert "datetime" in date_schema.dtype.lower() or "date" in date_schema.dtype.lower()

    def test_empty_dataframe(self):
        df = pd.DataFrame()
        result = profile(df)
        assert result.row_count == 0
        assert result.column_count == 0

    def test_single_row_df(self):
        df = pd.DataFrame({"x": [42.0], "y": ["hello"]})
        result = profile(df)
        assert result.row_count == 1

    def test_all_null_column(self):
        df = pd.DataFrame({"good": [1.0, 2.0, 3.0], "bad": [np.nan, np.nan, np.nan]})
        result = profile(df)
        bad_stats = next(s for s in result.statistics if s.name == "bad")
        assert bad_stats.null_count == 3

    def test_sample_values_present(self, simple_df):
        result = profile(simple_df)
        id_schema = next(c for c in result.columns if c.name == "id")
        assert len(id_schema.sample_values) > 0


# ── build_agent_summary() ─────────────────────────────────────────────────────

class TestBuildAgentSummary:
    def test_returns_dict(self, simple_df):
        p = profile(simple_df)
        result = build_agent_summary(simple_df, p)
        assert isinstance(result, dict)

    def test_has_required_top_level_keys(self, simple_df):
        p = profile(simple_df)
        result = build_agent_summary(simple_df, p)
        # Should include shape / overview
        assert "rows" in result or "row_count" in result or "shape" in result

    def test_summary_has_column_info(self, simple_df):
        p = profile(simple_df)
        result = build_agent_summary(simple_df, p)
        # Must reference column names somehow
        summary_str = str(result)
        assert "salary" in summary_str or "age" in summary_str

    def test_summary_is_json_serialisable(self, simple_df):
        """Summary must be serialisable so agents can embed it in prompts."""
        import json
        p = profile(simple_df)
        result = build_agent_summary(simple_df, p)
        # Should not raise
        serialised = json.dumps(result, default=str)
        assert len(serialised) > 0

    def test_summary_token_budget(self, wide_df):
        """Wide DataFrames must still produce a compact summary (≤ ~2000 tokens)."""
        import json
        p = profile(wide_df)
        result = build_agent_summary(wide_df, p)
        # Rough token estimate: 4 chars ≈ 1 token
        char_count = len(json.dumps(result, default=str))
        # Allow some headroom beyond the 2000-token target
        assert char_count < 16_000, f"Summary too large: {char_count} chars"

    def test_no_nan_in_summary(self, simple_df):
        """NaN values in summary would break JSON serialization."""
        import json
        p = profile(simple_df)
        result = build_agent_summary(simple_df, p)
        raw = json.dumps(result, default=str)
        assert "NaN" not in raw
        assert "Infinity" not in raw

    def test_null_pct_included(self, simple_df):
        p = profile(simple_df)
        result = build_agent_summary(simple_df, p)
        # Null information should be available somewhere in the summary
        summary_str = str(result)
        # Columns with nulls should be mentioned somehow
        assert "null" in summary_str.lower() or "missing" in summary_str.lower() or "nan" in summary_str.lower()
