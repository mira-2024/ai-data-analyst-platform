"""Tests for the exploratory data analysis module (ml/eda.py)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ml import eda


def test_profile_counts(messy_df):
    p = eda.profile_dataset(messy_df)
    assert p["n_rows"] == len(messy_df)
    assert p["n_cols"] == messy_df.shape[1]
    assert p["duplicate_rows"] == 2          # two duplicate rows were appended
    assert p["missing_cells"] > 0
    assert 0 <= p["missing_pct"] <= 100


def test_column_typing(clean_df):
    num = eda.numeric_columns(clean_df)
    cat = eda.categorical_columns(clean_df)
    assert "salary" in num and "age" in num
    assert "department" in cat and "promoted" in cat
    assert set(num).isdisjoint(cat)


def test_descriptive_stats_has_moments(clean_df):
    desc = eda.descriptive_stats(clean_df)
    for col in ("mean", "std", "median", "skewness", "kurtosis", "cv", "iqr"):
        assert col in desc.columns
    assert "salary" in desc.index


def test_outlier_detection_flags_injected_outlier(clean_df):
    df = clean_df.copy()
    df.loc[0, "salary"] = 10_000_000          # extreme outlier
    out = eda.outlier_summary(df)
    assert out.loc["salary", "iqr_outliers"] >= 1


def test_correlation_matrix_is_square(clean_df):
    corr = eda.correlation_matrix(clean_df)
    assert corr.shape[0] == corr.shape[1]
    assert np.allclose(np.diag(corr.values), 1.0)


def test_top_correlations_sorted(clean_df):
    top = eda.top_correlations(clean_df)
    if not top.empty:
        abs_corr = top["correlation"].abs().tolist()
        assert abs_corr == sorted(abs_corr, reverse=True)
