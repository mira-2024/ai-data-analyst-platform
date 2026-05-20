"""
Workflow event schema.

Every event emitted during agent execution must conform to one of these
typed Pydantic models. This is the contract between:
  - Orchestration engine (producer)
  - EventBus (transport)
  - DB persister (consumer)
  - SSE broadcaster (consumer)
  - Frontend (final consumer, via SSE JSON)

New event types are added here first, then handled in subscribers.
Never pass raw dicts between orchestration and transport layers.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


# ── Base event ────────────────────────────────────────────────────────────────

class BaseWorkflowEvent(BaseModel):
    """All workflow events share this envelope."""
    event_id: str = Field(default_factory=_uuid)
    session_id: str
    agent_run_id: str | None = None
    agent_name: str | None = None
    emitted_at: datetime = Field(default_factory=_now)
    sequence_num: int = 0  # Set by EventBus before dispatch

    def to_sse_dict(self) -> dict[str, Any]:
        """Serialize for SSE transmission (camelCase for frontend)."""
        return self.model_dump(mode="json")


# ── Session lifecycle events ──────────────────────────────────────────────────

class AnalysisStartedEvent(BaseWorkflowEvent):
    event_type: Literal["ANALYSIS_STARTED"] = "ANALYSIS_STARTED"
    dataset_id: str
    dataset_name: str
    agents_planned: list[str]


class AnalysisCompletedEvent(BaseWorkflowEvent):
    event_type: Literal["ANALYSIS_COMPLETED"] = "ANALYSIS_COMPLETED"
    duration_seconds: float
    total_tokens_used: int
    agents_completed: int
    agents_failed: int


class AnalysisFailedEvent(BaseWorkflowEvent):
    event_type: Literal["ANALYSIS_FAILED"] = "ANALYSIS_FAILED"
    error_message: str
    error_type: str


class AnalysisCancelledEvent(BaseWorkflowEvent):
    event_type: Literal["ANALYSIS_CANCELLED"] = "ANALYSIS_CANCELLED"
    reason: str | None = None


# ── Agent lifecycle events ────────────────────────────────────────────────────

class AgentStartedEvent(BaseWorkflowEvent):
    event_type: Literal["AGENT_STARTED"] = "AGENT_STARTED"
    agent_name: str
    agent_version: str
    description: str  # Human-readable "what this agent will do"


class AgentCompletedEvent(BaseWorkflowEvent):
    event_type: Literal["AGENT_COMPLETED"] = "AGENT_COMPLETED"
    agent_name: str
    duration_ms: int
    tokens_input: int
    tokens_output: int
    output_preview: dict[str, Any]  # Compact summary for UI


class AgentFailedEvent(BaseWorkflowEvent):
    event_type: Literal["AGENT_FAILED"] = "AGENT_FAILED"
    agent_name: str
    error_type: str
    error_message: str
    retry_count: int
    will_retry: bool


class AgentRetryingEvent(BaseWorkflowEvent):
    event_type: Literal["AGENT_RETRYING"] = "AGENT_RETRYING"
    agent_name: str
    retry_num: int
    max_retries: int
    delay_seconds: float
    reason: str


class AgentSkippedEvent(BaseWorkflowEvent):
    event_type: Literal["AGENT_SKIPPED"] = "AGENT_SKIPPED"
    agent_name: str
    reason: str


# ── Tool execution events ─────────────────────────────────────────────────────

class ToolCalledEvent(BaseWorkflowEvent):
    event_type: Literal["TOOL_CALLED"] = "TOOL_CALLED"
    tool_name: str
    input_preview: dict[str, Any]  # Truncated input for UI display


class ToolCompletedEvent(BaseWorkflowEvent):
    event_type: Literal["TOOL_COMPLETED"] = "TOOL_COMPLETED"
    tool_name: str
    duration_ms: int
    output_preview: dict[str, Any]


class ToolFailedEvent(BaseWorkflowEvent):
    event_type: Literal["TOOL_FAILED"] = "TOOL_FAILED"
    tool_name: str
    error_message: str


# ── Progress & output events ──────────────────────────────────────────────────

class AnalysisProgressEvent(BaseWorkflowEvent):
    event_type: Literal["ANALYSIS_PROGRESS"] = "ANALYSIS_PROGRESS"
    agent_name: str
    step: str          # e.g. "Imputing missing values"
    progress: float    # 0.0 → 1.0
    message: str


class ChartGeneratedEvent(BaseWorkflowEvent):
    event_type: Literal["CHART_GENERATED"] = "CHART_GENERATED"
    chart_id: str
    chart_type: str
    title: str
    columns_used: list[str]


class InsightGeneratedEvent(BaseWorkflowEvent):
    event_type: Literal["INSIGHT_GENERATED"] = "INSIGHT_GENERATED"
    title: str
    description: str
    category: str
    confidence: float


class CleaningCompletedEvent(BaseWorkflowEvent):
    event_type: Literal["CLEANING_COMPLETED"] = "CLEANING_COMPLETED"
    rows_before: int
    rows_after: int
    columns_fixed: int
    missing_values_imputed: int
    outliers_handled: int
    summary: str


class ReportCreatedEvent(BaseWorkflowEvent):
    event_type: Literal["REPORT_CREATED"] = "REPORT_CREATED"
    report_id: str
    title: str
    insight_count: int
    recommendation_count: int
    chart_count: int


# ── Union type for typed dispatch ─────────────────────────────────────────────

WorkflowEvent = (
    AnalysisStartedEvent
    | AnalysisCompletedEvent
    | AnalysisFailedEvent
    | AnalysisCancelledEvent
    | AgentStartedEvent
    | AgentCompletedEvent
    | AgentFailedEvent
    | AgentRetryingEvent
    | AgentSkippedEvent
    | ToolCalledEvent
    | ToolCompletedEvent
    | ToolFailedEvent
    | AnalysisProgressEvent
    | ChartGeneratedEvent
    | InsightGeneratedEvent
    | CleaningCompletedEvent
    | ReportCreatedEvent
)
