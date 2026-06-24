"""
Analysis sessions API router.

Endpoints:
    POST   /analysis/start            Start a new analysis session
    GET    /analysis                   List sessions (paginated)
    GET    /analysis/{id}             Get session with agent runs
    POST   /analysis/{id}/cancel      Cancel a running session
    GET    /analysis/{id}/events      Replay stored events (for history view)
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.analysis import (
    AnalysisSessionListResponse,
    AnalysisSessionResponse,
    StartAnalysisRequest,
)

router = APIRouter()


@router.post("/start", response_model=AnalysisSessionResponse, status_code=201)
async def start_analysis(
    body: StartAnalysisRequest,
    db: AsyncSession = Depends(get_db),
) -> AnalysisSessionResponse:
    """
    Start a new multi-agent analysis session on a dataset.

    Returns immediately with status=pending.
    Subscribe to GET /stream/{session_id} for real-time events.
    """
    from app.services.analysis_service import AnalysisService
    service = AnalysisService(db)
    session = await service.start(
        dataset_id=body.dataset_id,
        config=body.config,
    )
    return AnalysisSessionResponse.model_validate(session)


@router.get("", response_model=AnalysisSessionListResponse)
async def list_sessions(
    dataset_id: uuid.UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> AnalysisSessionListResponse:
    from app.services.analysis_service import AnalysisService
    service = AnalysisService(db)
    sessions, total = await service.list_sessions(
        dataset_id=dataset_id,
        page=page,
        page_size=page_size,
    )
    return AnalysisSessionListResponse(
        items=[AnalysisSessionResponse.model_validate(s) for s in sessions],
        total=total,
    )


@router.get("/{session_id}", response_model=AnalysisSessionResponse)
async def get_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> AnalysisSessionResponse:
    from app.services.analysis_service import AnalysisService
    service = AnalysisService(db)
    session = await service.get_by_id(session_id)
    return AnalysisSessionResponse.model_validate(session)


@router.post("/{session_id}/cancel", status_code=200)
async def cancel_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    from app.services.analysis_service import AnalysisService
    service = AnalysisService(db)
    await service.cancel(session_id)
    return {"status": "cancelled", "session_id": str(session_id)}
