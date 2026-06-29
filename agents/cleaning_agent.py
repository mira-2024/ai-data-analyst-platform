"""
CleaningAgent -- data preparation agent.

Performs deterministic, auditable cleaning steps and returns both the cleaned
DataFrame and a transparent log of exactly what changed. The LLM is used only
to phrase a friendly summary, and is optional.
"""

from __future__ import annotations

import pandas as pd

from utils.data_utils import get_df_summary
from utils import llm


class CleaningAgent:
    def clean(self, df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
        original_shape = df.shape
        df = df.copy()
        report_lines = [
            f"- **Original shape:** {original_shape[0]} rows x {original_shape[1]} columns"
        ]

        df = df.dropna(how="all")
        df = df.dropna(axis=1, how="all")

        dups = int(df.duplicated().sum())
        if dups > 0:
            df = df.drop_duplicates()
            report_lines.append(f"- Removed **{dups}** duplicate rows.")

        str_cols = df.select_dtypes(include="object").columns
        for col in str_cols:
            mask = df[col].notna()
            df.loc[mask, col] = df.loc[mask, col].astype(str).str.strip()

        num_cols = df.select_dtypes(include="number").columns
        filled_num = 0
        for col in num_cols:
            nulls = int(df[col].isnull().sum())
            if nulls > 0:
                df[col] = df[col].fillna(df[col].median())
                filled_num += nulls
        if filled_num:
            report_lines.append(
                f"- Imputed **{filled_num}** missing numeric values with the column median."
            )

        filled_cat = 0
        for col in str_cols:
            nulls = int(df[col].isnull().sum())
            if nulls > 0:
                mode_val = df[col].mode()
                df[col] = df[col].fillna(mode_val[0] if not mode_val.empty else "Unknown")
                filled_cat += nulls
        if filled_cat:
            report_lines.append(
                f"- Imputed **{filled_cat}** missing categorical values with the column mode."
            )

        if filled_num == 0 and filled_cat == 0 and dups == 0:
            report_lines.append("- No duplicates or missing values were found -- data was already clean.")

        report_lines.append(
            f"- **Cleaned shape:** {df.shape[0]} rows x {df.shape[1]} columns"
        )

        deterministic = "### Data Cleaning Report\n\n" + "\n".join(report_lines)

        summary = get_df_summary(df)
        prompt = (
            "You are a data preparation assistant. In 2-3 sentences, summarise the "
            "cleaning that was performed and confirm the dataset is ready for "
            f"analysis. Be concise.\n\nSteps:\n{chr(10).join(report_lines)}\n\n"
            f"Cleaned dataset:\n{summary}"
        )
        narration = llm.narrate(prompt)
        if narration:
            return df, deterministic + "\n\n" + narration
        return df, deterministic
