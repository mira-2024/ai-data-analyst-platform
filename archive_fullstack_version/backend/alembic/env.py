"""
Alembic migration environment.

Configured for async SQLAlchemy (asyncpg driver).
Reads DATABASE_URL from app settings — never from alembic.ini directly.
Imports all models via app.models so autogenerate detects every table.

Run migrations:
    alembic upgrade head          # Apply all pending migrations
    alembic revision --autogenerate -m "describe change"   # Generate new migration
    alembic downgrade -1          # Rollback one migration
    alembic history               # Show migration history
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# ── Load app config ───────────────────────────────────────────────────────────
# Must happen before importing models to ensure env vars are loaded
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import get_settings
from app.models import Base  # noqa: F401 — registers all models with metadata

# ── Alembic config ────────────────────────────────────────────────────────────
config = context.config
settings = get_settings()

# Override sqlalchemy.url from app settings (not alembic.ini)
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


# ── Offline migrations ────────────────────────────────────────────────────────

def run_migrations_offline() -> None:
    """
    Run migrations without a live DB connection.
    Generates SQL script to stdout for review before applying.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online migrations ─────────────────────────────────────────────────────────

def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        # Render item changes (column modifications) in autogenerate
        render_as_batch=False,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations with an async engine (required for asyncpg)."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


# ── Entry point ───────────────────────────────────────────────────────────────

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
