"""
ORM model registry.

Import all models here so Alembic's env.py can discover them
via `Base.metadata` without manually listing every file.

Import order matters for FK resolution — parents before children.
"""

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.dataset import Dataset, DatasetStatus
from app.models.analysis_session import AnalysisSession, SessionStatus
from app.models.agent_run import AgentRun, AgentName, AgentRunStatus
from app.models.workflow_event import WorkflowEvent, WorkflowEventType
from app.models.report import Report
from app.models.chart_config import ChartConfig, ChartType
from app.models.execution_trace import ExecutionTrace, TraceStepType

__all__ = [
    # Base
    "Base",
    "TimestampMixin",
    "UUIDPrimaryKeyMixin",
    # Models
    "Dataset",
    "DatasetStatus",
    "AnalysisSession",
    "SessionStatus",
    "AgentRun",
    "AgentName",
    "AgentRunStatus",
    "WorkflowEvent",
    "WorkflowEventType",
    "Report",
    "ChartConfig",
    "ChartType",
    "ExecutionTrace",
    "TraceStepType",
]
