"""
Abstract BaseAgent — shared infrastructure for all agents.

Every agent (Cleaner, Analyst, Visualizer, Storyteller) inherits from this.

Provides:
  - Tool registration interface
  - LLM tool-use loop via LLMClient
  - Execution trace emission (writes to DB via EventBus)
  - Token tracking
  - Structured output parsing (JSON extraction from LLM response)

Agents implement:
  - _get_tools()          → list of Anthropic tool definitions
  - _execute_tool()       → dispatch to tool functions
  - _build_user_message() → construct the prompt sent to Claude
  - _parse_output()       → convert LLM JSON response to Pydantic schema
  - run()                 → called by the orchestration graph
"""

from __future__ import annotations

import json
import re
import time
import uuid
from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.llm_client import LLMResponse, ToolDefinition, get_llm_client
from app.core.logging import get_logger
from app.models.execution_trace import TraceStepType
from app.orchestration.event_bus import EventBus
from app.orchestration.events import (
    AnalysisProgressEvent,
    ToolCalledEvent,
    ToolCompletedEvent,
    ToolFailedEvent,
)
from app.orchestration.state import AnalysisState
from app.prompts.registry import PromptRegistry

logger = get_logger(__name__)


class BaseAgent(ABC):
    """
    Abstract base for all analysis agents.

    Subclasses must implement the abstract methods.
    The run() method is called by the LangGraph node wrapper.
    """

    agent_name: str  # Override in subclass: "cleaner", "analyst", etc.
    agent_version: str = "1.0.0"

    def __init__(self, bus: EventBus, db: AsyncSession) -> None:
        self.bus = bus
        self.db = db
        self.llm = get_llm_client()
        self.prompt = PromptRegistry.get(self.agent_name)
        self._trace_sequence: int = 0
        self._agent_run_id: str | None = None

    # ── Abstract interface ────────────────────────────────────────────────────

    @abstractmethod
    def _get_tools(self) -> list[ToolDefinition]:
        """Return Anthropic tool definitions for this agent."""
        ...

    @abstractmethod
    def _execute_tool(self, tool_name: str, tool_input: dict) -> Any:
        """
        Dispatch a tool call to the appropriate implementation.
        Synchronous — runs in threadpool via LLMClient.
        """
        ...

    @abstractmethod
    def _build_user_message(self, state: AnalysisState) -> str:
        """Build the initial user message sent to Claude."""
        ...

    @abstractmethod
    def _parse_output(self, llm_response: LLMResponse, state: AnalysisState) -> Any:
        """
        Parse the LLM's final text response into a typed Pydantic model.
        Must return the appropriate *Output schema.
        """
        ...

    @abstractmethod
    async def run(
        self, state: AnalysisState, bus: EventBus
    ) -> AnalysisState:
        """
        Execute this agent and return the updated state.
        Called by the LangGraph node wrapper.
        """
        ...

    # ── Shared execution infrastructure ───────────────────────────────────────

    async def _run_llm(
        self, state: AnalysisState
    ) -> LLMResponse:
        """
        Run the LLM tool-use loop with trace emission wired in.
        """
        session_id = state["session_id"]
        agent_run_id = state.get(f"{self.agent_name}_run_id")
        self._agent_run_id = agent_run_id

        user_message = self._build_user_message(state)
        tools = self._get_tools()

        async def on_tool_call(tool_name: str, tool_input: dict) -> None:
            await self.bus.emit(ToolCalledEvent(
                session_id=session_id,
                agent_run_id=agent_run_id,
                agent_name=self.agent_name,
                tool_name=tool_name,
                input_preview=self._truncate_for_preview(tool_input),
            ))
            await self._write_trace(
                agent_run_id=agent_run_id,
                step_type=TraceStepType.TOOL_CALL,
                step_name=f"call:{tool_name}",
                tool_name=tool_name,
                input_data=tool_input,
            )

        async def on_tool_result(tool_name: str, result: Any) -> None:
            preview = self._truncate_for_preview(
                result if isinstance(result, dict) else {"result": str(result)[:200]}
            )
            await self.bus.emit(ToolCompletedEvent(
                session_id=session_id,
                agent_run_id=agent_run_id,
                agent_name=self.agent_name,
                tool_name=tool_name,
                duration_ms=0,  # Individual tool timing tracked in _execute_tool
                output_preview=preview,
            ))

        # Wrap callbacks to be sync-compatible (LLMClient calls them in threadpool)
        import asyncio

        loop = asyncio.get_running_loop()

        def sync_on_tool_call(name: str, inp: dict) -> None:
            asyncio.run_coroutine_threadsafe(on_tool_call(name, inp), loop)

        def sync_on_tool_result(name: str, res: Any) -> None:
            asyncio.run_coroutine_threadsafe(on_tool_result(name, res), loop)

        response = await self.llm.run_with_tools(
            system_prompt=self.prompt.system,
            user_message=user_message,
            tools=tools,
            tool_executor=self._timed_tool_executor,
            on_tool_call=sync_on_tool_call,
            on_tool_result=sync_on_tool_result,
        )

        logger.info(
            "agent_llm_complete",
            agent=self.agent_name,
            tokens_in=response.tokens_in,
            tokens_out=response.tokens_out,
        )

        return response

    def _timed_tool_executor(self, tool_name: str, tool_input: dict) -> Any:
        """Wraps _execute_tool with timing for trace records."""
        t0 = time.perf_counter()
        result = self._execute_tool(tool_name, tool_input)
        duration_ms = int((time.perf_counter() - t0) * 1000)
        logger.debug(
            "tool_executed",
            agent=self.agent_name,
            tool=tool_name,
            duration_ms=duration_ms,
        )
        return result

    async def _emit_progress(
        self,
        state: AnalysisState,
        step: str,
        message: str,
        progress: float,
    ) -> None:
        await self.bus.emit(AnalysisProgressEvent(
            session_id=state["session_id"],
            agent_run_id=state.get(f"{self.agent_name}_run_id"),
            agent_name=self.agent_name,
            step=step,
            progress=progress,
            message=message,
        ))

    async def _write_trace(
        self,
        agent_run_id: str | None,
        step_type: TraceStepType,
        step_name: str,
        tool_name: str | None = None,
        input_data: dict | None = None,
        output_data: dict | None = None,
        summary: str | None = None,
        duration_ms: int | None = None,
    ) -> None:
        """Persist an execution trace record to the DB."""
        if not agent_run_id:
            return

        from app.core.database import get_session
        from app.models.execution_trace import ExecutionTrace

        self._trace_sequence += 1

        try:
            async with get_session() as db:
                trace = ExecutionTrace(
                    agent_run_id=uuid.UUID(agent_run_id),
                    step_type=step_type,
                    step_name=step_name,
                    tool_name=tool_name,
                    sequence_num=self._trace_sequence,
                    duration_ms=duration_ms,
                    input_json=self._safe_json(input_data),
                    output_json=self._safe_json(output_data),
                    summary=summary,
                )
                db.add(trace)
        except Exception as exc:
            logger.warning(
                "trace_write_failed",
                agent=self.agent_name,
                step=step_name,
                error=str(exc),
            )

    # ── Output parsing utilities ──────────────────────────────────────────────

    @staticmethod
    def _extract_json_from_response(text: str) -> dict | list:
        """
        Extract a JSON object or array from LLM text response.

        Handles:
          - Bare JSON
          - JSON wrapped in ```json ... ``` code blocks
          - JSON embedded in surrounding text
        """
        # Try direct parse first
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass

        # Try extracting from code block
        code_block = re.search(r"```(?:json)?\s*\n?([\s\S]*?)\n?```", text, re.IGNORECASE)
        if code_block:
            try:
                return json.loads(code_block.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Try finding first { ... } or [ ... ] block
        for pattern in (r"(\{[\s\S]*\})", r"(\[[\s\S]*\])"):
            match = re.search(pattern, text)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    continue

        raise ValueError(
            f"Could not extract valid JSON from LLM response. "
            f"Response preview: {text[:200]!r}"
        )

    @staticmethod
    def _truncate_for_preview(data: dict, max_str_len: int = 100) -> dict:
        """Recursively truncate long string values for UI preview."""
        result = {}
        for k, v in data.items():
            if isinstance(v, str) and len(v) > max_str_len:
                result[k] = v[:max_str_len] + "..."
            elif isinstance(v, dict):
                result[k] = BaseAgent._truncate_for_preview(v, max_str_len)
            elif isinstance(v, list):
                result[k] = v[:5]  # First 5 items only
            else:
                result[k] = v
        return result

    @staticmethod
    def _safe_json(data: Any) -> dict | None:
        """Convert data to a DB-safe dict, handling non-serializable types."""
        if data is None:
            return None
        if isinstance(data, dict):
            return json.loads(json.dumps(data, default=str))
        return {"value": str(data)}
