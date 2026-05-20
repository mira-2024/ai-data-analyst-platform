"""
Analysis session Pydantic schemas.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AnalysisConfig(BaseModel):
    """User-provided configuration when starting an analysis."""
    focus_areas: list[str] = Field(
        default_factory=list,
        description="Optional: specific columns or questions to focus on",
    )
    run_cleaner: bool = True
    run_analyst: bool = True
    run_visualizer: bool = True
    run_storyteller: bool = True
    custom_instructions: str | None = None


class StartAnalysisRequest(BaseModel):
    dataset_id: uuid.UUID
    config: AnalysisConfig = Field(default_factory=AnalysisConfig)


class AgentRunSummary(BaseModel):
    id: uuid.UUID
    agent_name: str
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    duration_ms: int | None
    tokens_input: int
    tokens_output: int
    retry_count: int
    error_message: str | None = None

    model_config = {"from_attributes": True}


class AnalysisSessionResponse(BaseModel):
    id: uuid.UUID
    dataset_id: uuid.UUID
    status: str
    config_json: dict[str, Any]
    started_at: datetime | None
    completed_at: datetime | None
    total_tokens_used: int
    total_duration_seconds: int | None
    agent_count_completed: int
    agent_count_failed: int
    error_message: str | None = None
    agent_runs: list[AgentRunSummary] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AnalysisSessionListResponse(BaseModel):
    items: list[AnalysisSessionResponse]
    total: int
