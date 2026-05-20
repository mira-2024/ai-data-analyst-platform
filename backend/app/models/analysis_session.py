"""
AnalysisSession ORM model.

One session = one full multi-agent analysis run on a dataset.
A dataset can have many sessions (re-analysis, different configs).

Stores the full lifecycle: config → running → completed/failed.
Supports session replay via agent_runs and workflow_events relationships.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SessionStatus(str, Enum):
    PENDING = "pending"        # Created, not yet started
    RUNNING = "running"        # Orchestration in progress
    COMPLETED = "completed"    # All agents finished successfully
    FAILED = "failed"          # Unrecoverable failure
    CANCELLED = "cancelled"    # User-cancelled


class AnalysisSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "analysis_sessions"

    # ── Foreign keys ──────────────────────────────────────────────────────────
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Status ────────────────────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=SessionStatus.PENDING,
        index=True,
    )

    # ── Configuration ─────────────────────────────────────────────────────────
    # Analysis config provided by user (which agents to run, focus areas, etc.)
    config_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="User-provided analysis configuration",
    )

    # ── Timing ────────────────────────────────────────────────────────────────
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ── Derived metrics ───────────────────────────────────────────────────────
    total_tokens_used: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Cumulative LLM tokens across all agent runs",
    )
    total_duration_seconds: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    agent_count_completed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    agent_count_failed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # ── Error ─────────────────────────────────────────────────────────────────
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Future: user ownership (auth-ready) ───────────────────────────────────
    # owner_id: Mapped[uuid.UUID | None] = mapped_column(...)

    # ── Relationships ─────────────────────────────────────────────────────────
    dataset: Mapped["Dataset"] = relationship(  # noqa: F821
        "Dataset",
        back_populates="analysis_sessions",
        lazy="select",
    )
    agent_runs: Mapped[list["AgentRun"]] = relationship(  # noqa: F821
        "AgentRun",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="AgentRun.started_at",
        lazy="select",
    )
    workflow_events: Mapped[list["WorkflowEvent"]] = relationship(  # noqa: F821
        "WorkflowEvent",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="WorkflowEvent.sequence_num",
        lazy="select",
    )
    report: Mapped["Report | None"] = relationship(  # noqa: F821
        "Report",
        back_populates="session",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="select",
    )
    chart_configs: Mapped[list["ChartConfig"]] = relationship(  # noqa: F821
        "ChartConfig",
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return (
            f"<AnalysisSession id={self.id} "
            f"dataset_id={self.dataset_id} status={self.status}>"
        )
