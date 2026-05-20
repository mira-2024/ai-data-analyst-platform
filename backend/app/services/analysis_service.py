"""
AnalysisService — orchestration session lifecycle management.

This is the bridge between the HTTP API and the multi-agent orchestration engine.

Flow:
  POST /analysis/start
    → AnalysisService.start()
      → Create AnalysisSession in DB
      → Create EventBus for this session
      → Wire EventPersister subscriber (DB writes)
      → Wire SSE broadcaster (registered later by /stream endpoint)
      → Fire asyncio.create_task(run_orchestration())
      → Return session immediately (status=pending)

  Background:
      run_orchestration()
        → Emits ANALYSIS_STARTED event
        → Runs LangGraph: Cleaner → Analyst → Visualizer → Storyteller
        → Each step emits events → DB + SSE
        → Emits ANALYSIS_COMPLETED / ANALYSIS_FAILED
        → Closes SSE queue
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AnalysisAlreadyRunningError,
    AnalysisSessionNotFoundError,
    DatasetNotFoundError,
)
from app.core.logging import get_logger, session_id_var
from app.models.analysis_session import AnalysisSession, SessionStatus
from app.models.agent_run import AgentRun, AgentName, AgentRunStatus
from app.models.dataset import Dataset, DatasetStatus
from app.orchestration.event_bus import event_bus_registry
from app.orchestration.events import (
    AnalysisStartedEvent,
    AnalysisCompletedEvent,
    AnalysisFailedEvent,
    AnalysisCancelledEvent,
)
from app.schemas.analysis import AnalysisConfig

logger = get_logger(__name__)

# Registry of cancellation tokens for running sessions
_cancel_tokens: dict[str, asyncio.Event] = {}


class AnalysisService:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Start ─────────────────────────────────────────────────────────────────

    async def start(
        self,
        dataset_id: uuid.UUID,
        config: AnalysisConfig,
    ) -> AnalysisSession:
        """
        Create an analysis session and launch orchestration.

        Returns immediately — orchestration runs in background.
        Subscribe to GET /api/v1/stream/{session_id} for live events.
        """
        # Validate dataset exists and is ready
        ds_result = await self.db.execute(
            select(Dataset).where(Dataset.id == dataset_id)
        )
        dataset = ds_result.scalar_one_or_none()
        if dataset is None:
            raise DatasetNotFoundError(dataset_id=str(dataset_id))
        if dataset.status != DatasetStatus.READY:
            from app.core.exceptions import DataProcessingError
            raise DataProcessingError(
                message=f"Dataset is not ready for analysis (status={dataset.status}). "
                        "Wait for profiling to complete."
            )

        # Check no session is already running on this dataset
        running_result = await self.db.execute(
            select(AnalysisSession).where(
                AnalysisSession.dataset_id == dataset_id,
                AnalysisSession.status == SessionStatus.RUNNING,
            )
        )
        if running_result.scalar_one_or_none():
            from app.core.exceptions import AnalysisAlreadyRunningError
            raise AnalysisAlreadyRunningError(session_id="(existing)")

        # Create session record
        session_id = uuid.uuid4()
        session = AnalysisSession(
            id=session_id,
            dataset_id=dataset_id,
            status=SessionStatus.PENDING,
            config_json=config.model_dump(),
        )
        self.db.add(session)

        # Create AgentRun records for each planned agent
        planned_agents = self._planned_agents(config)
        for agent_name in planned_agents:
            agent_run = AgentRun(
                session_id=session_id,
                agent_name=agent_name,
                status=AgentRunStatus.PENDING,
            )
            self.db.add(agent_run)

        await self.db.flush()

        logger.info(
            "analysis_session_created",
            session_id=str(session_id),
            dataset_id=str(dataset_id),
            agents=planned_agents,
        )

        # Register EventBus — must happen before background task starts
        bus = await event_bus_registry.create(str(session_id))

        # Wire EventPersister as first subscriber
        from app.services.event_persister import EventPersister
        persister = EventPersister(session_id=str(session_id))
        bus.subscribe(persister)

        # Launch orchestration (non-blocking)
        cancel_token = asyncio.Event()
        _cancel_tokens[str(session_id)] = cancel_token

        asyncio.create_task(
            self._run_orchestration(
                session_id=session_id,
                dataset_id=dataset_id,
                config=config,
                planned_agents=planned_agents,
                cancel_token=cancel_token,
            ),
            name=f"orchestration-{session_id}",
        )

        await self.db.flush()
        # Re-fetch session with agent_runs eagerly loaded for serialization
        result = await self.db.execute(
            select(AnalysisSession)
            .options(selectinload(AnalysisSession.agent_runs))
            .where(AnalysisSession.id == session_id)
        )
        return result.scalar_one()

    # ── Cancel ────────────────────────────────────────────────────────────────

    async def cancel(self, session_id: uuid.UUID) -> None:
        """Signal a running orchestration to stop."""
        session = await self.get_by_id(session_id)
        if session.status not in (SessionStatus.PENDING, SessionStatus.RUNNING):
            return  # Already done

        token = _cancel_tokens.get(str(session_id))
        if token:
            token.set()

        session.status = SessionStatus.CANCELLED
        session.completed_at = datetime.now(tz=timezone.utc)
        await self.db.flush()

        # Emit cancellation event
        bus = event_bus_registry.get(str(session_id))
        if bus:
            await bus.emit(
                AnalysisCancelledEvent(
                    session_id=str(session_id),
                    reason="User requested cancellation",
                )
            )
            # Close any open SSE queues
            await event_bus_registry.destroy(str(session_id))

        logger.info("analysis_session_cancelled", session_id=str(session_id))

    # ── Queries ───────────────────────────────────────────────────────────────

    async def get_by_id(self, session_id: uuid.UUID) -> AnalysisSession:
        result = await self.db.execute(
            select(AnalysisSession)
            .options(selectinload(AnalysisSession.agent_runs))
            .where(AnalysisSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if session is None:
            raise AnalysisSessionNotFoundError(session_id=str(session_id))
        return session

    async def list_sessions(
        self,
        dataset_id: uuid.UUID | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[AnalysisSession], int]:
        offset = (page - 1) * page_size

        query = select(AnalysisSession).options(
            selectinload(AnalysisSession.agent_runs)
        )
        count_query = select(func.count()).select_from(AnalysisSession)

        if dataset_id:
            query = query.where(AnalysisSession.dataset_id == dataset_id)
            count_query = count_query.where(
                AnalysisSession.dataset_id == dataset_id
            )

        total = (await self.db.execute(count_query)).scalar_one()
        result = await self.db.execute(
            query.order_by(AnalysisSession.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        sessions = list(result.scalars().all())
        return sessions, total

    # ── Orchestration background task ─────────────────────────────────────────

    async def _run_orchestration(
        self,
        session_id: uuid.UUID,
        dataset_id: uuid.UUID,
        config: AnalysisConfig,
        planned_agents: list[str],
        cancel_token: asyncio.Event,
    ) -> None:
        """
        Execute the full multi-agent analysis pipeline.

        This runs entirely in the background — the HTTP request that
        triggered it has already returned. Uses a fresh DB session.
        """
        from app.core.database import get_session

        session_id_str = str(session_id)
        token = session_id_var.set(session_id_str)
        start_time = datetime.now(tz=timezone.utc)

        logger.info("orchestration_starting", session_id=session_id_str)

        async with get_session() as db:
            bus = event_bus_registry.get(session_id_str)
            if bus is None:
                logger.error(
                    "orchestration_no_event_bus",
                    session_id=session_id_str,
                )
                return

            try:
                # Re-fetch dataset within this session's context
                ds_result = await db.execute(
                    select(Dataset).where(Dataset.id == dataset_id)
                )
                dataset = ds_result.scalar_one_or_none()
                if dataset is None:
                    raise DatasetNotFoundError(dataset_id=str(dataset_id))

                # Mark session as running and commit immediately so the
                # frontend's polling queries see RUNNING before agents finish.
                await self._set_session_running(db, session_id, start_time)
                await db.commit()

                # Emit ANALYSIS_STARTED
                await bus.emit(
                    AnalysisStartedEvent(
                        session_id=session_id_str,
                        dataset_id=str(dataset.id),
                        dataset_name=dataset.name,
                        agents_planned=planned_agents,
                    )
                )

                # Load dataset file and build agent summary
                from app.storage import get_storage
                from app.processing.loader import load_from_bytes
                from app.processing.profiler import profile, build_agent_summary

                storage = get_storage()
                raw_data = await storage.retrieve(dataset.file_key)
                df = await asyncio.to_thread(
                    load_from_bytes, raw_data, dataset.original_filename
                )
                dataset_profile = await asyncio.to_thread(profile, df)
                agent_summary = await asyncio.to_thread(
                    build_agent_summary, df, dataset_profile
                )

                # Import and run the orchestration graph
                from app.orchestration.runner import OrchestratorRunner
                runner = OrchestratorRunner(
                    session_id=session_id_str,
                    dataset_id=str(dataset.id),
                    bus=bus,
                    db=db,
                    cancel_token=cancel_token,
                )

                final_state = await runner.run(
                    df=df,
                    agent_summary=agent_summary,
                    config=config,
                )

                # Mark session as completed
                end_time = datetime.now(tz=timezone.utc)
                duration = (end_time - start_time).total_seconds()
                total_tokens = final_state.get("total_tokens_used", 0)

                await self._set_session_completed(
                    db, session_id,
                    end_time=end_time,
                    duration_seconds=int(duration),
                    total_tokens=total_tokens,
                    agents_completed=final_state.get("agents_completed", 0),
                    agents_failed=final_state.get("agents_failed", 0),
                )

                await bus.emit(
                    AnalysisCompletedEvent(
                        session_id=session_id_str,
                        duration_seconds=duration,
                        total_tokens_used=total_tokens,
                        agents_completed=final_state.get("agents_completed", 0),
                        agents_failed=final_state.get("agents_failed", 0),
                    )
                )

                logger.info(
                    "orchestration_completed",
                    session_id=session_id_str,
                    duration_seconds=round(duration, 2),
                    total_tokens=total_tokens,
                )

            except asyncio.CancelledError:
                logger.info("orchestration_cancelled", session_id=session_id_str)
                raise

            except Exception as exc:
                logger.exception(
                    "orchestration_failed",
                    session_id=session_id_str,
                    error=str(exc),
                )
                await self._set_session_failed(db, session_id, error=str(exc))
                await bus.emit(
                    AnalysisFailedEvent(
                        session_id=session_id_str,
                        error_message=str(exc),
                        error_type=type(exc).__name__,
                    )
                )

            finally:
                # Signal SSE clients the stream is done
                for subscriber in getattr(bus, "_subscribers", []):
                    if hasattr(subscriber, "_queue"):
                        await subscriber._queue.close()

                await event_bus_registry.destroy(session_id_str)
                _cancel_tokens.pop(session_id_str, None)
                session_id_var.reset(token)

    # ── DB helpers ────────────────────────────────────────────────────────────

    @staticmethod
    async def _set_session_running(
        db: AsyncSession,
        session_id: uuid.UUID,
        start_time: datetime,
    ) -> None:
        result = await db.execute(
            select(AnalysisSession).where(AnalysisSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if session:
            session.status = SessionStatus.RUNNING
            session.started_at = start_time

    @staticmethod
    async def _set_session_completed(
        db: AsyncSession,
        session_id: uuid.UUID,
        end_time: datetime,
        duration_seconds: int,
        total_tokens: int,
        agents_completed: int,
        agents_failed: int,
    ) -> None:
        result = await db.execute(
            select(AnalysisSession).where(AnalysisSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if session:
            session.status = SessionStatus.COMPLETED
            session.completed_at = end_time
            session.total_duration_seconds = duration_seconds
            session.total_tokens_used = total_tokens
            session.agent_count_completed = agents_completed
            session.agent_count_failed = agents_failed

    @staticmethod
    async def _set_session_failed(
        db: AsyncSession,
        session_id: uuid.UUID,
        error: str,
    ) -> None:
        result = await db.execute(
            select(AnalysisSession).where(AnalysisSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if session:
            session.status = SessionStatus.FAILED
            session.completed_at = datetime.now(tz=timezone.utc)
            session.error_message = error

    @staticmethod
    def _planned_agents(config: AnalysisConfig) -> list[str]:
        """Return list of agent names to run based on config."""
        agents = []
        if config.run_cleaner:
            agents.append(AgentName.CLEANER)
        if config.run_analyst:
            agents.append(AgentName.ANALYST)
        if config.run_visualizer:
            agents.append(AgentName.VISUALIZER)
        if config.run_storyteller:
            agents.append(AgentName.STORYTELLER)
        return agents
