"""
Structured logging configuration.

Produces JSON-formatted logs in production, human-readable in development.
Every log line includes: timestamp, level, logger name, message, and
any extra context fields passed by the caller.

Usage:
    from app.core.logging import get_logger
    logger = get_logger(__name__)
    logger.info("Dataset uploaded", dataset_id=str(dataset.id), rows=1000)
"""

from __future__ import annotations

import logging
import sys
from contextvars import ContextVar
from typing import Any

import structlog

from app.core.config import get_settings

# ── Request ID context (set by middleware per request) ────────────────────────
request_id_var: ContextVar[str] = ContextVar("request_id", default="")
session_id_var: ContextVar[str] = ContextVar("session_id", default="")


def _add_request_context(
    logger: Any,
    method: str,
    event_dict: dict,
) -> dict:
    """Inject request_id and session_id into every log record."""
    if rid := request_id_var.get():
        event_dict["request_id"] = rid
    if sid := session_id_var.get():
        event_dict["session_id"] = sid
    return event_dict


def configure_logging() -> None:
    """
    Bootstrap structlog + stdlib logging.
    Must be called once at application startup (in main.py).
    """
    settings = get_settings()

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        _add_request_context,
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.LOG_FORMAT == "json" or settings.is_production:
        # Production: machine-parseable JSON
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Development: color-coded, human-readable
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.LOG_LEVEL.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    # Also configure stdlib logging to route through structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.getLevelName(settings.LOG_LEVEL.upper()),
    )

    # Silence noisy third-party loggers
    for noisy in ("uvicorn.access", "httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a named logger.

    Args:
        name: Typically __name__ of the calling module.

    Returns:
        Structlog BoundLogger instance.
    """
    return structlog.get_logger(name)
