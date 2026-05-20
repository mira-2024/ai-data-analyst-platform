import os
import pandas as pd
from google import genai
from dotenv import load_dotenv
from utils.data_utils import get_df_summary

load_dotenv()
_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "gemini-2.5-flash"


class CleaningAgent:
    def clean(self, df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
        original_shape = df.shape
        report_lines = [f"Original shape: {original_shape[0]} rows × {original_shape[1]} columns"]

        df = df.dropna(how="all")
        df = df.dropna(axis=1, how="all")

        dups = df.duplicated().sum()
        if dups > 0:
            df = df.drop_duplicates()
            report_lines.append(f"Removed {dups} duplicate rows.")

        str_cols = df.select_dtypes(include="object").columns
        for col in str_cols:
            df[col] = df[col].str.strip()

        num_cols = df.select_dtypes(include="number").columns
        filled_num = 0
        for col in num_cols:
            nulls = df[col].isnull().sum()
            if nulls > 0:
                df[col] = df[col].fillna(df[col].median())
                filled_num += nulls
        if filled_num:
            report_lines.append(f"Filled {filled_num} missing numeric values with column medians.")

        filled_cat = 0
        for col in str_cols:
            nulls = df[col].isnull().sum()
            if nulls > 0:
                mode_val = df[col].mode()
                df[col] = df[col].fillna(mode_val[0] if not mode_val.empty else "Unknown")
                filled_cat += nulls
        if filled_cat:
            report_lines.append(f"Filled {filled_cat} missing categorical values with column modes.")

        report_lines.append(f"Cleaned shape: {df.shape[0]} rows × {df.shape[1]} columns")

        summary = get_df_summary(df)
        prompt = f"""You are a data cleaning assistant. Summarize the cleaning steps taken and the current state of the dataset in 3-5 clear bullet points. Be concise.

Cleaning steps performed:
{chr(10).join(report_lines)}

Cleaned dataset summary:
{summary}"""

        response = _client.models.generate_content(model=MODEL, contents=prompt)
        return df, response.text.strip()
