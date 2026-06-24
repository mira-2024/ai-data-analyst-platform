"""Shared pytest fixtures for the DataFlow AI test suite."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def clean_df() -> pd.DataFrame:
    """A clean, balanced classification dataset (employee promotion)."""
    rng = np.random.default_rng(42)
    n = 80
    perf = rng.normal(3.8, 0.5, n).clip(1, 5)
    salary = 40000 + perf * 12000 + rng.normal(0, 4000, n)
    promoted = (perf + rng.normal(0, 0.3, n) > 4.0)
    return pd.DataFrame({
        "emp_id": range(1, n + 1),                       # identifier (should be dropped)
        "department": rng.choice(["Eng", "HR", "Finance"], n),
        "age": rng.integers(22, 60, n),
        "salary": salary.round(0),
        "performance_score": perf.round(2),
        "promoted": np.where(promoted, "Yes", "No"),
    })


@pytest.fixture
def messy_df() -> pd.DataFrame:
    """A deliberately messy dataset: missing values, duplicates, whitespace,
    a constant column."""
    df = pd.DataFrame({
        "dept": ["Eng ", "Eng", None, " HR", "HR", None, "Finance", "HR"],
        "age": [25, 30, None, 40, 35, 28, None, 33],
        "salary": [90000, None, 70000, None, 60000, 80000, 120000, 75000],
        "constant": [7] * 8,
        "promoted": ["Yes", "No", "Yes", "No", "No", "Yes", "Yes", "No"],
    })
    # add duplicate rows
    return pd.concat([df, df.iloc[:2]], ignore_index=True)


@pytest.fixture
def regression_df() -> pd.DataFrame:
    """A continuous-target dataset for regression tests."""
    rng = np.random.default_rng(0)
    n = 90
    x1 = rng.normal(10, 3, n)
    x2 = rng.normal(50, 10, n)
    y = 2.5 * x1 + 0.8 * x2 + rng.normal(0, 2, n)
    return pd.DataFrame({"feature_a": x1, "feature_b": x2, "target": y})
