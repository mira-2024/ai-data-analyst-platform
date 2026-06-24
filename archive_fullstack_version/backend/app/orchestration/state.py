"""
Shared analysis state — the contract between all agents.

AnalysisState is a TypedDict passed through the LangGraph workflow.
Each agent node reads from it and writes its outputs back to it.
Agents communicate ONLY through this state — never by calling each other.

Design principles:
  - DataFrames are held in memory during execution only
  - All serializable outputs (insights, charts, report) are Pydantic models
  - The state is checkpointed to DB after each agent completes (via AgentRun.output_json)
  - 'total_tokens_used', 'agents_completed', 'agents_failed' are updated incrementally
"""

from __future__ import annotations

from typing import Any, TypedDict

import pandas as pd

from app.schemas.agent import (
    AnalystOutput,
    CleanerOutput,
    VisualizerOutput,
    StorytellerOutput,
)


class AnalysisState(TypedDict, total=False):
    # ── Identity ──────────────────────────────────────────────────────────────
    session_id: str
    dataset_id: str
    dataset_name: str

    # ── Input data ────────────────────────────────────────────────────────────
    raw_df: pd.DataFrame          # Original DataFrame — never mutated
    clean_df: pd.DataFrame        # After CleanerAgent
    agent_summary: dict[str, Any] # Compact summary sent to LLMs

    # ── Analysis config ───────────────────────────────────────────────────────
    config: dict[str, Any]        # User config (focus areas, toggles)

    # ── Agent outputs (written once per agent, never overwritten) ─────────────
    cleaner_output: CleanerOutput | None
    analyst_output: AnalystOutput | None
    visualizer_output: VisualizerOutput | None
    storyteller_output: StorytellerOutput | None

    # ── Agent run IDs (for linking events to DB records) ──────────────────────
    cleaner_run_id: str | None
    analyst_run_id: str | None
    visualizer_run_id: str | None
    storyteller_run_id: str | None

    # ── Counters ──────────────────────────────────────────────────────────────
    total_tokens_used: int
    agents_completed: int
    agents_failed: int

    # ── Error tracking ────────────────────────────────────────────────────────
    last_error: str | None
    failed_agents: list[str]
