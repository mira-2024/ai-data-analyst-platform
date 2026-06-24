"""Tests for the supervised ML pipeline (ml/modeling.py)."""

from __future__ import annotations

import pandas as pd
import pytest

from ml import modeling


def test_detect_task(clean_df, regression_df):
    assert modeling.detect_task(clean_df, "promoted") == "classification"
    assert modeling.detect_task(regression_df, "target") == "regression"


def test_suggest_target_prefers_label(clean_df):
    assert modeling.suggest_target(clean_df) == "promoted"


def test_looks_like_id_detects_identifier(clean_df):
    assert modeling._looks_like_id(clean_df, "emp_id") is True
    assert modeling._looks_like_id(clean_df, "department") is False


def test_classification_pipeline(clean_df):
    res = modeling.train_and_evaluate(clean_df, "promoted")
    assert res["task"] == "classification"
    assert res["best_model"] in {"Logistic Regression", "Random Forest", "Gradient Boosting"}
    # identifier column must be excluded from features
    assert "emp_id" in res["dropped_id_columns"]
    # metrics present and in valid range
    r = res["results"]
    for col in ("accuracy", "precision", "recall", "f1"):
        assert col in r.columns
        assert r[col].between(0, 1).all()
    assert 0.0 <= res["best_score"] <= 1.0
    # classification extras
    assert res["confusion_matrix"].values.sum() == res["n_test"]
    assert not res["feature_importance"].empty


def test_regression_pipeline(regression_df):
    res = modeling.train_and_evaluate(regression_df, "target")
    assert res["task"] == "regression"
    for col in ("r2", "rmse", "mae"):
        assert col in res["results"].columns
    # a strongly linear target should be modelled well
    assert res["best_score"] > 0.8


def test_reproducible(clean_df):
    a = modeling.train_and_evaluate(clean_df, "promoted")["best_score"]
    b = modeling.train_and_evaluate(clean_df, "promoted")["best_score"]
    assert a == b                              # fixed random_state → deterministic


def test_raises_on_too_few_rows():
    df = pd.DataFrame({"x": range(5), "y": [0, 1, 0, 1, 0]})
    with pytest.raises(ValueError):
        modeling.train_and_evaluate(df, "y")


def test_handles_missing_values(messy_df):
    """The pipeline imputes internally, so missing values must not crash it."""
    big = pd.concat([messy_df] * 3, ignore_index=True)   # >= 20 rows
    res = modeling.train_and_evaluate(big, "promoted")
    assert res["task"] == "classification"
