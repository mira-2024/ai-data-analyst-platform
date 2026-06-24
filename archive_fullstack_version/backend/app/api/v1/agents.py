"""Agents API — execution traces and run details."""
from __future__ import annotations
import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.agent import ExecutionTraceResponse

router = APIRouter()

@router.get("/{agent_run_id}/traces", response_model=list[ExecutionTraceResponse])
async def get_agent_traces(
    agent_run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[ExecutionTraceResponse]:
    """Get all execution traces for an agent run (for Agent Trace Viewer)."""
    from sqlalchemy import select, asc
    from app.models.execution_trace import ExecutionTrace
    result = await db.execute(
        select(ExecutionTrace)
        .where(ExecutionTrace.agent_run_id == agent_run_id)
        .order_by(asc(ExecutionTrace.sequence_num))
    )
    traces = result.scalars().all()
    return [ExecutionTraceResponse.model_validate(t) for t in traces]
