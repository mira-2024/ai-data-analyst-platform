"""Initial schema — all tables

Revision ID: 0001
Revises:
Create Date: 2026-01-01 00:00:00.000000

Creates all tables for the Multi-Agent Data Analyst platform:
- datasets
- analysis_sessions
- agent_runs
- workflow_events
- reports
- chart_configs
- execution_traces
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── datasets ──────────────────────────────────────────────────────────────
    op.create_table(
        "datasets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("original_filename", sa.String(512), nullable=False),
        sa.Column("file_key", sa.String(1024), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("mime_type", sa.String(128), nullable=False),
        sa.Column("file_extension", sa.String(16), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.Column("column_count", sa.Integer(), nullable=True),
        sa.Column("schema_json", postgresql.JSONB(), nullable=True),
        sa.Column("preview_json", postgresql.JSONB(), nullable=True),
        sa.Column("statistics_json", postgresql.JSONB(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("file_key"),
    )
    op.create_index("ix_datasets_id", "datasets", ["id"])
    op.create_index("ix_datasets_status", "datasets", ["status"])
    op.create_index("ix_datasets_created_at", "datasets", ["created_at"])

    # ── analysis_sessions ─────────────────────────────────────────────────────
    op.create_table(
        "analysis_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("config_json", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_tokens_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_duration_seconds", sa.Integer(), nullable=True),
        sa.Column("agent_count_completed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("agent_count_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id"], ["datasets.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_analysis_sessions_id", "analysis_sessions", ["id"])
    op.create_index("ix_analysis_sessions_dataset_id", "analysis_sessions", ["dataset_id"])
    op.create_index("ix_analysis_sessions_status", "analysis_sessions", ["status"])
    op.create_index("ix_analysis_sessions_created_at", "analysis_sessions", ["created_at"])

    # ── agent_runs ────────────────────────────────────────────────────────────
    op.create_table(
        "agent_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_name", sa.String(64), nullable=False),
        sa.Column("agent_version", sa.String(32), nullable=False, server_default="1.0.0"),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("tokens_input", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tokens_output", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("llm_model", sa.String(128), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("input_summary_json", postgresql.JSONB(), nullable=True),
        sa.Column("output_json", postgresql.JSONB(), nullable=True),
        sa.Column("error_type", sa.String(128), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("error_traceback", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["session_id"], ["analysis_sessions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_runs_id", "agent_runs", ["id"])
    op.create_index("ix_agent_runs_session_id", "agent_runs", ["session_id"])
    op.create_index("ix_agent_runs_agent_name", "agent_runs", ["agent_name"])
    op.create_index("ix_agent_runs_status", "agent_runs", ["status"])

    # ── workflow_events ───────────────────────────────────────────────────────
    op.create_table(
        "workflow_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("agent_name", sa.String(64), nullable=True),
        sa.Column("sequence_num", sa.BigInteger(), nullable=False),
        sa.Column("emitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.ForeignKeyConstraint(
            ["session_id"], ["analysis_sessions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["agent_run_id"], ["agent_runs.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workflow_events_id", "workflow_events", ["id"])
    op.create_index("ix_workflow_events_session_id", "workflow_events", ["session_id"])
    op.create_index("ix_workflow_events_agent_run_id", "workflow_events", ["agent_run_id"])
    op.create_index("ix_workflow_events_event_type", "workflow_events", ["event_type"])
    op.create_index("ix_workflow_events_emitted_at", "workflow_events", ["emitted_at"])
    op.create_index(
        "ix_workflow_events_session_seq",
        "workflow_events",
        ["session_id", "sequence_num"],
    )
    op.create_index(
        "ix_workflow_events_session_type",
        "workflow_events",
        ["session_id", "event_type"],
    )

    # ── reports ───────────────────────────────────────────────────────────────
    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("executive_summary", sa.Text(), nullable=True),
        sa.Column("narrative_json", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("insights_json", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("recommendations_json", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("cleaning_summary_json", postgresql.JSONB(), nullable=True),
        sa.Column("statistical_highlights_json", postgresql.JSONB(), nullable=True),
        sa.Column("file_key", sa.String(1024), nullable=True),
        sa.Column("file_mime_type", sa.String(128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["session_id"], ["analysis_sessions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id"),
    )
    op.create_index("ix_reports_id", "reports", ["id"])
    op.create_index("ix_reports_session_id", "reports", ["session_id"])

    # ── chart_configs ─────────────────────────────────────────────────────────
    op.create_table(
        "chart_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("description", sa.String(1024), nullable=True),
        sa.Column("chart_type", sa.String(64), nullable=False),
        sa.Column("plotly_config", postgresql.JSONB(), nullable=False),
        sa.Column("columns_used", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("insight_context", sa.String(1024), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("image_file_key", sa.String(1024), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["session_id"], ["analysis_sessions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["agent_run_id"], ["agent_runs.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chart_configs_id", "chart_configs", ["id"])
    op.create_index("ix_chart_configs_session_id", "chart_configs", ["session_id"])
    op.create_index("ix_chart_configs_chart_type", "chart_configs", ["chart_type"])

    # ── execution_traces ──────────────────────────────────────────────────────
    op.create_table(
        "execution_traces",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("step_type", sa.String(64), nullable=False),
        sa.Column("step_name", sa.String(255), nullable=False),
        sa.Column("tool_name", sa.String(128), nullable=True),
        sa.Column("sequence_num", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("input_json", postgresql.JSONB(), nullable=True),
        sa.Column("output_json", postgresql.JSONB(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["agent_run_id"], ["agent_runs.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_execution_traces_id", "execution_traces", ["id"])
    op.create_index("ix_execution_traces_agent_run_id", "execution_traces", ["agent_run_id"])
    op.create_index("ix_execution_traces_step_type", "execution_traces", ["step_type"])


def downgrade() -> None:
    op.drop_table("execution_traces")
    op.drop_table("chart_configs")
    op.drop_table("reports")
    op.drop_table("workflow_events")
    op.drop_table("agent_runs")
    op.drop_table("analysis_sessions")
    op.drop_table("datasets")
