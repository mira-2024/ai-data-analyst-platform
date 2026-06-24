"""
ReportAgent — automated reporting agent.

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
            parts += ["", "## 2. Key Statistics", "", desc.to_markdown()]

        if not missing.empty:
            parts += ["", "## 3. Missing-Value Profile", "", missing.to_markdown()]
        else:
            parts += ["", "## 3. Missing-Value Profile", "",
                      "_No missing values detected._"]

        if not top_corr.empty:
            parts += ["", "## 4. Strongest Correlations (with significance)", "",
                      top_corr.to_markdown(index=False)]

        deterministic = "\n".join(parts)

        # Optional LLM-written executive summary + recommendations.
        prompt = (
            "You are a senior data analyst. Based ONLY on the computed report below "
            "(do not invent numbers), write two short sections in markdown:\n"
            "## Executive Summary (2-3 sentences)\n"
            "## Recommendations (3 concrete, data-driven bullet points)\n\n"
            f"{deterministic}"
            + (f"\n\nPrior analysis context:\n{prior_analysis}" if prior_analysis else "")
        )
        narrative = llm.narrate(prompt)
        if narrative:
            return narrative + "\n\n---\n\n" + deterministic
        return deterministic
