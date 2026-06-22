"""
Unit tests for AnalystAgent tool functions.

Tests cover all 6 tools:
    statistical_summary, correlation_analysis, frequency_distribution,
    detect_anomalies, trend_analysis, group_comparison

Run:
    cd backend && pytest tests/unit/test_analyst_tools.py -v
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.agents.analyst.tools import (
    correlation_analysis,
    detect_anomalies,
    frequency_distribution,
    group_comparison,
    statistical_summary,
    trend_analysis,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def numeric_df() -> pd.DataFrame:
    np.random.seed(42)
    return pd.DataFrame(
        {
            "revenue": np.random.normal(100_000, 20_000, 50),
            "units": np.random.randint(1, 200, 50).astype(float),
            "margin": np.random.uniform(0.1, 0.5, 50),
        }
    )


@pytest.fixture
def categorical_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "region": ["North", "South", "North", "East", "South", "North", "East", "South"],
            "sales": [100.0, 80.0, 110.0, 90.0, 70.0, 120.0, 95.0, 85.0],
            "category": ["A", "B", "A", "A", "B", "C", "A", "B"],
        }
    )


@pytest.fixture
def time_series_df() -> pd.DataFrame:
    dates = pd.date_range("2023-01-01", periods=24, freq="ME")
    values = np.linspace(100, 200, 24) + np.random.normal(0, 5, 24)
    return pd.DataFrame({"date": dates, "revenue": values})


@pytest.fixture
def outlier_df() -> pd.DataFrame:
    vals = [10.0, 12.0, 11.0, 10.5, 13.0, 9.5, 1000.0]  # 1000 is extreme outlier
    return pd.DataFrame({"x": vals})


# ── statistical_summary ───────────────────────────────────────────────────────

class TestStatisticalSummary:
    def test_returns_all_numeric_columns(self, numeric_df):
        result = statistical_summary(numeric_df)
        assert "error" not in result
        stats = result["statistics"]
        assert "revenue" in stats
        assert "units" in stats
        assert "margin" in stats

    def test_correct_keys_per_column(self, numeric_df):
        result = statistical_summary(numeric_df)
        col = result["statistics"]["revenue"]
        for key in ["count", "mean", "median", "std", "min", "max", "q25", "q75"]:
            assert key in col

    def test_column_subset(self, numeric_df):
        result = statistical_summary(numeric_df, columns=["revenue"])
        assert result["columns_analyzed"] == 1
        assert "units" not in result["statistics"]

    def test_no_numeric_columns(self):
        df = pd.DataFrame({"name": ["a", "b", "c"]})
        result = statistical_summary(df)
        assert "error" in result

    def test_nonexistent_column_ignored(self, numeric_df):
        result = statistical_summary(numeric_df, columns=["revenue", "ghost"])
        assert "ghost" not in result["statistics"]

    def test_count_correct(self, numeric_df):
        result = statistical_summary(numeric_df)
        assert result["statistics"]["revenue"]["count"] == 50

    def test_no_nan_in_output(self, numeric_df):
        """NaN and Inf values should be replaced with None."""
        result = statistical_summary(numeric_df)
        for col_stats in result["statistics"].values():
            for v in col_stats.values():
                if isinstance(v, float):
                    assert not (v != v)  # NaN check: NaN != NaN


# ── correlation_analysis ──────────────────────────────────────────────────────

class TestCorrelationAnalysis:
    def test_returns_significant_pairs(self, numeric_df):
        result = correlation_analysis(numeric_df, threshold=0.0)
        assert "significant_pairs" in result
        assert "correlation_matrix" in result

    def test_threshold_filters_weak(self, numeric_df):
        all_pairs = correlation_analysis(numeric_df, threshold=0.0)["significant_count"]
        filtered = correlation_analysis(numeric_df, threshold=0.9)["significant_count"]
        assert filtered <= all_pairs

    def test_perfect_correlation(self):
        df = pd.DataFrame({"a": [1.0, 2.0, 3.0, 4.0], "b": [2.0, 4.0, 6.0, 8.0]})
        result = correlation_analysis(df, threshold=0.0)
        pair = result["significant_pairs"][0]
        assert abs(pair["correlation"] - 1.0) < 0.001
        assert pair["strength"] == "very strong"
        assert pair["direction"] == "positive"

    def test_negative_correlation(self):
        df = pd.DataFrame({"a": [1.0, 2.0, 3.0, 4.0], "b": [4.0, 3.0, 2.0, 1.0]})
        result = correlation_analysis(df, threshold=0.0)
        pair = result["significant_pairs"][0]
        assert pair["direction"] == "negative"

    def test_single_column_returns_error(self):
        df = pd.DataFrame({"a": [1.0, 2.0, 3.0]})
        result = correlation_analysis(df)
        assert "error" in result


# ── frequency_distribution ───────────────────────────────────────────────────

class TestFrequencyDistribution:
    def test_basic_distribution(self, categorical_df):
        result = frequency_distribution(categorical_df, "region")
        assert result["column"] == "region"
        assert result["unique_values"] == 3
        assert len(result["top_values"]) <= 20

    def test_top_n_limit(self, categorical_df):
        result = frequency_distribution(categorical_df, "category", top_n=2)
        assert len(result["top_values"]) <= 2

    def test_column_not_found(self, categorical_df):
        result = frequency_distribution(categorical_df, "missing")
        assert "error" in result

    def test_most_common_correct(self, categorical_df):
        result = frequency_distribution(categorical_df, "region")
        # "North" appears 3 times, most
        assert result["most_common"] == "North"

    def test_pcts_sum_to_100(self, categorical_df):
        result = frequency_distribution(categorical_df, "region", top_n=100)
        total_pct = sum(v["pct"] for v in result["top_values"])
        assert abs(total_pct - 100.0) < 0.1

    def test_high_cardinality_flag(self):
        df = pd.DataFrame({"col": list(range(60))})
        result = frequency_distribution(df, "col")
        assert result["is_high_cardinality"] is True


# ── detect_anomalies ──────────────────────────────────────────────────────────

class TestDetectAnomalies:
    def test_detects_obvious_outlier(self, outlier_df):
        result = detect_anomalies(outlier_df, "x")
        assert result["iqr_outliers_count"] >= 1
        assert result["zscore_outliers_count"] >= 1

    def test_no_anomalies_in_clean_data(self):
        df = pd.DataFrame({"x": [1.0, 2.0, 3.0, 2.5, 2.8, 2.1]})
        result = detect_anomalies(df, "x")
        assert result["iqr_outliers_count"] == 0

    def test_column_not_found(self, outlier_df):
        result = detect_anomalies(outlier_df, "missing")
        assert "error" in result

    def test_non_numeric_returns_error(self, categorical_df):
        result = detect_anomalies(categorical_df, "region")
        assert "error" in result

    def test_severity_high_when_many_outliers(self):
        vals = [1.0, 2.0, 3.0, 1000.0, 2000.0, 3000.0, 4000.0]
        df = pd.DataFrame({"x": vals})
        result = detect_anomalies(df, "x")
        assert result["severity"] in ("high", "medium")

    def test_iqr_bounds_returned(self, outlier_df):
        result = detect_anomalies(outlier_df, "x")
        assert "iqr_bounds" in result
        assert result["iqr_bounds"]["lower"] is not None
        assert result["iqr_bounds"]["upper"] is not None

    def test_example_anomalies_are_list(self, outlier_df):
        result = detect_anomalies(outlier_df, "x")
        assert isinstance(result["example_anomalies"], list)


# ── trend_analysis ────────────────────────────────────────────────────────────

class TestTrendAnalysis:
    def test_upward_trend_detected(self, time_series_df):
        result = trend_analysis(time_series_df, "date", "revenue")
        assert "error" not in result
        assert result["trend_direction"] == "upward"
        assert result["slope"] > 0

    def test_required_fields_present(self, time_series_df):
        result = trend_analysis(time_series_df, "date", "revenue")
        for key in ["trend_direction", "slope", "pct_change_overall", "monthly_averages"]:
            assert key in result

    def test_date_column_not_found(self, time_series_df):
        result = trend_analysis(time_series_df, "missing_date", "revenue")
        assert "error" in result

    def test_value_column_not_found(self, time_series_df):
        result = trend_analysis(time_series_df, "date", "ghost")
        assert "error" in result

    def test_too_few_points_returns_error(self):
        df = pd.DataFrame(
            {"date": pd.to_datetime(["2024-01-01"]), "val": [100.0]}
        )
        result = trend_analysis(df, "date", "val")
        assert "error" in result

    def test_downward_trend(self):
        dates = pd.date_range("2023-01-01", periods=12, freq="ME")
        values = np.linspace(200, 100, 12)
        df = pd.DataFrame({"date": dates, "val": values})
        result = trend_analysis(df, "date", "val")
        assert result["trend_direction"] == "downward"


# ── group_comparison ──────────────────────────────────────────────────────────

class TestGroupComparison:
    def test_basic_comparison(self, categorical_df):
        result = group_comparison(categorical_df, "region", "sales")
        assert "error" not in result
        assert result["group_count"] == 3

    def test_groups_sorted_by_mean_desc(self, categorical_df):
        result = group_comparison(categorical_df, "region", "sales")
        means = [g["mean"] for g in result["groups"]]
        assert means == sorted(means, reverse=True)

    def test_highest_and_lowest_group(self, categorical_df):
        result = group_comparison(categorical_df, "region", "sales")
        assert result["highest_group"] is not None
        assert result["lowest_group"] is not None
        assert result["highest_group"]["mean"] >= result["lowest_group"]["mean"]

    def test_column_not_found(self, categorical_df):
        result = group_comparison(categorical_df, "ghost", "sales")
        assert "error" in result

    def test_non_numeric_value_returns_error(self, categorical_df):
        result = group_comparison(categorical_df, "region", "category")
        assert "error" in result

    def test_vs_overall_pct_field_present(self, categorical_df):
        result = group_comparison(categorical_df, "region", "sales")
        for g in result["groups"]:
            assert "vs_overall_pct" in g

    def test_overall_mean_correct(self, categorical_df):
        result = group_comparison(categorical_df, "region", "sales")
        expected_mean = categorical_df["sales"].mean()
        assert abs(result["overall_mean"] - expected_mean) < 0.01
