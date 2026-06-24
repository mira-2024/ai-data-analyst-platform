"""
VisualizerAgent — chart generation and data storytelling through visuals.

Consumes analyst insights + cleaned DataFrame.
Selects the most appropriate chart types, generates full Plotly figure
dicts, and returns a structured VisualizerOutput for frontend rendering.
"""

from __future__ import annotations

import json
import uuid

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base_agent import BaseAgent
from app.agents.llm_client import LLMResponse, ToolDefinition
from app.agents.visualizer.tools import (
    create_bar_chart,
    create_box_plot,
    create_correlation_heatmap,
    create_histogram,
    create_line_chart,
    create_scatter_plot,
)
from app.orchestration.event_bus import EventBus
from app.orchestration.events import ChartGeneratedEvent
from app.orchestration.state import AnalysisState
from app.schemas.agent import PlotlyChartSpec, VisualizerOutput


class VisualizerAgent(BaseAgent):
    agent_name = "visualizer"

    def __init__(self, bus: EventBus, db: AsyncSession) -> None:
        super().__init__(bus=bus, db=db)
        self._df: pd.DataFrame | None = None
        # Accumulates every successful chart dict produced by _execute_tool
        self._chart_results: list[dict] = []

    # ── Tool definitions ───────────────────────────────────────────────────────

    def _get_tools(self) -> list[ToolDefinition]:
        return [
            {
                "name": "create_bar_chart",
                "description": (
                    "Create a horizontal bar chart showing category frequencies or aggregated values. "
                    "Use for comparing categories, distributions, or rankings."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "category_column": {
                            "type": "string",
                            "description": "Categorical column for the y-axis",
                        },
                        "value_column": {
                            "type": "string",
                            "description": "Numeric column to aggregate (omit = count occurrences)",
                        },
                        "title": {"type": "string", "description": "Chart title"},
                        "top_n": {
                            "type": "integer",
                            "description": "Show top N categories (default 15)",
                        },
                    },
                    "required": ["category_column"],
                },
            },
            {
                "name": "create_histogram",
                "description": (
                    "Create a histogram for a numeric column. "
                    "Use to understand value distribution, skewness, and spread."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "column": {
                            "type": "string",
                            "description": "Numeric column to plot",
                        },
                        "bins": {
                            "type": "integer",
                            "description": "Number of bins (default 30)",
                        },
                        "title": {"type": "string", "description": "Chart title"},
                    },
                    "required": ["column"],
                },
            },
            {
                "name": "create_scatter_plot",
                "description": (
                    "Create a scatter plot between two numeric columns, with optional color grouping. "
                    "Includes an OLS trend line when no color grouping is specified. "
                    "Use to show relationships and correlations."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "x_column": {
                            "type": "string",
                            "description": "Numeric column for x-axis",
                        },
                        "y_column": {
                            "type": "string",
                            "description": "Numeric column for y-axis",
                        },
                        "color_column": {
                            "type": "string",
                            "description": "Optional categorical column to color-code points",
                        },
                        "title": {"type": "string", "description": "Chart title"},
                    },
                    "required": ["x_column", "y_column"],
                },
            },
            {
                "name": "create_correlation_heatmap",
                "description": (
                    "Create a Pearson correlation heatmap for all numeric columns. "
                    "Use when there are 3+ numeric columns and the analyst found significant correlations."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Chart title"},
                    },
                },
            },
            {
                "name": "create_line_chart",
                "description": (
                    "Create a line chart for time-series or ordered numeric data. "
                    "Use when a datetime column exists and trends were identified."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "x_column": {
                            "type": "string",
                            "description": "Datetime or ordered column for x-axis",
                        },
                        "y_columns": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "One or more numeric columns to plot as lines",
                        },
                        "title": {"type": "string", "description": "Chart title"},
                    },
                    "required": ["x_column", "y_columns"],
                },
            },
            {
                "name": "create_box_plot",
                "description": (
                    "Create a box plot showing distribution and outliers. "
                    "Use to compare distributions across groups or show outlier extent."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "value_column": {
                            "type": "string",
                            "description": "Numeric column to plot",
                        },
                        "group_column": {
                            "type": "string",
                            "description": "Optional categorical column to group boxes",
                        },
                        "title": {"type": "string", "description": "Chart title"},
                    },
                    "required": ["value_column"],
                },
            },
        ]

    # ── Tool dispatch ──────────────────────────────────────────────────────────

    def _execute_tool(self, tool_name: str, tool_input: dict):
        assert self._df is not None
        result = self._call_chart_tool(tool_name, tool_input, self._df)
        # Capture every successful chart for _parse_output
        if isinstance(result, dict) and "plotly_figure" in result:
            self._chart_results.append(result)
        return result

    def _call_chart_tool(self, tool_name: str, tool_input: dict, df: pd.DataFrame):
        if tool_name == "create_bar_chart":
            return create_bar_chart(
                df,
                category_column=tool_input["category_column"],
                value_column=tool_input.get("value_column"),
                title=tool_input.get("title"),
                top_n=tool_input.get("top_n", 15),
            )
        if tool_name == "create_histogram":
            return create_histogram(
                df,
                column=tool_input["column"],
                bins=tool_input.get("bins", 30),
                title=tool_input.get("title"),
            )
        if tool_name == "create_scatter_plot":
            return create_scatter_plot(
                df,
                x_column=tool_input["x_column"],
                y_column=tool_input["y_column"],
                color_column=tool_input.get("color_column"),
                title=tool_input.get("title"),
            )
        if tool_name == "create_correlation_heatmap":
            return create_correlation_heatmap(df, title=tool_input.get("title"))
        if tool_name == "create_line_chart":
            return create_line_chart(
                df,
                x_column=tool_input["x_column"],
                y_columns=tool_input["y_columns"],
                title=tool_input.get("title"),
            )
        if tool_name == "create_box_plot":
            return create_box_plot(
                df,
                value_column=tool_input["value_column"],
                group_column=tool_input.get("group_column"),
                title=tool_input.get("title"),
            )
        return {"error": f"Unknown tool: {tool_name}"}

    # ── Prompt construction ────────────────────────────────────────────────────

    def _build_user_message(self, state: AnalysisState) -> str:
        summary = state["agent_summary"]
        analyst_output = state.get("analyst_output")

        analyst_context = ""
        recommended_charts: list[str] = []

        if analyst_output:
            top_insights = analyst_output.insights[:5]
            insight_lines = "\n".join(
                f"- [{i.category.upper()}] {i.title}: {i.description}"
                for i in top_insights
            )
            top_correlations = analyst_output.correlations[:3]
            corr_lines = "\n".join(
                "  - " + c.column_a + " <-> " + c.column_b
                + ": r=" + f"{c.correlation:.3f}"
                + " -- " + c.interpretation
                for c in top_correlations
            )
            recommended_charts = analyst_output.recommended_visualizations
            rec_str = ", ".join(recommended_charts) if recommended_charts else "bar, histogram, scatter"
            analyst_context = (
                "\n## Analyst Findings\n"
                "### Top Insights\n"
                + insight_lines
                + "\n\n### Top Correlations\n"
                + corr_lines
                + "\n\n### Recommended Chart Types\n"
                + rec_str
                + "\n\n### Anomalies Detected\n"
                + json.dumps(analyst_output.anomalies_detected, indent=2)
                + "\n"
            )

        numeric_cols = [
            c["name"] for c in summary["columns"]
            if c["dtype"] in ("integer", "float", "numeric")
        ]
        categorical_cols = [
            c["name"] for c in summary["columns"]
            if c["dtype"] in ("object", "string", "category")
        ]
        datetime_cols = summary.get("likely_datetime_columns", [])
        chart_rec = ", ".join(recommended_charts) if recommended_charts else "bar, histogram, scatter"

        shape_info = (
            str(summary["shape"]["rows"])
            + " rows x "
            + str(summary["shape"]["columns"])
            + " columns"
        )

        return (
            "Generate 3-6 meaningful visualizations for this dataset.\n\n"
            "## Dataset Overview\n"
            "- Shape: " + shape_info + "\n"
            "- Numeric columns: " + str(numeric_cols) + "\n"
            "- Categorical columns: " + str(categorical_cols) + "\n"
            "- Datetime columns: " + str(datetime_cols) + "\n"
            + analyst_context
            + "\n## Column Details\n"
            + json.dumps(summary["columns"], indent=2)
            + "\n\n## Instructions\n"
            "1. Generate charts that DIRECTLY support the analyst insights above\n"
            "2. Prioritize chart types recommended by the analyst: " + chart_rec + "\n"
            "3. For correlated columns, create a scatter plot\n"
            "4. If datetime columns exist, create a line chart\n"
            "5. Create a correlation heatmap if there are 3+ numeric columns\n"
            "6. Cover both distribution (histogram/box) and relationship (scatter/heatmap) charts\n"
            "7. Each chart must have a specific, insight-driven title -- not generic names\n"
            "8. Vary chart types -- do not create the same type twice unless clearly justified\n\n"
            "After generating all charts, output a JSON summary:\n"
            "```json\n"
            "{\n"
            '  "charts": [\n'
            "    {\n"
            '      "tool_name": "<tool used>",\n'
            '      "title": "<chart title>",\n'
            '      "description": "<what this chart reveals>",\n'
            '      "insight_context": "<which insight or finding this chart supports>"\n'
            "    }\n"
            "  ],\n"
            '  "summary": "<two-sentence summary of the visualization set>"\n'
            "}\n"
            "```\n"
        )

    # ── Output parsing ─────────────────────────────────────────────────────────

    def _parse_output(self, llm_response: LLMResponse, state: AnalysisState) -> VisualizerOutput:
        try:
            data = self._extract_json_from_response(llm_response.content)
        except ValueError:
            data = {}

        chart_meta: list[dict] = data.get("charts", [])

        # self._chart_results was populated by _execute_tool during the tool-use loop
        charts: list[PlotlyChartSpec] = []
        for i, result in enumerate(self._chart_results):
            meta = chart_meta[i] if i < len(chart_meta) else {}
            charts.append(
                PlotlyChartSpec(
                    chart_type=result.get("chart_type", "unknown"),
                    title=result.get("title", meta.get("title", "Chart " + str(i + 1))),
                    description=meta.get("description", result.get("title", "")),
                    columns_used=result.get("columns_used", []),
                    plotly_figure=result["plotly_figure"],
                    insight_context=meta.get("insight_context", ""),
                )
            )

        return VisualizerOutput(
            charts=charts,
            summary=data.get("summary", "Generated " + str(len(charts)) + " visualizations."),
        )

    # ── Main run ───────────────────────────────────────────────────────────────

    async def run(self, state: AnalysisState, bus: EventBus) -> AnalysisState:
        _clean = state.get("clean_df")
        self._df = _clean if _clean is not None else state["raw_df"]
        self._chart_results = []  # Reset for this run

        await self._emit_progress(
            state, "Selecting chart types", "Analyzing insights for visualization", 0.05
        )

        llm_response = await self._run_llm(state)

        await self._emit_progress(
            state, "Rendering charts", "Generating Plotly figures", 0.80
        )

        output = self._parse_output(llm_response, state)
        output._tokens_in = llm_response.tokens_in    # type: ignore[attr-defined]
        output._tokens_out = llm_response.tokens_out  # type: ignore[attr-defined]

        # Emit one SSE event per chart
        for chart in output.charts:
            await bus.emit(
                ChartGeneratedEvent(
                    session_id=state["session_id"],
                    agent_run_id=state.get("visualizer_run_id"),
                    agent_name="visualizer",
                    chart_id=str(uuid.uuid4()),
                    chart_type=chart.chart_type,
                    title=chart.title,
                    columns_used=chart.columns_used,
                )
            )

        await self._emit_progress(
            state, "Done", "Generated " + str(len(output.charts)) + " charts", 1.0
        )

        state["visualizer_output"] = output
        return state
