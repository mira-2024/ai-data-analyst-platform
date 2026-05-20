"""
OrchestratorRunner — LangGraph workflow execution engine.

Builds and executes the multi-agent analysis graph:
  CleanerAgent → AnalystAgent → VisualizerAgent → StorytellerAgent

Each node:
  1. Updates the AgentRun DB record (status → running)
  2. Emits AGENT_STARTED event
  3. Executes the agent (LLM + tools)
  4. Writes output to shared state
  5. Updates AgentRun DB record (status → completed/failed)
  6. Emits AGENT_COMPLETED / AGENT_FAILED event

Cancellation is checked before each node via cancel_token.
Retry logic is handled inside each agent via tenacity.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.agent_run import AgentRun, AgentRunStatus
from app.orchestration.event_bus import EventBus
from app.orchestration.events import (
    AgentCompletedEvent,
    AgentFailedEvent,
    AgentStartedEvent,
)
from app.orchestration.state import AnalysisState
from app.schemas.analysis import AnalysisConfig

logger = get_logger(__name__)
settings = get_settings()


class OrchestratorRunner:
    """
    Executes the multi-agent analysis pipeline via LangGraph.

    One instance per analysis session.
    """

    def __init__(
        self,
        session_id: str,
        dataset_id: str,
        bus: EventBus,
        db: AsyncSession,
        cancel_token: asyncio.Event,
    ) -> None:
        self.session_id = session_id
        self.dataset_id = dataset_id
        self.bus = bus
        self.db = db
        self.cancel_token = cancel_token

    async def run(
        self,
        df: pd.DataFrame,
        agent_summary: dict[str, Any],
        config: AnalysisConfig,
    ) -> AnalysisState:
        """
        Execute the full agent pipeline.

        Returns the final AnalysisState with all agent outputs.
        """
        from app.orchestration.graph import build_graph

        # Build initial state
        initial_state: AnalysisState = {
            "session_id": self.session_id,
            "dataset_id": self.dataset_id,
            "raw_df": df,
            "clean_df": df.copy(),
            "agent_summary": agent_summary,
            "config": config.model_dump(),
            "cleaner_output": None,
            "analyst_output": None,
            "visualizer_output": None,
            "storyteller_output": None,
            "cleaner_run_id": None,
            "analyst_run_id": None,
            "visualizer_run_id": None,
            "storyteller_run_id": None,
            "total_tokens_used": 0,
            "agents_completed": 0,
            "agents_failed": 0,
            "last_error": None,
            "failed_agents": [],
        }

        # Fetch AgentRun IDs from DB (created by AnalysisService.start)
        await self._load_agent_run_ids(initial_state)

        # Build and compile the LangGraph
        graph = build_graph(
            bus=self.bus,
            db=self.db,
            cancel_token=self.cancel_token,
            config=config,
        )

        # Execute graph
        final_state = await graph.ainvoke(
            initial_state,
            config={"recursion_limit": 20},
        )

        return final_state

    async def _load_agent_run_ids(self, state: AnalysisState) -> None:
        """
        Pre-load AgentRun IDs into state so nodes can reference them
        when emitting events without extra DB queries.
        """
        result = await self.db.execute(
            select(AgentRun).where(
                AgentRun.session_id == uuid.UUID(self.session_id)
            )
        )
        runs = result.scalars().all()

        for run in runs:
            key = f"{run.agent_name}_run_id"
            if key in AnalysisState.__annotations__:
                state[key] = str(run.id)  # type: ignore[literal-required]


async def execute_agent_node(
    agent_name: str,
    agent_run_id: str | None,
    state: AnalysisState,
    bus: EventBus,
    db: AsyncSession,
    cancel_token: asyncio.Event,
    agent_fn,  # The async agent callable
) -> AnalysisState:
    """
    Shared execution wrapper for all agent nodes.

    Handles: cancel check, DB status updates, event emission, timing,
    retry orchestration, and error capture.
    """
    session_id = state["session_id"]

    # Check for cancellation before starting
    if cancel_token.is_set():
        logger.info(
            "agent_node_cancelled_before_start",
            agent=agent_name,
            session_id=session_id,
        )
        return state

    start_time = datetime.now(tz=timezone.utc)

    # Update AgentRun → running
    if agent_run_id:
        await _update_agent_run_status(
            db, agent_run_id, AgentRunStatus.RUNNING,
            started_at=start_time,
        )

    # Emit AGENT_STARTED
    await bus.emit(
        AgentStartedEvent(
            session_id=session_id,
            agent_run_id=agent_run_id,
            agent_name=agent_name,
            agent_version="1.0.0",
            description=_agent_description(agent_name),
        )
    )

    try:
        # Execute the agent
        updated_state = await agent_fn(state, bus)

        end_time = datetime.now(tz=timezone.utc)
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        # Extract token usage from agent output
        tokens_in = _extract_tokens_in(updated_state, agent_name)
        tokens_out = _extract_tokens_out(updated_state, agent_name)

        # Update AgentRun → completed
        if agent_run_id:
            output = _extract_output_json(updated_state, agent_name)
            await _update_agent_run_completed(
                db, agent_run_id,
                end_time=end_time,
                duration_ms=duration_ms,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                output_json=output,
            )

        # Update state counters
        updated_state["total_tokens_used"] = (
            state.get("total_tokens_used", 0) + tokens_in + tokens_out
        )
        updated_state["agents_completed"] = state.get("agents_completed", 0) + 1

        # Emit AGENT_COMPLETED
        await bus.emit(
            AgentCompletedEvent(
                session_id=session_id,
                agent_run_id=agent_run_id,
                agent_name=agent_name,
                duration_ms=duration_ms,
                tokens_input=tokens_in,
                tokens_output=tokens_out,
                output_preview=_build_output_preview(updated_state, agent_name),
            )
        )

        logger.info(
            "agent_node_completed",
            agent=agent_name,
            duration_ms=duration_ms,
            tokens=tokens_in + tokens_out,
        )

        return updated_state

    except Exception as exc:
        end_time = datetime.now(tz=timezone.utc)
        duration_ms = int((end_time - start_time).total_seconds() * 1000)
        error_msg = str(exc)

        logger.exception(
            "agent_node_failed",
            agent=agent_name,
            session_id=session_id,
            error=error_msg,
        )

        # Update AgentRun → failed
        if agent_run_id:
            await _update_agent_run_failed(
                db, agent_run_id,
                end_time=end_time,
                duration_ms=duration_ms,
                error_type=type(exc).__name__,
                error_message=error_msg,
            )

        state["agents_failed"] = state.get("agents_failed", 0) + 1
        state["last_error"] = error_msg
        failed = list(state.get("failed_agents", []))
        failed.append(agent_name)
        state["failed_agents"] = failed

        # Emit AGENT_FAILED
        await bus.emit(
            AgentFailedEvent(
                session_id=session_id,
                agent_run_id=agent_run_id,
                agent_name=agent_name,
                error_type=type(exc).__name__,
                error_message=error_msg,
                retry_count=0,
                will_retry=False,
            )
        )

        # Return unchanged state — downstream agents proceed with degraded input
        return state


# ── DB update helpers ─────────────────────────────────────────────────────────

async def _update_agent_run_status(
    db: AsyncSession,
    agent_run_id: str,
    status: AgentRunStatus,
    started_at: datetime | None = None,
) -> None:
    result = await db.execute(
        select(AgentRun).where(AgentRun.id == uuid.UUID(agent_run_id))
    )
    run = result.scalar_one_or_none()
    if run:
        run.status = status
        if started_at:
            run.started_at = started_at


async def _update_agent_run_completed(
    db: AsyncSession,
    agent_run_id: str,
    end_time: datetime,
    duration_ms: int,
    tokens_in: int,
    tokens_out: int,
    output_json: dict | None,
) -> None:
    result = await db.execute(
        select(AgentRun).where(AgentRun.id == uuid.UUID(agent_run_id))
    )
    run = result.scalar_one_or_none()
    if run:
        run.status = AgentRunStatus.COMPLETED
        run.completed_at = end_time
        run.duration_ms = duration_ms
        run.tokens_input = tokens_in
        run.tokens_output = tokens_out
        run.output_json = output_json
        run.llm_model = settings.LLM_MODEL


async def _update_agent_run_failed(
    db: AsyncSession,
    agent_run_id: str,
    end_time: datetime,
    duration_ms: int,
    error_type: str,
    error_message: str,
) -> None:
    result = await db.execute(
        select(AgentRun).where(AgentRun.id == uuid.UUID(agent_run_id))
    )
    run = result.scalar_one_or_none()
    if run:
        run.status = AgentRunStatus.FAILED
        run.completed_at = end_time
        run.duration_ms = duration_ms
        run.error_type = error_type
        run.error_message = error_message


# ── State extraction helpers ──────────────────────────────────────────────────

def _extract_tokens_in(state: AnalysisState, agent_name: str) -> int:
    output = _get_agent_output(state, agent_name)
    return getattr(output, "_tokens_in", 0) if output else 0


def _extract_tokens_out(state: AnalysisState, agent_name: str) -> int:
    output = _get_agent_output(state, agent_name)
    return getattr(output, "_tokens_out", 0) if output else 0


def _extract_output_json(state: AnalysisState, agent_name: str) -> dict | None:
    output = _get_agent_output(state, agent_name)
    if output and hasattr(output, "model_dump"):
        return output.model_dump(mode="json", exclude={"_tokens_in", "_tokens_out"})
    return None


def _get_agent_output(state: AnalysisState, agent_name: str):
    return state.get(f"{agent_name}_output")  # type: ignore


def _build_output_preview(state: AnalysisState, agent_name: str) -> dict:
    """Build a compact preview of the agent's output for the UI."""
    output = _get_agent_output(state, agent_name)
    if not output:
        return {}
    if agent_name == "cleaner":
        return {
            "rows_before": getattr(output, "rows_before", 0),
            "rows_after": getattr(output, "rows_after", 0),
            "quality_score": getattr(output, "quality_score", 0),
            "actions_count": len(getattr(output, "actions", [])),
        }
    if agent_name == "analyst":
        return {
            "insights_count": len(getattr(output, "insights", [])),
            "correlations_count": len(getattr(output, "correlations", [])),
        }
    if agent_name == "visualizer":
        return {"charts_count": len(getattr(output, "charts", []))}
    if agent_name == "storyteller":
        return {
            "title": getattr(output, "title", ""),
            "recommendations_count": len(getattr(output, "recommendations", [])),
        }
    return {}


def _agent_description(agent_name: str) -> str:
    return {
        "cleaner": "Cleaning and validating the dataset — handling missing values, outliers, and type corrections",
        "analyst": "Running exploratory data analysis — correlations, statistics, anomaly detection, and hypothesis generation",
        "visualizer": "Generating the best visualizations to communicate the key findings",
        "storyteller": "Synthesizing insights into an executive narrative with business recommendations",
    }.get(agent_name, f"Running {agent_name} agent")
