import os
import json
import re
import pandas as pd
import plotly.express as px
from google import genai
from dotenv import load_dotenv
from utils.data_utils import get_df_summary

load_dotenv()
_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "gemini-2.5-flash"


class VisualizationAgent:
    def generate(self, df: pd.DataFrame, query: str = "") -> list[dict]:
        summary = get_df_summary(df)
        user_request = query if query else "Generate the most insightful visualizations for this dataset."

        prompt = f"""You are a data visualization expert. Given the dataset information below, suggest up to 4 charts.

Dataset Summary:
{summary}

User Request: {user_request}

Respond with ONLY a valid JSON array (no markdown, no explanation). Each element must have:
- "title": string — chart title
- "type": one of ["histogram", "scatter", "bar", "box", "heatmap", "pie", "line"]
- "x": column name for x-axis or null
- "y": column name for y-axis or null
- "color": column name for color grouping or null
- "description": one sentence describing the insight

Use only column names that exist: {list(df.columns)}
"""
        response = _client.models.generate_content(model=MODEL, contents=prompt)
        raw = response.text.strip()

        match = re.search(r"```(?:json)?\s*(.*?)\s*```", raw, re.DOTALL)
        if match:
            raw = match.group(1)

        try:
            specs = json.loads(raw)
        except json.JSONDecodeError:
            return []

        figures = []
        for spec in specs[:4]:
            fig = self._build_figure(df, spec)
            if fig is not None:
                figures.append({
                    "title": spec.get("title", "Chart"),
                    "figure": fig,
                    "description": spec.get("description", ""),
                })
        return figures

    def _build_figure(self, df: pd.DataFrame, spec: dict):
        cols = set(df.columns)

        def valid(col):
            return col if col and col in cols else None

        chart = spec.get("type", "")
        x = valid(spec.get("x"))
        y = valid(spec.get("y"))
        color = valid(spec.get("color"))
        title = spec.get("title", "")

        try:
            if chart == "histogram" and x:
                return px.histogram(df, x=x, color=color, title=title, template="plotly_white")
            elif chart == "scatter" and x and y:
                return px.scatter(df, x=x, y=y, color=color, title=title, template="plotly_white")
            elif chart == "bar":
                if x and y:
                    return px.bar(df, x=x, y=y, color=color, title=title, template="plotly_white")
                elif x:
                    vc = df[x].value_counts().reset_index()
                    vc.columns = [x, "count"]
                    return px.bar(vc, x=x, y="count", title=title, template="plotly_white")
            elif chart == "box" and y:
                return px.box(df, x=x, y=y, color=color, title=title, template="plotly_white")
            elif chart == "line" and x and y:
                return px.line(df, x=x, y=y, color=color, title=title, template="plotly_white")
            elif chart == "pie" and x:
                vc = df[x].value_counts().reset_index()
                vc.columns = [x, "count"]
                return px.pie(vc, names=x, values="count", title=title)
            elif chart == "heatmap":
                num_df = df.select_dtypes(include="number")
                if len(num_df.columns) > 1:
                    corr = num_df.corr().round(2)
                    return px.imshow(corr, text_auto=True, color_continuous_scale="RdBu_r",
                                     title=title, template="plotly_white")
        except Exception:
            pass
        return None
