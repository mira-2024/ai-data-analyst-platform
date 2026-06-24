"""
API v1 router — aggregates all route modules.

Each sub-router is mounted here with a prefix and tags.
Adding a new resource = add one include_router() call.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.v1 import datasets, analysis, agents, reports, stream, health
from app.core.auth import verify_api_key

# /health is exempt — monitoring infra must not need a key.
# All other v1 routes require X-API-Key (no-op when API_KEY is empty).
router = APIRouter()

router.include_router(health.router, prefix="/health", tags=["Health"])

_auth = [Depends(verify_api_key)]
router.include_router(datasets.router, prefix="/datasets",  tags=["Datasets"],  dependencies=_auth)
router.include_router(analysis.router, prefix="/analysis",  tags=["Analysis"],  dependencies=_auth)
router.include_router(agents.router,   prefix="/agents",    tags=["Agents"],    dependencies=_auth)
router.include_router(reports.router,  prefix="/reports",   tags=["Reports"],   dependencies=_auth)
router.include_router(stream.router,   prefix="/stream",    tags=["Stream"],    dependencies=_auth)
