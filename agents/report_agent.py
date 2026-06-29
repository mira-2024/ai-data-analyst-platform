"""
ReportAgent -- automated reporting agent.

Assembles a professional, reproducible report from real computed statistics
(EDA + significance tests) and, when available, an LLM-written executive
summary and recommendations grounded in those numbers.
"""

from __future__ import annotations

import pandas as pd

from ml import eda, statistics
from utils import llm


class ReportAgent:
    def generate(self, df: pd.DataFrame, prior_analysis: str = "") -> str:
        profile = eda.profile_dataset(df)
        desc = eda.descriptive_stats(df)
        missing = eda.missing_analysis(df)
        top_corr = statistics.correlation_significance(df).head(5)

        parts = [
            "# Data Analysis Report",
            "",
            "## 1. Dataset Overview",
            "",
            f"- **Rows:** {profile['n_rows']:,}",
            f"- **Columns:** {profile['n_cols']} "
            f"({profile['n_numeric']} numeric, {profile['n_categorical']} categorical, "
            f"{profile['n_datetime']} datetime)",
            f"- **Missing cells:** {profile['missing_cells']:,} ({profile['missing_pct']}%)",
            f"- **Duplicate rows:** {profile['duplicate_rows']} ({profile['duplicate_pct']}%)",
            f"- **Memory:** {profile['memory_kb']} KB",
        ]

        if not desc.empty:
            parts += [
                "",
                "## 2. Descriptive Statistics",
                "",
                desc.to_markdown(),
            ]
            skewed = desc[desc["skewness"].abs() > 1]
            if not skewed.empty:
                feats = ", ".join(f"`{i}`" for i in skewed.index)
                parts += ["", f"_Strongly skewed features (|skew| > 1): {feats}._"]

        if not missing.empty:
            has_missing = missing[missing["missing_count"] > 0]
            if not has_missing.empty:
                parts += [
                    "",
                    "## 3. Missing Values",
                    "",
                    has_missing.to_markdown(index=False),
                ]

        if not top_corr.empty:
            sig = top_corr[top_corr["significant"] == "significant"]
            if not sig.empty:
                parts += [
                    "",
                    "## 4. Key Correlations",
                    "",
                    sig.to_markdown(index=False),
                ]

        deterministic = "\n".join(parts)

        context = prior_analysis or deterministic
        prompt = (
            "You are a senior data scientist writing an executive summary. "
            "Using ONLY the statistics below (do not invent numbers), write: "
            "(1) a 3-sentence executive summary, (2) 3 key insights, "
            "(3) 2 recommended next steps. Be specific and cite actual numbers.\n\n"
            f"{context}"
        )
        narrative = llm.narrate(prompt)
        if narrative:
            return (
                "## Executive Summary\n\n"
                + narrative
                + "\n\n---\n\n"
                + deterministic
            )
        return deterministic
