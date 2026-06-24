"""Tests for the inferential statistics module (ml/statistics.py)."""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

from ml import statistics


def test_normality_detects_normal_and_skewed():
    rng = np.random.default_rng(1)
    normal = pd.Series(rng.normal(0, 1, 500))
    skewed = pd.Series(rng.exponential(1.0, 500))
    assert statistics.normality_test(normal)["normal"] is True
    assert statistics.normality_test(skewed)["normal"] is False


def test_correlation_significance_flags_real_correlation():
    rng = np.random.default_rng(2)
    x = rng.normal(0, 1, 200)
    df = pd.DataFrame({"x": x, "y": 3 * x + rng.normal(0, 0.1, 200)})
    res = statistics.correlation_significance(df)
    row = res.iloc[0]
    assert abs(row["r"]) > 0.9
    assert row["significant"] == "significant"


def test_correlation_significance_skips_constant_column():
    """Regression test: a zero-variance column must not raise or appear."""
    rng = np.random.default_rng(3)
    df = pd.DataFrame({
        "a": rng.normal(0, 1, 50),
        "b": rng.normal(0, 1, 50),
        "constant": [5.0] * 50,
    })
    with warnings.catch_warnings():
        warnings.simplefilter("error")        # any warning fails the test
        res = statistics.correlation_significance(df)
    feats = set(res["feature_a"]) | set(res["feature_b"])
    assert "constant" not in feats


def test_compare_groups_two_and_many():
    rng = np.random.default_rng(4)
    df = pd.DataFrame({
        "value": np.concatenate([rng.normal(0, 1, 50), rng.normal(3, 1, 50)]),
        "two": ["A"] * 50 + ["B"] * 50,
        "many": (["A"] * 33 + ["B"] * 33 + ["C"] * 34),
    })
    assert statistics.compare_groups(df, "value", "two")["test"] == "Welch t-test"
    assert statistics.compare_groups(df, "value", "many")["test"] == "one-way ANOVA"


def test_chi_square_independence():
    df = pd.DataFrame({
        "x": ["A", "A", "B", "B"] * 25,
        "y": ["yes", "no", "yes", "no"] * 25,
    })
    res = statistics.chi_square_independence(df, "x", "y")
    assert "p_value" in res and "cramers_v" in res


def test_feature_target_screen_ranks_by_pvalue(clean_df):
    res = statistics.feature_target_screen(clean_df, "promoted")
    assert not res.empty
    pvals = res["p_value"].tolist()
    assert pvals == sorted(pvals)             # ranked ascending by p-value
    # performance_score is engineered to drive promotion → should be significant
    perf = res[res["feature"] == "performance_score"].iloc[0]
    assert perf["significant"] == "significant"
