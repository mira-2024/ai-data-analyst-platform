"""
AnalysisAgent — statistical analysis agent.

Rewritten to be *computation-first*. Instead of asking a language model to
"analyse" a text summary (which produces plausible-sounding but unverified
prose), this agent now computes real exploratory and inferential statistics
with pandas/SciPy via the ``ml`` package, and only then uses the LLM — if
available — to interpret those concrete numbers.
"""

from __future__ import annotations

import pandas as pd

from ml import eda, statistics
from utils import llm


class AnalysisAgent:
    def analyze(self, df: pd.DataFrame, query: str = "") -> str:
        profile = eda.profile_dataset(df)
        desc = eda.descriptive_stats(df)
        cats = eda.categorical_summary(df)
        outliers = eda.outlier_summary(df)
        corr_sig = statistics.correlation_significance(df, method="pearson")

        sections = [
            "## Statistical Analysis",
            "",
            f"**Dataset:** {profile['n_rows']:,} rows x {profile['n_cols']} columns "
            f"({profile['n_numeric']} numeric, {profile['n_categorical']} categorical). "
            f"Missing: {profile['missing_pct']}% of cells. "
            f"Duplicate rows: {profile['duplicate_rows']}.",
        ]

        if not desc.empty:
            sections += ["", "### Descriptive statistics (numeric)", "",
                         desc.to_markdown()]
            # Flag notable distribution shapes from the real skewness values.
            skewed = desc[desc["skewness"].abs() > 1]
            if not skewed.empty:
                feats = ", ".join(f"`{i}` (skew={skewed.loc[i, 'skewness']:.2f})"
                                  for i in skewed.index)
                sections += ["", f"_Strongly skewed (|skew| > 1): {feats}. "
                                 f"Consider a log/transform before linear modeling._"]

        if not cats.empty:
            sections += ["", "### Categorical summary", "", cats.to_markdown()]

        if not corr_sig.empty:
            sig = corr_sig[corr_sig["significant"] == "significant"].head(8)
            sections += ["", "### Significant correlations (Pearson, p < 0.05)", ""]
            sections += [sig.to_markdown(index=False) if not sig.empty
                         else "_No statistically significant linear correlations found._"]

        if not outliers.empty:
            flagged = outliers[outliers["iqr_outliers"] > 0]
            if not flagged.empty:
                sections += ["", "### Outliers (IQR rule)", "",
                             flagged[["iqr_outliers", "iqr_outlier_pct"]].to_markdown()]

        deterministic = "\n".join(sections)

        # Optional LLM interpretation grounded in the computed numbers.
        request = query or "Summarise the key statistical findings and what they imply."
        prompt = (
            "You are a senior data analyst. Using ONLY the computed statistics below "
            "(do not invent numbers), write a concise interpretation (4-6 sentences) "
            f"answering the user's request: \"{request}\".\n\n{deterministic}"
        )
        interpretation = llm.narrate(prompt)
        if interpretation:
            return deterministic + "\n\n### Interpretation\n\n" + interpretation
        return deterministic
