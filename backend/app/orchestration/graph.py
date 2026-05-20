"""
LangGraph workflow graph definition.

Defines the multi-agent DAG:
  cleaner_node → analyst_node → visualizer_node → storyteller_node

Each node is a thin wrapper that calls execute_agent_node() with
the appropriate agent function. The graph handles routing — agents
don't know what comes before or after them.

Conditional edges allow skipping agents that are disabled in config
or that have already failed with a fatal error.
"""

from __future__ import annotations

import asyncio
from typing import Any

from langgraph.graph import END, START, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.orchestration.event_bus import EventBus
from app.orchestration.runner import execute_agent_node
from app.orchestration.state import AnalysisState
from app.schemas.analysis import AnalysisConfig


def build_graph(
    bus: EventBus,
    db: AsyncSession,
    cancel_token: asyncio.Event,
    config: AnalysisConfig,
) -> Any:
    """
    Build and compile the analysis LangGraph.

    Returns a compiled CompiledGraph ready for ainvoke().
    """
    workflow = StateGraph(AnalysisState)

    # ── Node definitions ──────────────────────────────────────────────────────

    async def cleaner_node(state: AnalysisState) -> AnalysisState:
        from app.agents.cleaner.agent import CleanerAgent
        agent = CleanerAgent(bus=bus, db=db)
        return await execute_agent_node(
            agent_name="cleaner",
            agent_run_id=state.get("cleaner_run_id"),
            state=state,
            bus=bus,
            db=db,
            cancel_token=cancel_token,
            agent_fn=agent.run,
        )

    async def analyst_node(state: AnalysisState) -> AnalysisState:
        from app.agents.analyst.agent import AnalystAgent
        agent = AnalystAgent(bus=bus, db=db)
        return await execute_agent_node(
            agent_name="analyst",
            agent_run_id=state.get("analyst_run_id"),
            state=state,
            bus=bus,
            db=db,
            cancel_token=cancel_token,
            agent_fn=agent.run,
        )

    async def visualizer_node(state: AnalysisState) -> AnalysisState:
        from app.agents.visualizer.agent import VisualizerAgent
        agent = VisualizerAgent(bus=bus, db=db)
        return await execute_agent_node(
            agent_name="visualizer",
            agent_run_id=state.get("visualizer_run_id"),
            state=state,
            bus=bus,
            db=db,
            cancel_token=cancel_token,
            agent_fn=agent.run,
        )

    async def storyteller_node(state: AnalysisState) -> AnalysisState:
        from app.agents.storyteller.agent import StorytellerAgent
        agent = StorytellerAgent(bus=bus, db=db)
        return await execute_agent_node(
            agent_name="storyteller",
            agent_run_id=state.get("storyteller_run_id"),
            state=state,
            bus=bus,
            db=db,
            cancel_token=cancel_token,
            agent_fn=agent.run,
        )

    # ── Register nodes ────────────────────────────────────────────────────────

    if config.run_cleaner:
        workflow.add_node("cleaner", cleaner_node)
    if config.run_analyst:
        workflow.add_node("analyst", analyst_node)
    if config.run_visualizer:
        workflow.add_node("visualizer", visualizer_node)
    if config.run_storyteller:
        workflow.add_node("storyteller", storyteller_node)

    # ── Edge wiring ───────────────────────────────────────────────────────────
    # Build the sequence dynamically based on which agents are enabled

    enabled = []
    if config.run_cleaner:
        enabled.append("cleaner")
    if config.run_analyst:
        enabled.append("analyst")
    if config.run_visualizer:
        enabled.append("visualizer")
    if config.run_storyteller:
        enabled.append("storyteller")

    if not enabled:
        # Nothing to run — go straight to end
        workflow.add_edge(START, END)
    else:
        workflow.add_edge(START, enabled[0])
        for i in range(len(enabled) - 1):
            workflow.add_edge(enabled[i], enabled[i + 1])
        workflow.add_edge(enabled[-1], END)

    return workflow.compile()
