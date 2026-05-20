"""
AgentRun ORM model.

Represents a single agent's execution within an analysis session.
One AnalysisSession has exactly one AgentRun per agent type
(cleaner, analyst, visualizer, storyteller).

Stores the full I/O of each agent for observability, replay, and
token accounting. This is what populates the Agent Timeline UI.
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


class AgentName(str, Enum):
    CLEANER = "cleaner"
    ANALYST = "analyst"
    VISUALIZER = "visualizer"
    STORYTELLER = "storyteller"


class AgentRunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"    # Skipped due to upstream failure


class AgentRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agent_runs"

    # ── Foreign keys ──────────────────────────────────────────────────────────
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analysis_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Identity ──────────────────────────────────────────────────────────────
    agent_name: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="One of: cleaner, analyst, visualizer, storyteller",
    )
    agent_version: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="1.0.0",
        comment="Agent implementation version for audit trail",
    )

    # ── Status & timing ───────────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=AgentRunStatus.PENDING,
        index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── LLM accounting ────────────────────────────────────────────────────────
    tokens_input: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_output: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    llm_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # ── Input / Output ────────────────────────────────────────────────────────
    # Compact summary of what was passed INTO the agent (never full DataFrame)
    input_summary_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Compact representation of agent input state",
    )

    # Full structured output from the agent (Pydantic model serialized)
    output_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Structured agent output (Pydantic schema serialized)",
    )

    # ── Error ─────────────────────────────────────────────────────────────────
    error_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_traceback: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    session: Mapped["AnalysisSession"] = relationship(  # noqa: F821
        "AnalysisSession",
        back_populates="agent_runs",
        lazy="select",
    )
    execution_traces: Mapped[list["ExecutionTrace"]] = relationship(  # noqa: F821
        "ExecutionTrace",
        back_populates="agent_run",
        cascade="all, delete-orphan",
        order_by="ExecutionTrace.created_at",
        lazy="select",
    )
    workflow_events: Mapped[list["WorkflowEvent"]] = relationship(  # noqa: F821
        "WorkflowEvent",
        back_populates="agent_run",
        lazy="select",
    )

    def __repr__(self) -> str:
        return (
            f"<AgentRun id={self.id} agent={self.agent_name} "
            f"status={self.status} duration={self.duration_ms}ms>"
        )
