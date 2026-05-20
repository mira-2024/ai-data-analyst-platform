"""
API v1 router — aggregates all route modules.

Each sub-router is mounted here with a prefix and tags.
Adding a new resource = add one include_router() call.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import datasets, analysis, agents, reports, stream, health

router = APIRouter()

router.include_router(health.router,   prefix="/health",   tags=["Health"])
router.include_router(datasets.router, prefix="/datasets",  tags=["Datasets"])
router.include_router(analysis.router, prefix="/analysis",  tags=["Analysis"])
router.include_router(agents.router,   prefix="/agents",    tags=["Agents"])
router.include_router(reports.router,  prefix="/reports",   tags=["Reports"])
router.include_router(stream.router,   prefix="/stream",    tags=["Stream"])
