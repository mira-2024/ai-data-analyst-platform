"""
ExecutionTrace ORM model.

Granular step-by-step trace of what happened inside each AgentRun.
One AgentRun → many ExecutionTraces (one per tool call or reasoning step).

This is the data source for the Agent Trace Viewer page — users can
drill into exactly which tool was called, with what arguments, and
what it returned.

Design principle: traces are append-only. Never update or delete traces.
They are the immutable audit record of what the agent did.
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Any

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class TraceStepType(str, Enum):
    TOOL_CALL        = "tool_call"        # Agent invoked a tool
    TOOL_RESULT      = "tool_result"      # Tool returned a result
    LLM_REASONING    = "llm_reasoning"   # Agent's intermediate reasoning
    STATE_WRITE      = "state_write"      # Agent wrote to shared state
    VALIDATION       = "validation"       # Output validation step
    ERROR            = "error"            # An error occurred


class ExecutionTrace(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "execution_traces"

    # ── Foreign keys ──────────────────────────────────────────────────────────
    agent_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Step identity ─────────────────────────────────────────────────────────
    step_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    step_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Human-readable name e.g. 'impute_missing_values'",
    )
    tool_name: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        comment="Name of the tool function called (null for reasoning steps)",
    )

    # ── Ordering within the agent run ─────────────────────────────────────────
    sequence_num: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Step order within the agent run",
    )

    # ── Timing ────────────────────────────────────────────────────────────────
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── I/O ───────────────────────────────────────────────────────────────────
    input_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Tool call arguments or reasoning input",
    )
    output_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Tool result or reasoning output",
    )

    # Human-readable summary for UI display (avoids parsing full JSON)
    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="One-line human-readable description of this step",
    )

    # ── Error (if step_type == error) ─────────────────────────────────────────
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    agent_run: Mapped["AgentRun"] = relationship(  # noqa: F821
        "AgentRun",
        back_populates="execution_traces",
        lazy="select",
    )

    def __repr__(self) -> str:
        return (
            f"<ExecutionTrace step={self.step_name!r} "
            f"type={self.step_type} seq={self.sequence_num} "
            f"duration={self.duration_ms}ms>"
        )
