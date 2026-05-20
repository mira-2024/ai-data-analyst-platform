"""
SSE streaming endpoint.

Clients subscribe here to receive real-time orchestration events.
Uses Server-Sent Events (text/event-stream) — HTTP-native, no WebSocket.

Each event is a JSON-serialized WorkflowEvent wrapped in SSE format:
    data: {"event_type": "AGENT_STARTED", "agent_name": "cleaner", ...}

If the session is already complete, stored events are replayed from the DB.
If the session is running, live events are streamed as they occur.
"""

from __future__ import annotations

import asyncio
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.logging import get_logger
from app.orchestration.event_bus import SSEBroadcaster, SSEQueue, event_bus_registry

router = APIRouter()
logger = get_logger(__name__)
settings = get_settings()


def _format_sse(data: dict, event: str | None = None, id: str | None = None) -> str:
    """Format a dict as an SSE message string."""
    lines = []
    if id:
        lines.append(f"id: {id}")
    if event:
        lines.append(f"event: {event}")
    lines.append(f"data: {json.dumps(data)}")
    lines.append("")  # Required blank line between events
    return "\n".join(lines) + "\n"


@router.get("/{session_id}")
async def stream_session_events(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """
    Stream real-time orchestration events for a session via SSE.

    Connect with:
        const es = new EventSource(`/api/v1/stream/${sessionId}`)
        es.onmessage = (e) => console.log(JSON.parse(e.data))

    The stream closes automatically when the session completes or fails.
    Keepalive comments (': keepalive') are sent every 15 seconds.
    """
    session_id_str = str(session_id)
    bus = event_bus_registry.get(session_id_str)

    if bus is None:
        # Session not actively running — check if it exists and replay from DB
        from app.services.analysis_service import AnalysisService
        service = AnalysisService(db)
        try:
            session = await service.get_by_id(session_id)
        except Exception:
            raise HTTPException(status_code=404, detail="Session not found.")

        if session.status in ("completed", "failed", "cancelled"):
            # Replay stored events from DB
            return StreamingResponse(
                _replay_events(session_id_str, db),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "X-Accel-Buffering": "no",
                },
            )
        raise HTTPException(
            status_code=404,
            detail="Session is not actively streaming. Start analysis first.",
        )

    # Live session — subscribe SSEQueue to the bus
    queue = SSEQueue(session_id=session_id_str)
    broadcaster = SSEBroadcaster(queue=queue)
    bus.subscribe(broadcaster)

    logger.info("sse_client_connected", session_id=session_id_str)

    return StreamingResponse(
        _live_event_generator(queue, bus, broadcaster, session_id_str),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
            "Connection": "keep-alive",
        },
    )


async def _live_event_generator(
    queue: SSEQueue,
    bus,
    broadcaster: SSEBroadcaster,
    session_id: str,
):
    """Yield SSE-formatted events from the live queue."""
    keepalive_interval = settings.SSE_KEEPALIVE_INTERVAL_SECONDS
    try:
        while True:
            try:
                event_dict = await asyncio.wait_for(
                    queue.get(),
                    timeout=keepalive_interval,
                )
            except asyncio.TimeoutError:
                # Send keepalive comment to prevent connection timeout
                yield ": keepalive\n\n"
                continue

            if event_dict is None:
                # Sentinel — analysis complete, close stream
                yield _format_sse({"event_type": "STREAM_CLOSED"})
                break

            yield _format_sse(
                data=event_dict,
                id=event_dict.get("event_id"),
                event=event_dict.get("event_type"),
            )

    except asyncio.CancelledError:
        # Client disconnected
        logger.info("sse_client_disconnected", session_id=session_id)
    finally:
        bus.unsubscribe(broadcaster)


async def _replay_events(session_id: str, db: AsyncSession):
    """Replay stored events from DB for a completed session."""
    from sqlalchemy import select, asc
    from app.models.workflow_event import WorkflowEvent

    result = await db.execute(
        select(WorkflowEvent)
        .where(WorkflowEvent.session_id == uuid.UUID(session_id))
        .order_by(asc(WorkflowEvent.sequence_num))
    )
    events = result.scalars().all()

    for event in events:
        event_dict = {
            "event_type": event.event_type,
            "session_id": str(event.session_id),
            "agent_name": event.agent_name,
            "sequence_num": event.sequence_num,
            "emitted_at": event.emitted_at.isoformat(),
            **event.payload,
        }
        yield _format_sse(
            data=event_dict,
            id=str(event.id),
            event=event.event_type,
        )

    yield _format_sse({"event_type": "REPLAY_COMPLETE"})
