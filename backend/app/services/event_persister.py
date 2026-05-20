"""
EventPersister — durable event storage subscriber.

Registered as an EventBus subscriber for every analysis session.
Every WorkflowEvent emitted during orchestration is written to
the workflow_events table in real-time.

This enables:
  - Session replay (re-stream stored events to new SSE clients)
  - Analysis history (full audit trail per session)
  - Agent Timeline UI (live + historical view uses same data)
  - Observability / debugging

Design notes:
  - Uses its own DB session (not the orchestration session) to avoid
    transaction boundary conflicts
  - Errors are caught and logged — a DB write failure should never
    crash the orchestration pipeline
  - Batch-writing (multiple events per flush) is possible as v2 optimization
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.core.logging import get_logger
from app.models.workflow_event import WorkflowEvent
from app.orchestration.events import BaseWorkflowEvent

logger = get_logger(__name__)


class EventPersister:
    """
    EventBus subscriber that persists every event to PostgreSQL.

    Instantiated once per session, registered on the session's EventBus.
    Each call to __call__() opens a short-lived DB session, writes the
    event, and closes it. This keeps writes isolated and immediately durable.
    """

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id

    async def __call__(self, event: BaseWorkflowEvent) -> None:
        """Persist a single workflow event to the DB."""
        from app.core.database import get_session

        try:
            async with get_session() as db:
                record = WorkflowEvent(
                    id=uuid.UUID(event.event_id)
                    if self._is_valid_uuid(event.event_id)
                    else uuid.uuid4(),
                    session_id=uuid.UUID(self.session_id),
                    agent_run_id=uuid.UUID(event.agent_run_id)
                    if event.agent_run_id and self._is_valid_uuid(event.agent_run_id)
                    else None,
                    event_type=event.event_type,
                    agent_name=event.agent_name,
                    sequence_num=event.sequence_num,
                    emitted_at=event.emitted_at or datetime.now(tz=timezone.utc),
                    payload=self._extract_payload(event),
                )
                db.add(record)

        except Exception as exc:
            # Log but never propagate — a DB failure must not kill the pipeline
            logger.error(
                "event_persist_failed",
                session_id=self.session_id,
                event_type=event.event_type,
                sequence_num=event.sequence_num,
                error=str(exc),
            )

    @staticmethod
    def _extract_payload(event: BaseWorkflowEvent) -> dict:
        """
        Extract event-specific payload fields (exclude envelope fields
        that are stored as dedicated columns).
        """
        envelope_keys = {
            "event_id", "session_id", "agent_run_id", "agent_name",
            "emitted_at", "sequence_num", "event_type",
        }
        return {
            k: v
            for k, v in event.model_dump(mode="json").items()
            if k not in envelope_keys
        }

    @staticmethod
    def _is_valid_uuid(value: str) -> bool:
        try:
            uuid.UUID(value)
            return True
        except (ValueError, AttributeError):
            return False
