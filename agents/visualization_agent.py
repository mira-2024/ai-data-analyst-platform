"""
VisualizationAgent — automated charting agent.

When an LLM is available it proposes a tailored set of charts (returned as JSON
specs) which are then rendered with real data via Plotly. When no LLM is
available it falls back to a deterministic, rule-based EDA chart set
(distributions, correlation heatmap, category counts, relationships) so the
feature still works offline.
"""

from __future__ import annotations

import json
import re

import pandas as pd
import plotly.express as px

from ml import eda
from utils.data_utils import get_df_summary
from utils import llm


class VisualizationAgent:
    def generate(self, df: pd.DataFrame, query: str = "") -> list[dict]:
        user_request = query or "Generate the most insightful visualizations for this dataset."

        specs = self._llm_specs(df, user_request) if llm.available() else []
        figures = []
        for spec in specs[:4]:
            fig = self._build_figure(df, spec)
            if fig is not None:
                figures.append({"title": spec.get("title", "Chart"), "figure": fig,
                                "description": spec.get("description", "")})

        # Fallback (or top-up) with deterministic EDA charts.
        if not figures:
            figures = self._auto_charts(df)
        return figures

    # ── LLM-proposed charts ───────────────────────────────────────────────────
    def _llm_specs(self, df: pd.DataFrame, user_request: str) -> list[dict]:
        summary = get_df_summary(df)
        prompt = f"""You are a data visualization expert. Given the dataset information below, suggest up to 4 charts.

Dataset Summary:
{summary}

User Request: {user_request}

Respond with ONLY a valid JSON array (no markdown). Each element must have:
- "title": string
- "type": one of ["histogram", "scatter", "bar", "box", "heatmap", "pie", "line"]
- "x": column name or null
- "y": column name or null
- "color": column name or null
- "description": one sentence describing the insight

Use only column names that exist: {list(df.columns)}
"""
        raw = llm.narrate(prompt)
        if not raw:
            return []
        match = re.search(r"```(?:json)?\s*(.*?)\s*```", raw, re.DOTALL)
        if match:
            raw = match.group(1)
        try:
            specs = json.loads(raw)
            return specs if isinstance(specs, list) else []
        except json.JSONDecodeError:
            return []

    # ── deterministic fallback ────────────────────────────────────────────────
    def _auto_charts(self, df: pd.DataFrame) -> list[dict]:
        figs = []
        num = eda.numeric_columns(df)
        cats = eda.categorical_columns(df)

        # Correlation heatmap
        if len(num) >= 2:
            corr = df[num].corr().round(2)
            fig = px.imshow(corr, text_auto=True, color_continuous_scale="RdBu_r",
                            title="Correlation heatmap (numeric features)",
                            template="plotly_white", aspect="auto")
            figs.append({"title": "Correlation heatmap", "figure": fig,
                         "description": "Pairwise Pearson correlations between numeric features."})

        # Distribution of the highest-variance numeric feature
        if num:
            target = df[num].var(numeric_only=True).idxmax()
            fig = px.histogram(df, x=target, title=f"Distribution of {target}",
                               template="plotly_white", marginal="box")
            figs.append({"title": f"Distribution of {target}", "figure": fig,
                         "description": f"Histogram and box plot of {target}."})

        # Counts of the lowest-cardinality categorical
        if cats:
            cat = min(cats, key=lambda c: df[c].nunique())
            vc = df[cat].value_counts().reset_index()
            vc.columns = [cat, "count"]
            fig = px.bar(vc, x=cat, y="count", title=f"Counts by {cat}",
                         template="plotly_white", color=cat)
            figs.append({"title": f"Counts by {cat}", "figure": fig,
                         "description": f"Frequency of each category in {cat}."})

        # Relationship between the two highest-variance numeric features
        if len(num) >= 2:
            variances = df[num].var(numeric_only=True).sort_values(ascending=False)
            x, y = variances.index[0], variances.index[1]
            color = cats[0] if cats else None
            fig = px.scatter(df, x=x, y=y, color=color, title=f"{y} vs {x}",
                             template="plotly_white")
            figs.append({"title": f"{y} vs {x}", "figure": fig,
                         "description": f"Relationship between {x} and {y}."})
        return figs[:4]

    # ── shared figure builder ─────────────────────────────────────────────────
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
