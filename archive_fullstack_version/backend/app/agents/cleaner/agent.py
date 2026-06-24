"""
CleanerAgent — data cleaning and validation.

Receives the raw dataset summary, uses tools to clean the DataFrame,
and returns a structured CleanerOutput with full audit trail.

The cleaned DataFrame is stored back in state.clean_df for downstream agents.
"""

from __future__ import annotations

import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base_agent import BaseAgent
from app.agents.cleaner.tools import DataFrameContainer, drop_duplicates, fix_dtype
from app.agents.cleaner.tools import handle_outliers, impute_missing, normalize_column
from app.agents.cleaner.tools import validate_schema
from app.agents.llm_client import LLMResponse, ToolDefinition
from app.models.execution_trace import TraceStepType
from app.orchestration.event_bus import EventBus
from app.orchestration.events import CleaningCompletedEvent
from app.orchestration.state import AnalysisState
from app.schemas.agent import CleanerOutput, CleaningAction


class CleanerAgent(BaseAgent):
    agent_name = "cleaner"

    def __init__(self, bus: EventBus, db: AsyncSession) -> None:
        super().__init__(bus=bus, db=db)
        self._container: DataFrameContainer | None = None

    # ── Tool definitions ──────────────────────────────────────────────────────

    def _get_tools(self) -> list[ToolDefinition]:
        return [
            {
                "name": "impute_missing",
                "description": "Impute missing values in a column using a specified strategy.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string", "description": "Column name to impute"},
                        "strategy": {
                            "type": "string",
                            "enum": ["mean", "median", "mode", "ffill", "bfill", "drop"],
                            "description": "Imputation strategy to use",
                        },
                    },
                    "required": ["column", "strategy"],
                },
            },
            {
                "name": "drop_duplicates",
                "description": "Remove duplicate rows from the dataset.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "subset": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Columns to check for duplicates. Leave empty to check all columns.",
                        },
                    },
                },
            },
            {
                "name": "fix_dtype",
                "description": "Convert a column to the correct data type.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string", "description": "Column name"},
                        "target_dtype": {
                            "type": "string",
                            "enum": ["numeric", "datetime", "string", "boolean", "category"],
                            "description": "Target data type",
                        },
                    },
                    "required": ["column", "target_dtype"],
                },
            },
            {
                "name": "handle_outliers",
                "description": "Detect and handle outliers in a numeric column.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string", "description": "Numeric column name"},
                        "method": {
                            "type": "string",
                            "enum": ["iqr", "zscore"],
                            "description": "Detection method: IQR (interquartile range) or Z-score (3 sigma)",
                        },
                        "action": {
                            "type": "string",
                            "enum": ["cap", "drop", "flag"],
                            "description": "cap=winsorize to bounds, drop=remove rows, flag=add boolean column",
                        },
                    },
                    "required": ["column", "method", "action"],
                },
            },
            {
                "name": "normalize_column",
                "description": "Normalize or standardize a numeric column.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string", "description": "Numeric column name"},
                        "method": {
                            "type": "string",
                            "enum": ["minmax", "zscore"],
                            "description": "minmax=scale to [0,1], zscore=standardize to mean=0 std=1",
                        },
                    },
                    "required": ["column", "method"],
                },
            },
            {
                "name": "validate_schema",
                "description": "Validate the final cleaned dataset and produce a quality report. Call this last.",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                },
            },
        ]

    def _execute_tool(self, tool_name: str, tool_input: dict) -> dict:
        """Dispatch tool calls to the implementation functions."""
        assert self._container is not None, "Container not initialized"
        c = self._container

        if tool_name == "impute_missing":
            return impute_missing(c, **tool_input)
        if tool_name == "drop_duplicates":
            return drop_duplicates(c, subset=tool_input.get("subset") or None)
        if tool_name == "fix_dtype":
            return fix_dtype(c, **tool_input)
        if tool_name == "handle_outliers":
            return handle_outliers(c, **tool_input)
        if tool_name == "normalize_column":
            return normalize_column(c, **tool_input)
        if tool_name == "validate_schema":
            return validate_schema(c)

        return {"error": f"Unknown tool: {tool_name}"}

    def _build_user_message(self, state: AnalysisState) -> str:
        summary = state["agent_summary"]
        config = state.get("config", {})
        focus = config.get("focus_areas", [])
        custom = config.get("custom_instructions", "")

        msg = f"""You are cleaning the following dataset. Use the available tools to systematically clean it.

## Dataset Summary
- Shape: {summary['shape']['rows']} rows × {summary['shape']['columns']} columns
- Overall null rate: {summary['overall_null_rate_pct']}%
- Likely categorical columns: {summary['likely_categorical_columns']}
- Likely datetime columns: {summary['likely_datetime_columns']}

## Column Details
{json.dumps(summary['columns'], indent=2)}

## Sample Rows
{json.dumps(summary['sample_rows'], indent=2)}
"""
        if focus:
            msg += f"\n## Focus Areas\nPay special attention to: {', '.join(focus)}\n"
        if custom:
            msg += f"\n## Additional Instructions\n{custom}\n"

        msg += """
## Task
1. Use the tools to clean this dataset systematically
2. Start with fix_dtype for any obvious type issues
3. Then impute_missing for each column with missing values
4. Then drop_duplicates
5. Then handle_outliers for numeric columns with high variance
6. Finally call validate_schema to confirm the cleaned state

After using all tools, produce a CleanerOutput JSON with this exact structure:
```json
{
  "rows_before": <int>,
  "rows_after": <int>,
  "columns_before": <int>,
  "columns_after": <int>,
  "missing_values_imputed": <int>,
  "duplicates_removed": <int>,
  "outliers_handled": <int>,
  "dtype_corrections": <int>,
  "actions": [
    {
      "action_type": <str>,
      "column": <str or null>,
      "description": <str>,
      "rows_affected": <int>,
      "before_value": <any>,
      "after_value": <any>
    }
  ],
  "quality_score": <float 0.0-1.0>,
  "summary": <one paragraph plain English summary>,
  "warnings": [<str>]
}
```
"""
        return msg

    def _parse_output(self, llm_response: LLMResponse, state: AnalysisState) -> CleanerOutput:
        """Parse LLM JSON response into CleanerOutput, with container data as fallback."""
        assert self._container is not None

        try:
            data = self._extract_json_from_response(llm_response.content)
        except ValueError:
            # Fallback: reconstruct from container state
            data = self._build_fallback_output(state)

        # Merge container actions if LLM omitted them
        if not data.get("actions") and self._container.actions:
            data["actions"] = self._container.actions

        if not data.get("warnings"):
            data["warnings"] = self._container.warnings

        actions = [CleaningAction(**a) for a in data.get("actions", [])]

        return CleanerOutput(
            rows_before=data.get("rows_before", state["agent_summary"]["shape"]["rows"]),
            rows_after=data.get("rows_after", len(self._container.df)),
            columns_before=data.get("columns_before", state["agent_summary"]["shape"]["columns"]),
            columns_after=data.get("columns_after", len(self._container.df.columns)),
            missing_values_imputed=data.get("missing_values_imputed", 0),
            duplicates_removed=data.get("duplicates_removed", 0),
            outliers_handled=data.get("outliers_handled", 0),
            dtype_corrections=data.get("dtype_corrections", 0),
            actions=actions,
            quality_score=max(0.0, min(1.0, float(data.get("quality_score", 0.8)))),
            summary=data.get("summary", "Dataset cleaned successfully."),
            warnings=data.get("warnings", []),
        )

    def _build_fallback_output(self, state: AnalysisState) -> dict:
        assert self._container is not None
        c = self._container
        rows_before = state["agent_summary"]["shape"]["rows"]
        return {
            "rows_before": rows_before,
            "rows_after": len(c.df),
            "columns_before": state["agent_summary"]["shape"]["columns"],
            "columns_after": len(c.df.columns),
            "missing_values_imputed": sum(
                a["rows_affected"] for a in c.actions if a["action_type"] == "impute_missing"
            ),
            "duplicates_removed": sum(
                a["rows_affected"] for a in c.actions if a["action_type"] == "drop_duplicates"
            ),
            "outliers_handled": sum(
                a["rows_affected"] for a in c.actions if a["action_type"] == "handle_outliers"
            ),
            "dtype_corrections": sum(
                1 for a in c.actions if a["action_type"] == "fix_dtype"
            ),
            "actions": c.actions,
            "quality_score": 0.8,
            "summary": f"Cleaned dataset: {len(c.actions)} actions applied.",
            "warnings": c.warnings,
        }

    # ── Main entry point ──────────────────────────────────────────────────────

    async def run(self, state: AnalysisState, bus: EventBus) -> AnalysisState:
        """Execute cleaning pipeline and return updated state."""
        raw_df = state["raw_df"]
        rows_before = len(raw_df)

        # Initialize the mutable container
        self._container = DataFrameContainer(raw_df)

        await self._emit_progress(state, "Initializing", "Preparing dataset for cleaning", 0.05)

        # Run LLM tool-use loop
        llm_response = await self._run_llm(state)

        await self._emit_progress(state, "Finalizing", "Building cleaning report", 0.9)

        # Parse structured output
        output = self._parse_output(llm_response, state)

        # Attach token counts to output (for runner)
        output._tokens_in = llm_response.tokens_in  # type: ignore[attr-defined]
        output._tokens_out = llm_response.tokens_out  # type: ignore[attr-defined]

        # Emit cleaning completion event
        await bus.emit(CleaningCompletedEvent(
            session_id=state["session_id"],
            agent_run_id=state.get("cleaner_run_id"),
            agent_name="cleaner",
            rows_before=rows_before,
            rows_after=output.rows_after,
            columns_fixed=output.dtype_corrections,
            missing_values_imputed=output.missing_values_imputed,
            outliers_handled=output.outliers_handled,
            summary=output.summary,
        ))

        await self._write_trace(
            agent_run_id=state.get("cleaner_run_id"),
            step_type=TraceStepType.STATE_WRITE,
            step_name="write_clean_df",
            summary=f"Wrote cleaned DataFrame: {output.rows_after} rows",
        )

        await self._emit_progress(state, "Done", "Cleaning complete", 1.0)

        # Update state with cleaned DataFrame and output
        state["clean_df"] = self._container.df
        state["cleaner_output"] = output

        return state
