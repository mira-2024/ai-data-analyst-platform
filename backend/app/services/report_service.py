"""
ReportService — report retrieval and management.

Reports are created by the StorytellerAgent during orchestration.
This service provides read access and future export capabilities.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ReportNotFoundError, AnalysisSessionNotFoundError
from app.core.logging import get_logger
from app.models.report import Report
from app.models.chart_config import ChartConfig
from app.models.analysis_session import AnalysisSession

logger = get_logger(__name__)


class ReportService:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_session(self, session_id: uuid.UUID) -> Report:
        """
        Fetch the report for an analysis session, including all chart configs.
        """
        # Verify session exists
        session_result = await self.db.execute(
            select(AnalysisSession).where(AnalysisSession.id == session_id)
        )
        if not session_result.scalar_one_or_none():
            raise AnalysisSessionNotFoundError(session_id=str(session_id))

        # Fetch report with charts
        result = await self.db.execute(
            select(Report).where(Report.session_id == session_id)
        )
        report = result.scalar_one_or_none()
        if report is None:
            raise ReportNotFoundError(report_id=f"session:{session_id}")

        # Load charts separately (avoid lazy load issues)
        charts_result = await self.db.execute(
            select(ChartConfig)
            .where(ChartConfig.session_id == session_id)
            .order_by(ChartConfig.display_order)
        )
        # Attach charts manually for the response schema
        report.__dict__["_charts"] = list(charts_result.scalars().all())

        return report

    async def create_report(
        self,
        session_id: uuid.UUID,
        agent_run_id: uuid.UUID | None,
        storyteller_output: "StorytellerOutput",  # noqa: F821
        chart_specs: list["PlotlyChartSpec"],       # noqa: F821
    ) -> Report:
        """
        Persist the StorytellerAgent output as a Report record.
        Called by the orchestration runner after the storyteller completes.
        """
        from app.models.chart_config import ChartConfig

        # Create report
        report = Report(
            session_id=session_id,
            title=storyteller_output.title,
            executive_summary=storyteller_output.executive_summary,
            narrative_json=[b.model_dump() for b in storyteller_output.narrative_blocks],
            insights_json=[],           # Populated from analyst output
            recommendations_json=[
                r.model_dump() for r in storyteller_output.recommendations
            ],
        )
        self.db.add(report)
        await self.db.flush()

        # Create chart configs
        for i, chart_spec in enumerate(chart_specs):
            chart = ChartConfig(
                session_id=session_id,
                agent_run_id=agent_run_id,
                title=chart_spec.title,
                description=chart_spec.description,
                chart_type=chart_spec.chart_type,
                plotly_config=chart_spec.plotly_figure,
                columns_used=chart_spec.columns_used,
                insight_context=chart_spec.insight_context,
                display_order=i,
            )
            self.db.add(chart)

        await self.db.flush()

        logger.info(
            "report_created",
            session_id=str(session_id),
            report_id=str(report.id),
            chart_count=len(chart_specs),
        )

        return report
