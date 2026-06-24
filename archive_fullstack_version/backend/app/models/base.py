"""
SQLAlchemy declarative base and shared mixins.

All ORM models inherit from Base (for the registry) and TimestampMixin
(for created_at / updated_at). Primary keys are UUIDs by default —
never integers — so they are safe to expose in APIs and support
future distributed/sharded deployments.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


class TimestampMixin:
    """
    Adds created_at and updated_at to any model.

    Both are timezone-aware UTC timestamps.
    updated_at is automatically refreshed by the DB on every UPDATE
    via server_onupdate=func.now().
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UUIDPrimaryKeyMixin:
    """UUID primary key generated at the Python level (not DB-side)."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
