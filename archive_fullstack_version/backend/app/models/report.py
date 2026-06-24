"""
Report ORM model.

One report per AnalysisSession — the final deliverable of the full
multi-agent pipeline. Stores both structured data (JSON) and a
reference to a rendered artifact (PDF/HTML) in object storage.

Structured fields allow the frontend to render an interactive report
without parsing a document. The file_key provides a downloadable version.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Report(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "reports"

    # ── Foreign keys ──────────────────────────────────────────────────────────
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analysis_sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,   # One report per session
        index=True,
    )

    # ── Content ───────────────────────────────────────────────────────────────
    title: Mapped[str] = mapped_column(String(512), nullable=False)

    executive_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Plain-text executive summary from StorytellerAgent",
    )

    # Structured narrative blocks: [{type, heading, content, importance}]
    narrative_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        comment="Ordered narrative sections from StorytellerAgent",
    )

    # Key insights: [{title, description, confidence, category}]
    insights_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    # Business recommendations: [{title, action, priority, rationale}]
    recommendations_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    # Cleaning summary from CleanerAgent
    cleaning_summary_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Statistical highlights from AnalystAgent
    statistical_highlights_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # ── Storage reference ─────────────────────────────────────────────────────
    # Logical key for rendered PDF/HTML artifact in object storage
    file_key: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
        comment="Storage key for rendered PDF report artifact",
    )
    file_mime_type: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    session: Mapped["AnalysisSession"] = relationship(  # noqa: F821
        "AnalysisSession",
        back_populates="report",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Report id={self.id} session_id={self.session_id} title={self.title!r}>"
