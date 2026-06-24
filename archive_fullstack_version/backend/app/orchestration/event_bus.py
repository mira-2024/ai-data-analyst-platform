"""
Async event bus for orchestration events.

Architecture:
  Agents → EventBus.emit() → [subscribers notified concurrently]
                                ├── EventPersister → PostgreSQL
                                └── SSEBroadcaster → connected clients

The EventBus is a session-scoped pub/sub system:
- Each analysis session gets its own isolated bus instance
- Subscribers register callbacks (async functions)
- Events are dispatched concurrently to all subscribers
- Sequence numbers are assigned atomically per session

This decouples orchestration logic from delivery mechanism entirely.
Agents call bus.emit(event) — they know nothing about HTTP, SSE, or DB.

Usage:
    bus = EventBus(session_id="uuid")
    bus.subscribe(my_async_handler)
    await bus.emit(AgentStartedEvent(session_id="uuid", agent_name="cleaner"))
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any

from app.core.logging import get_logger
from app.orchestration.events import BaseWorkflowEvent, WorkflowEvent

logger = get_logger(__name__)

# Type alias for subscriber callbacks
EventHandler = Callable[[WorkflowEvent], Awaitable[None]]


class EventBus:
    """
    Per-session async event bus.

    Thread-safe for async code. Each emit() assigns a monotonically
    increasing sequence_num and notifies all subscribers concurrently.

    Errors in individual subscribers are logged but do not propagate —
    a failing DB write should not crash the SSE stream, and vice versa.
    """

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self._subscribers: list[EventHandler] = []
        self._sequence_counter: int = 0
        self._lock = asyncio.Lock()

    def subscribe(self, handler: EventHandler) -> None:
        """
        Register a subscriber callback.

        The handler will be called for every event emitted on this bus.
        Handlers must be async functions accepting a single WorkflowEvent arg.
        """
        self._subscribers.append(handler)
        logger.debug(
            "event_bus_subscriber_registered",
            session_id=self.session_id,
            handler=getattr(handler, "__qualname__", type(handler).__name__),
        )

    def unsubscribe(self, handler: EventHandler) -> None:
        """Remove a subscriber. Silently ignores if not registered."""
        try:
            self._subscribers.remove(handler)
        except ValueError:
            pass

    async def emit(self, event: BaseWorkflowEvent) -> None:
        """
        Emit an event to all subscribers.

        Assigns sequence_num atomically, then notifies subscribers
        concurrently. Subscriber errors are caught and logged.

        Args:
            event: Any WorkflowEvent instance with session_id pre-set.
        """
        async with self._lock:
            self._sequence_counter += 1
            event.sequence_num = self._sequence_counter

        logger.debug(
            "event_emitted",
            session_id=self.session_id,
            event_type=event.event_type,
            sequence_num=event.sequence_num,
            agent_name=event.agent_name,
        )

        if not self._subscribers:
            return

        # Dispatch to all subscribers concurrently
        results = await asyncio.gather(
            *[handler(event) for handler in self._subscribers],
            return_exceptions=True,
        )

        # Log subscriber errors without crashing the bus
        for handler, result in zip(self._subscribers, results):
            if isinstance(result, Exception):
                logger.error(
                    "event_bus_subscriber_error",
                    session_id=self.session_id,
                    handler=getattr(handler, "__qualname__", type(handler).__name__),
                    event_type=event.event_type,
                    error=str(result),
                )

    async def emit_many(self, events: list[BaseWorkflowEvent]) -> None:
        """Emit multiple events sequentially (preserving order)."""
        for event in events:
            await self.emit(event)

    async def close_all_queues(self) -> None:
        """
        Signal all connected SSE clients that the stream is closed.

        Iterates subscribers and calls close() on any SSEBroadcaster queues.
        Use this instead of reaching into private internals from outside.
        """
        for subscriber in self._subscribers:
            queue = getattr(subscriber, "_queue", None)
            if queue is not None and hasattr(queue, "close"):
                await queue.close()

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)


class SSEQueue:
    """
    Per-session SSE event queue.

    The SSEBroadcaster writes events here.
    The SSE endpoint reads from here and streams to the client.

    Uses asyncio.Queue for backpressure. If the queue is full
    (client too slow), older events are dropped with a warning.
    """

    def __init__(self, session_id: str, maxsize: int = 1000) -> None:
        self.session_id = session_id
        self._queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue(maxsize=maxsize)

    async def put(self, event_dict: dict[str, Any]) -> None:
        """Add an event to the queue (non-blocking, drops if full)."""
        try:
            self._queue.put_nowait(event_dict)
        except asyncio.QueueFull:
            logger.warning(
                "sse_queue_full_dropping_event",
                session_id=self.session_id,
                event_type=event_dict.get("event_type"),
            )

    async def get(self) -> dict[str, Any] | None:
        """
        Wait for next event. Returns None as a sentinel to close the stream.
        """
        return await self._queue.get()

    async def close(self) -> None:
        """Signal stream end by enqueuing None sentinel."""
        await self._queue.put(None)


class SSEBroadcaster:
    """
    EventBus subscriber that pushes events to an SSEQueue.

    One SSEBroadcaster per connected SSE client per session.
    Multiple clients can connect to the same session simultaneously.
    """

    def __init__(self, queue: SSEQueue) -> None:
        self._queue = queue

    async def __call__(self, event: BaseWorkflowEvent) -> None:
        """Called by EventBus for every emitted event."""
        await self._queue.put(event.to_sse_dict())


# ── Global session bus registry ───────────────────────────────────────────────

class EventBusRegistry:
    """
    Application-level registry of active session EventBus instances.

    Allows SSE endpoints to look up the bus for a given session_id
    and subscribe a new SSEQueue to it.

    Sessions are cleaned up when analysis completes.
    """

    def __init__(self) -> None:
        self._buses: dict[str, EventBus] = {}
        self._lock = asyncio.Lock()

    async def create(self, session_id: str) -> EventBus:
        """Create and register a new EventBus for a session."""
        async with self._lock:
            if session_id in self._buses:
                raise RuntimeError(f"EventBus already exists for session {session_id}")
            bus = EventBus(session_id=session_id)
            self._buses[session_id] = bus
            logger.info("event_bus_created", session_id=session_id)
            return bus

    def get(self, session_id: str) -> EventBus | None:
        """Return the bus for a session, or None if not found."""
        return self._buses.get(session_id)

    async def destroy(self, session_id: str) -> None:
        """Remove a session's bus after analysis completes."""
        async with self._lock:
            self._buses.pop(session_id, None)
            logger.info("event_bus_destroyed", session_id=session_id)

    @property
    def active_sessions(self) -> list[str]:
        return list(self._buses.keys())


# Application-level singleton
event_bus_registry = EventBusRegistry()
