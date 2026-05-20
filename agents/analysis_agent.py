import os
import pandas as pd
from google import genai
from dotenv import load_dotenv
from utils.data_utils import get_df_summary, get_data_sample

load_dotenv()
_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "gemini-2.5-flash"


class AnalysisAgent:
    def analyze(self, df: pd.DataFrame, query: str = "") -> str:
        summary = get_df_summary(df)
        sample = get_data_sample(df, n=10)
        user_request = query if query else "Provide a comprehensive statistical analysis with key insights."

        prompt = f"""You are an expert data analyst. Analyze the dataset below and answer the user's request.
Return well-structured markdown with sections, bullet points, and any relevant statistics.

Dataset Summary:
{summary}

Sample Data (first 10 rows):
{sample}

User Request: {user_request}

Focus on:
- Key statistics and distributions
- Correlations and relationships between variables
- Outliers or anomalies
- Actionable insights
"""
        response = _client.models.generate_content(model=MODEL, contents=prompt)
        return response.text.strip()
