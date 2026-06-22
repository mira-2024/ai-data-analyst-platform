"""
Dataset Pydantic schemas.

Separate schemas for:
- API request bodies (DatasetCreate)
- API responses (DatasetResponse, DatasetListResponse)
- Internal processing (DatasetProfile)

Never expose ORM models directly in API responses.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ColumnSchema(BaseModel):
    name: str
    dtype: str
    nullable: bool
    unique_count: int | None = None
    null_count: int | None = None
    sample_values: list[Any] = Field(default_factory=list)


class ColumnStatistics(BaseModel):
    name: str
    dtype: str
    min: float | str | None = None
    max: float | str | None = None
    mean: float | None = None
    std: float | None = None
    null_pct: float = 0.0
    unique_count: int | None = None


class DatasetProfile(BaseModel):
    """Internal model — result of profiling an uploaded dataset."""
    row_count: int
    column_count: int
    columns: list[ColumnSchema]
    statistics: list[ColumnStatistics]
    preview_rows: list[dict[str, Any]]  # First 10 rows


class DatasetResponse(BaseModel):
    """API response for a single dataset."""
    id: uuid.UUID
    name: str
    description: str | None
    original_filename: str
    file_size_bytes: int
    mime_type: str
    file_extension: str
    status: str
    row_count: int | None
    column_count: int | None
    schema_json: list[dict[str, Any]] | None = None
    preview_json: list[dict[str, Any]] | None = None
    statistics_json: dict[str, Any] | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DatasetListResponse(BaseModel):
    items: list[DatasetResponse]
    total: int
    page: int
    page_size: int


class DatasetUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
