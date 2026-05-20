"""
FastAPI middleware stack.

Registered in main.py in order:
1. RequestIDMiddleware  — injects X-Request-ID into every request/response
2. LoggingMiddleware    — logs method, path, status, duration for every request
3. ErrorHandlerMiddleware — catches AppError and converts to JSON responses
4. CORS                 — configured from settings.ALLOWED_ORIGINS
"""

from __future__ import annotations

import time
import uuid
from typing import Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.logging import get_logger, request_id_var

logger = get_logger(__name__)
settings = get_settings()


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Attach a unique request ID to every request.

    Reads X-Request-ID from incoming headers (allowing upstream proxies
    to propagate IDs). Generates a new UUID if not present.
    Sets the ID in both the context var (for logging) and response header.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = request_id_var.set(request_id)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            request_id_var.reset(token)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Log every HTTP request with method, path, status code, and duration.
    Skips /health and /metrics endpoints to avoid log spam.
    """

    SKIP_PATHS = {"/health", "/metrics", "/favicon.ico"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        logger.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
            client_host=request.client.host if request.client else None,
        )
        return response


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register global exception handlers on the FastAPI app.
    Must be called after app creation, before startup.
    """

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        logger.warning(
            "app_error",
            error_code=exc.error_code,
            message=exc.message,
            meta=exc.meta,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict(),
        )

    @app.exception_handler(Exception)
    async def handle_unhandled_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "unhandled_error",
            path=request.url.path,
            exc_info=exc,
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "INTERNAL_ERROR",
                "detail": "An unexpected error occurred.",
                "meta": {},
            },
        )


def register_middleware(app: FastAPI) -> None:
    """
    Register all middleware on the FastAPI application.
    Call this in main.py before any routes are mounted.

    Order matters: middleware is applied bottom-up (last registered = outermost).
    """
    # CORS — must be outermost
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    # Logging
    app.add_middleware(LoggingMiddleware)

    # Request ID injection
    app.add_middleware(RequestIDMiddleware)
