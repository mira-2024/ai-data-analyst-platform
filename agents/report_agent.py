import os
import pandas as pd
from google import genai
from dotenv import load_dotenv
from utils.data_utils import get_df_summary, get_data_sample

load_dotenv()
_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "gemini-2.5-flash"


class ReportAgent:
    def generate(self, df: pd.DataFrame, prior_analysis: str = "") -> str:
        summary = get_df_summary(df)
        sample = get_data_sample(df, n=10)
        prior_section = f"\nPrior Analysis:\n{prior_analysis}\n" if prior_analysis else ""

        prompt = f"""You are a senior data analyst writing a professional data report.
Generate a comprehensive markdown report with the following sections:

1. **Executive Summary** — 2-3 sentence overview
2. **Dataset Overview** — shape, columns, data types, missing values
3. **Key Statistics** — important numeric stats
4. **Key Findings** — top 5 insights from the data
5. **Recommendations** — 3 actionable recommendations based on the data
6. **Conclusion** — brief closing statement

Dataset Summary:
{summary}

Sample Data:
{sample}
{prior_section}

Write in a professional tone. Use tables where appropriate. Be specific with numbers.
"""
        response = _client.models.generate_content(model=MODEL, contents=prompt)
        return response.text.strip()
