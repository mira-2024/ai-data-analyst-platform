"""
WorkflowEvent ORM model.

Every significant event during orchestration is persisted here.
This table is the audit log, the replay source, and the SSE feed source.

sequence_num ensures events are ordered correctly even if
timestamps have sub-millisecond ties.

The frontend Agent Timeline UI reads from this table for:
- real-time streaming (via SSE)
- session replay (re-streaming from stored events)
- historical analysis views
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin


class WorkflowEventType(str, Enum):
    # Session lifecycle
    ANALYSIS_STARTED    = "ANALYSIS_STARTED"
    ANALYSIS_COMPLETED  = "ANALYSIS_COMPLETED"
    ANALYSIS_FAILED     = "ANALYSIS_FAILED"
    ANALYSIS_CANCELLED  = "ANALYSIS_CANCELLED"

    # Agent lifecycle
    AGENT_STARTED       = "AGENT_STARTED"
    AGENT_COMPLETED     = "AGENT_COMPLETED"
    AGENT_FAILED        = "AGENT_FAILED"
    AGENT_SKIPPED       = "AGENT_SKIPPED"
    AGENT_RETRYING      = "AGENT_RETRYING"

    # Tool execution
    TOOL_CALLED         = "TOOL_CALLED"
    TOOL_COMPLETED      = "TOOL_COMPLETED"
    TOOL_FAILED         = "TOOL_FAILED"

    # Progress signals
    ANALYSIS_PROGRESS   = "ANALYSIS_PROGRESS"

    # Outputs
    CHART_GENERATED     = "CHART_GENERATED"
    REPORT_CREATED      = "REPORT_CREATED"
    INSIGHT_GENERATED   = "INSIGHT_GENERATED"
    CLEANING_COMPLETED  = "CLEANING_COMPLETED"


class WorkflowEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "workflow_events"

    # No TimestampMixin — we use a single emitted_at for query efficiency

    # ── Foreign keys ──────────────────────────────────────────────────────────
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analysis_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ── Event identity ────────────────────────────────────────────────────────
    event_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    agent_name: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="Which agent emitted this event (null for session-level events)",
    )

    # ── Ordering ──────────────────────────────────────────────────────────────
    sequence_num: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="Monotonically increasing per session — guarantees order",
    )
    emitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    # ── Payload ───────────────────────────────────────────────────────────────
    # Event-type-specific data. Schema enforced at application level (not DB).
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Structured event payload, schema varies by event_type",
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    session: Mapped["AnalysisSession"] = relationship(  # noqa: F821
        "AnalysisSession",
        back_populates="workflow_events",
        lazy="select",
    )
    agent_run: Mapped["AgentRun | None"] = relationship(  # noqa: F821
        "AgentRun",
        back_populates="workflow_events",
        lazy="select",
    )

    # ── Composite indexes for common queries ──────────────────────────────────
    __table_args__ = (
        # Replaying all events for a session in order
        Index(
            "ix_workflow_events_session_seq",
            "session_id",
            "sequence_num",
        ),
        # Filtering by event type within a session
        Index(
            "ix_workflow_events_session_type",
            "session_id",
            "event_type",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<WorkflowEvent type={self.event_type} "
            f"agent={self.agent_name} seq={self.sequence_num}>"
        )
