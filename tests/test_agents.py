"""Tests for the agents and the orchestrator routing."""

from __future__ import annotations

import pandas as pd

from agents.cleaning_agent import CleaningAgent
from orchestrator.orchestrator import Orchestrator


# ── CleaningAgent ────────────────────────────────────────────────────────────
def test_cleaning_imputes_and_dedupes(messy_df):
    cleaned, report = CleaningAgent().clean(messy_df)
    # no missing values remain
    assert cleaned.isnull().sum().sum() == 0
    # duplicates removed
    assert cleaned.duplicated().sum() == 0
    assert isinstance(report, str) and "Cleaning" in report


def test_cleaning_does_not_leave_literal_nan_strings(messy_df):
    """Regression test: missing categoricals must be imputed with the mode,
    not turned into the literal string 'nan'/'None'."""
    cleaned, _ = CleaningAgent().clean(messy_df)
    for bad in ("nan", "None", "NaN"):
        assert bad not in cleaned["dept"].astype(str).values
    # whitespace was trimmed
    assert "Eng " not in cleaned["dept"].values
    assert "Eng" in cleaned["dept"].values


def test_cleaning_does_not_mutate_input(messy_df):
    before = messy_df.copy()
    CleaningAgent().clean(messy_df)
    pd.testing.assert_frame_equal(messy_df, before)


# ── Orchestrator routing (keyword fallback, no LLM) ──────────────────────────
def test_keyword_routing():
    route = Orchestrator._keyword_intent
    assert route("please clean the data") == "clean"
    assert route("analyse the dataset") == "analyze"
    assert route("build a predictive model to predict churn") == "model"
    assert route("show me some charts") == "visualize"
    assert route("generate a full report") == "report"
    assert route("hello there") == "chat"


def test_process_returns_expected_shape(clean_df):
    o = Orchestrator()
    res = o.process(clean_df, "analyse the dataset", [])
    assert set(res) == {"intent", "text", "figures", "cleaned_df"}
    assert res["intent"] == "analyze"
    assert isinstance(res["text"], str) and res["text"]


def test_process_model_intent_produces_figures(clean_df):
    o = Orchestrator()
    res = o.process(clean_df, "train a model to predict promoted", [])
    assert res["intent"] == "model"
    assert len(res["figures"]) >= 1
