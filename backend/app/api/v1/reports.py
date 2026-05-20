"""Reports API."""
from __future__ import annotations
import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.report import ReportResponse

router = APIRouter()

@router.get("/{session_id}", response_model=ReportResponse)
async def get_report(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ReportResponse:
    from app.services.report_service import ReportService
    service = ReportService(db)
    report = await service.get_by_session(session_id)
    return ReportResponse.model_validate(report)
