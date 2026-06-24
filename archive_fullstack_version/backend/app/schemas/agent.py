"""
Agent output Pydantic schemas.

These are the STRUCTURED OUTPUTS each agent must return.
Every agent's run() method returns one of these models.
They are serialized to agent_runs.output_json in the DB.

These schemas define the contract between agents and downstream consumers
(next agents in the pipeline, report generator, frontend).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ── Cleaner Agent Output ──────────────────────────────────────────────────────

class CleaningAction(BaseModel):
    """A single cleaning action taken on the dataset."""
    action_type: str          # e.g. "impute_mean", "drop_duplicates", "fix_dtype"
    column: str | None        # Affected column (None for row-level actions)
    description: str          # Human-readable explanation
    rows_affected: int
    before_value: Any = None  # Example value before cleaning
    after_value: Any = None   # Example value after cleaning


class CleanerOutput(BaseModel):
    """Structured output from the CleanerAgent."""
    rows_before: int
    rows_after: int
    columns_before: int
    columns_after: int
    missing_values_imputed: int
    duplicates_removed: int
    outliers_handled: int
    dtype_corrections: int
    actions: list[CleaningAction] = Field(default_factory=list)
    quality_score: float = Field(ge=0.0, le=1.0)  # 0 = bad, 1 = clean
    summary: str  # One-paragraph human-readable summary
    warnings: list[str] = Field(default_factory=list)


# ── Analyst Agent Output ──────────────────────────────────────────────────────

class Insight(BaseModel):
    title: str
    description: str
    category: str             # "correlation", "anomaly", "trend", "distribution", etc.
    confidence: float = Field(ge=0.0, le=1.0)
    columns_involved: list[str]
    supporting_statistics: dict[str, Any] = Field(default_factory=dict)
    importance: str           # "high" | "medium" | "low"


class CorrelationResult(BaseModel):
    column_a: str
    column_b: str
    correlation: float
    interpretation: str


class AnalystOutput(BaseModel):
    """Structured output from the AnalystAgent."""
    insights: list[Insight] = Field(default_factory=list)
    correlations: list[CorrelationResult] = Field(default_factory=list)
    anomalies_detected: list[dict[str, Any]] = Field(default_factory=list)
    hypothesis: list[str] = Field(default_factory=list)  # Testable hypotheses
    key_statistics: dict[str, Any] = Field(default_factory=dict)
    recommended_visualizations: list[str] = Field(
        default_factory=list,
        description="Chart types the VisualizerAgent should create",
    )
    summary: str


# ── Visualizer Agent Output ───────────────────────────────────────────────────

class PlotlyChartSpec(BaseModel):
    chart_type: str
    title: str
    description: str
    columns_used: list[str]
    plotly_figure: dict[str, Any]  # Full Plotly figure dict
    insight_context: str           # Which insight this chart supports


class VisualizerOutput(BaseModel):
    """Structured output from the VisualizerAgent."""
    charts: list[PlotlyChartSpec] = Field(default_factory=list)
    summary: str


# ── Storyteller Agent Output ──────────────────────────────────────────────────

class NarrativeBlock(BaseModel):
    block_type: str   # "intro", "finding", "recommendation", "conclusion"
    heading: str
    content: str
    importance: str   # "high" | "medium" | "low"


class Recommendation(BaseModel):
    title: str
    action: str
    rationale: str
    priority: str     # "high" | "medium" | "low"
    expected_impact: str


class StorytellerOutput(BaseModel):
    """Structured output from the StorytellerAgent."""
    title: str
    executive_summary: str
    narrative_blocks: list[NarrativeBlock] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    key_takeaways: list[str] = Field(default_factory=list)


# ── Execution trace schema ────────────────────────────────────────────────────

class ExecutionTraceResponse(BaseModel):
    id: str
    step_type: str
    step_name: str
    tool_name: str | None
    sequence_num: int
    duration_ms: int | None
    input_json: dict[str, Any] | None
    output_json: dict[str, Any] | None
    summary: str | None
    error_message: str | None

    model_config = {"from_attributes": True}
