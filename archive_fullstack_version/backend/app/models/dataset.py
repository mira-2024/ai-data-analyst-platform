"""
Dataset ORM model.

Represents an uploaded dataset. Separates:
- file metadata (name, size, type)      → PostgreSQL
- file content                           → StorageBackend (local/S3)
- parsed schema and preview              → JSONB columns

The `file_key` column is a logical storage key (e.g. "datasets/uuid/raw.csv"),
not a filesystem path — the StorageService resolves it to an actual location.
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Any

from sqlalchemy import BigInteger, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class DatasetStatus(str, Enum):
    PENDING = "pending"        # Uploaded, not yet profiled
    PROFILING = "profiling"    # Being analyzed for schema/stats
    READY = "ready"            # Available for analysis
    ERROR = "error"            # Failed to process


class Dataset(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "datasets"

    # ── Identity ──────────────────────────────────────────────────────────────
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="User-provided or derived display name",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ── File metadata ─────────────────────────────────────────────────────────
    original_filename: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        comment="Original filename as uploaded by user",
    )
    file_key: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
        unique=True,
        comment="Logical storage key resolved by StorageService",
    )
    file_size_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    mime_type: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    file_extension: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )

    # ── Profiling results ─────────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=DatasetStatus.PENDING,
        index=True,
    )
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    column_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Column schema: [{name, dtype, nullable, unique_count, sample_values}]
    schema_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Detected column schema after profiling",
    )

    # First N rows for preview display in UI
    preview_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="First 10 rows as list of dicts for UI preview",
    )

    # Statistical summary (min/max/mean/std/nulls per column)
    statistics_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Column-level descriptive statistics",
    )

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Future: user ownership (auth-ready) ───────────────────────────────────
    # owner_id: Mapped[uuid.UUID | None] = mapped_column(
    #     UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    # )

    # ── Relationships ─────────────────────────────────────────────────────────
    analysis_sessions: Mapped[list["AnalysisSession"]] = relationship(  # noqa: F821
        "AnalysisSession",
        back_populates="dataset",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return (
            f"<Dataset id={self.id} name={self.name!r} "
            f"status={self.status} rows={self.row_count}>"
        )
