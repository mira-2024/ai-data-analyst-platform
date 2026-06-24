"""
AnalystAgent — exploratory data analysis and insight generation.

Operates on the cleaned DataFrame from CleanerAgent.
Uses statistical tools to discover patterns, correlations, anomalies,
and generates structured insights for downstream agents.
"""

from __future__ import annotations

import json

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.analyst.tools import (
    correlation_analysis,
    detect_anomalies,
    frequency_distribution,
    group_comparison,
    statistical_summary,
    trend_analysis,
)
from app.agents.base_agent import BaseAgent
from app.agents.llm_client import LLMResponse, ToolDefinition
from app.orchestration.event_bus import EventBus
from app.orchestration.events import InsightGeneratedEvent
from app.orchestration.state import AnalysisState
from app.schemas.agent import AnalystOutput, CorrelationResult, Insight


class AnalystAgent(BaseAgent):
    agent_name = "analyst"

    def __init__(self, bus: EventBus, db: AsyncSession) -> None:
        super().__init__(bus=bus, db=db)
        self._df: pd.DataFrame | None = None

    def _get_tools(self) -> list[ToolDefinition]:
        return [
            {
                "name": "statistical_summary",
                "description": "Compute descriptive statistics (mean, median, std, skewness, etc.) for numeric columns.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "columns": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific columns to analyze. Leave empty for all numeric columns.",
                        },
                    },
                },
            },
            {
                "name": "correlation_analysis",
                "description": "Compute pairwise Pearson correlations between all numeric columns. Returns significant pairs with interpretations.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "threshold": {
                            "type": "number",
                            "description": "Minimum absolute correlation to report (0.0–1.0). Default 0.3.",
                        },
                    },
                },
            },
            {
                "name": "frequency_distribution",
                "description": "Analyze value frequency distribution for a categorical or low-cardinality column.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string", "description": "Column name"},
                        "top_n": {"type": "integer", "description": "Number of top values to return (default 20)"},
                    },
                    "required": ["column"],
                },
            },
            {
                "name": "detect_anomalies",
                "description": "Detect anomalies/outliers in a numeric column using IQR and Z-score methods.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string", "description": "Numeric column name"},
                    },
                    "required": ["column"],
                },
            },
            {
                "name": "trend_analysis",
                "description": "Analyze trend in a numeric value over time. Requires a datetime and a numeric column.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "date_column": {"type": "string", "description": "Datetime column"},
                        "value_column": {"type": "string", "description": "Numeric value column"},
                    },
                    "required": ["date_column", "value_column"],
                },
            },
            {
                "name": "group_comparison",
                "description": "Compare a numeric metric across groups defined by a categorical column.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "group_column": {"type": "string", "description": "Categorical column to group by"},
                        "value_column": {"type": "string", "description": "Numeric column to compare"},
                    },
                    "required": ["group_column", "value_column"],
                },
            },
        ]

    def _execute_tool(self, tool_name: str, tool_input: dict):
        assert self._df is not None
        df = self._df

        if tool_name == "statistical_summary":
            return statistical_summary(df, columns=tool_input.get("columns"))
        if tool_name == "correlation_analysis":
            return correlation_analysis(df, threshold=tool_input.get("threshold", 0.3))
        if tool_name == "frequency_distribution":
            return frequency_distribution(df, tool_input["column"], top_n=tool_input.get("top_n", 20))
        if tool_name == "detect_anomalies":
            return detect_anomalies(df, tool_input["column"])
        if tool_name == "trend_analysis":
            return trend_analysis(df, tool_input["date_column"], tool_input["value_column"])
        if tool_name == "group_comparison":
            return group_comparison(df, tool_input["group_column"], tool_input["value_column"])

        return {"error": f"Unknown tool: {tool_name}"}

    def _build_user_message(self, state: AnalysisState) -> str:
        summary = state["agent_summary"]
        config = state.get("config", {})
        focus = config.get("focus_areas", [])

        # Include cleaning summary if available
        cleaning_context = ""
        cleaner_output = state.get("cleaner_output")
        if cleaner_output:
            cleaning_context = f"""
## Cleaning Summary (from CleanerAgent)
- Quality score: {cleaner_output.quality_score:.2f}
- Rows: {cleaner_output.rows_before} → {cleaner_output.rows_after}
- Actions taken: {len(cleaner_output.actions)}
- {cleaner_output.summary}
"""

        msg = f"""Analyze the following cleaned dataset and generate meaningful insights.

## Dataset
- Shape: {summary['shape']['rows']} rows × {summary['shape']['columns']} columns
- Numeric columns: {[c['name'] for c in summary['columns'] if c['dtype'] in ('integer', 'float', 'numeric')]}
- Categorical columns: {[c['name'] for c in summary['columns'] if c['dtype'] in ('object', 'string', 'category')]}
- Datetime columns: {summary['likely_datetime_columns']}
{cleaning_context}

## Column Details
{json.dumps(summary['columns'], indent=2)}

## Sample Rows
{json.dumps(summary['sample_rows'], indent=2)}
"""
        if focus:
            msg += f"\n## Focus Areas\n{', '.join(focus)}\n"

        msg += """
## Task
1. Start with statistical_summary to understand the overall data landscape
2. Run correlation_analysis to find relationships between numeric columns
3. Run frequency_distribution for each important categorical column
4. Run detect_anomalies on high-variance numeric columns
5. Run trend_analysis if datetime columns are present
6. Run group_comparison if there are categorical + numeric column pairs of interest

After all analysis, produce an AnalystOutput JSON:
```json
{
  "insights": [
    {
      "title": "<concise title>",
      "description": "<specific finding with numbers>",
      "category": "<correlation|anomaly|trend|distribution|comparison>",
      "confidence": <0.0-1.0>,
      "columns_involved": ["col1", "col2"],
      "supporting_statistics": {"key": "value"},
      "importance": "<high|medium|low>"
    }
  ],
  "correlations": [
    {
      "column_a": "<col>",
      "column_b": "<col>",
      "correlation": <float>,
      "interpretation": "<plain English>"
    }
  ],
  "anomalies_detected": [{"column": "<col>", "count": <int>, "severity": "<high|medium|low>"}],
  "hypothesis": ["<testable hypothesis 1>", "<testable hypothesis 2>"],
  "key_statistics": {"<col>": {"mean": <float>, "std": <float>}},
  "recommended_visualizations": ["scatter", "heatmap", "histogram"],
  "summary": "<two paragraph executive summary with specific numbers>"
}
```

Minimum 3 insights. Be specific — always include column names and numeric values.
"""
        return msg

    def _parse_output(self, llm_response: LLMResponse, state: AnalysisState) -> AnalystOutput:
        try:
            data = self._extract_json_from_response(llm_response.content)
        except ValueError:
            return AnalystOutput(
                insights=[],
                correlations=[],
                anomalies_detected=[],
                hypothesis=[],
                key_statistics={},
                recommended_visualizations=["bar", "scatter", "histogram"],
                summary="Analysis completed. Unable to parse structured output.",
            )

        insights = [
            Insight(
                title=i.get("title", "Finding"),
                description=i.get("description", ""),
                category=i.get("category", "general"),
                confidence=float(i.get("confidence", 0.7)),
                columns_involved=i.get("columns_involved", []),
                supporting_statistics=i.get("supporting_statistics", {}),
                importance=i.get("importance", "medium"),
            )
            for i in data.get("insights", [])
        ]

        correlations = [
            CorrelationResult(
                column_a=c.get("column_a", ""),
                column_b=c.get("column_b", ""),
                correlation=float(c.get("correlation", 0)),
                interpretation=c.get("interpretation", ""),
            )
            for c in data.get("correlations", [])
        ]

        output = AnalystOutput(
            insights=insights,
            correlations=correlations,
            anomalies_detected=data.get("anomalies_detected", []),
            hypothesis=data.get("hypothesis", []),
            key_statistics=data.get("key_statistics", {}),
            recommended_visualizations=data.get("recommended_visualizations", []),
            summary=data.get("summary", ""),
        )
        return output

    async def run(self, state: AnalysisState, bus: EventBus) -> AnalysisState:
        # Use cleaned DataFrame if available, else raw.
        # Must use `is not None` — `or` triggers bool(df) which raises ValueError.
        _clean = state.get("clean_df")
        self._df = _clean if _clean is not None else state["raw_df"]

        await self._emit_progress(state, "Starting EDA", "Analyzing dataset structure", 0.05)

        llm_response = await self._run_llm(state)

        await self._emit_progress(state, "Generating insights", "Structuring findings", 0.85)

        output = self._parse_output(llm_response, state)
        output._tokens_in = llm_response.tokens_in   # type: ignore[attr-defined]
        output._tokens_out = llm_response.tokens_out  # type: ignore[attr-defined]

        # Emit top insights to the event stream
        for insight in output.insights[:3]:  # Top 3 only to avoid SSE flood
            await bus.emit(InsightGeneratedEvent(
                session_id=state["session_id"],
                agent_run_id=state.get("analyst_run_id"),
                agent_name="analyst",
                title=insight.title,
                description=insight.description,
                category=insight.category,
                confidence=insight.confidence,
            ))

        await self._emit_progress(state, "Done", "Analysis complete", 1.0)

        state["analyst_output"] = output
        return state
