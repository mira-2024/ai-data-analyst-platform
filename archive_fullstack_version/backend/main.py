"""
FastAPI application entry point.

Bootstraps:
1. Structured logging
2. FastAPI app with OpenAPI metadata
3. Middleware stack (CORS, request ID, logging)
4. Exception handlers
5. API v1 router
6. DB connection lifecycle
7. Health check

Run with:
    uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.database import check_connection, dispose_engine
from app.core.logging import configure_logging, get_logger
from app.core.middleware import register_exception_handlers, register_middleware

# Bootstrap logging before anything else
configure_logging()
logger = get_logger(__name__)
settings = get_settings()


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    logger.info(
        "application_starting",
        name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
    )

    # Verify DB connectivity on startup
    db_ok = await check_connection()
    if not db_ok:
        logger.error("database_unreachable_on_startup")
        # Don't crash — allow health endpoint to report degraded status
    else:
        logger.info("database_connected")

    logger.info("application_ready")
    yield

    # Shutdown
    logger.info("application_shutting_down")
    await dispose_engine()
    logger.info("application_stopped")


# ── App factory ───────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "Multi-Agent AI Data Analyst Platform. "
            "Upload datasets and let collaborative AI agents clean, analyze, "
            "visualize, and generate insights from your data."
        ),
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # Middleware (order: outermost to innermost)
    register_middleware(app)

    # Exception handlers
    register_exception_handlers(app)

    # API routes
    from app.api.v1.router import router as v1_router
    app.include_router(v1_router, prefix=settings.API_V1_PREFIX)

    # Health check (outside API versioning)
    @app.get("/health", tags=["System"], include_in_schema=True)
    async def health() -> JSONResponse:
        db_ok = await check_connection()
        status = "healthy" if db_ok else "degraded"
        return JSONResponse(
            status_code=200 if db_ok else 503,
            content={
                "status": status,
                "version": settings.APP_VERSION,
                "environment": settings.ENVIRONMENT,
                "database": "connected" if db_ok else "unreachable",
            },
        )

    return app


app = create_app()
