"""Report and chart Pydantic schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ChartConfigResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    title: str
    description: str | None
    chart_type: str
    plotly_config: dict[str, Any]
    columns_used: list[str]
    insight_context: str | None
    display_order: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ReportResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    title: str
    executive_summary: str | None
    narrative_json: list[dict[str, Any]]
    insights_json: list[dict[str, Any]]
    recommendations_json: list[dict[str, Any]]
    cleaning_summary_json: dict[str, Any] | None
    statistical_highlights_json: dict[str, Any] | None
    file_key: str | None
    charts: list[ChartConfigResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
