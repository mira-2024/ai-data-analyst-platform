"""
Async SQLAlchemy database engine and session factory.

Architecture decisions:
- asyncpg driver for non-blocking PostgreSQL I/O
- Connection pool sized for concurrent agent workloads
- Single engine instance shared across the application lifetime
- Per-request sessions via FastAPI dependency injection

Usage in routes:
    async def my_route(db: AsyncSession = Depends(get_db)):
        result = await db.execute(select(Dataset))

Usage in services (outside request context):
    async with get_session() as db:
        result = await db.execute(select(Dataset))
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

# ── Engine ────────────────────────────────────────────────────────────────────

def _build_engine() -> AsyncEngine:
    """
    Create the async SQLAlchemy engine.

    NullPool is used in test environments to avoid connection leaks
    between test cases. In production, use the default pool.
    """
    pool_kwargs: dict = {}

    if settings.is_production:
        pool_kwargs = {
            "pool_size": settings.DATABASE_POOL_SIZE,
            "max_overflow": settings.DATABASE_MAX_OVERFLOW,
            "pool_timeout": settings.DATABASE_POOL_TIMEOUT,
            "pool_pre_ping": True,  # Validate connections before use
        }

    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DATABASE_ECHO,
        future=True,
        **pool_kwargs,
    )

    logger.info(
        "database_engine_created",
        url=settings.DATABASE_URL.split("@")[-1],  # Log host only, not credentials
        pool_size=settings.DATABASE_POOL_SIZE,
    )

    return engine


# Module-level singleton — created once on import
engine: AsyncEngine = _build_engine()

# Session factory
AsyncSessionFactory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Avoid lazy-load errors after commit
    autocommit=False,
    autoflush=False,
)


# ── Dependencies ──────────────────────────────────────────────────────────────

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency: yields a DB session per request.

    Commits on success, rolls back on exception, always closes.
    Use with:
        async def route(db: AsyncSession = Depends(get_db)):
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for DB access outside of request context.
    Use in background tasks, orchestration engine, services.

    Usage:
        async with get_session() as db:
            await db.execute(...)
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ── Lifecycle ─────────────────────────────────────────────────────────────────

async def check_connection() -> bool:
    """Verify database connectivity. Used in health check endpoint."""
    try:
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        return True
    except Exception as exc:
        logger.error("database_connection_failed", error=str(exc))
        return False


async def dispose_engine() -> None:
    """Cleanly close all connections. Called on app shutdown."""
    await engine.dispose()
    logger.info("database_engine_disposed")
