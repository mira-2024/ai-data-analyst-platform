"""
API key authentication dependency.

All v1 routes (except /health) require an X-API-Key header that matches
the API_KEY setting.  If API_KEY is empty (local dev default), auth is
skipped so the dev experience requires zero configuration.

Usage:
    # Applied once on the v1 router — all child routes inherit it.
    router = APIRouter(dependencies=[Depends(verify_api_key)])

Clients must send:
    X-API-Key: <your-api-key>

Set in .env:
    API_KEY=<random 32-byte hex string>
    # Generate: python -c "import secrets; print(secrets.token_hex(32))"
"""

from __future__ import annotations

from fastapi import Depends, Security
from fastapi.security.api_key import APIKeyHeader

from app.core.config import get_settings
from app.core.exceptions import UnauthorizedError

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(
    api_key: str | None = Security(_api_key_header),
) -> None:
    """
    FastAPI dependency — validates the X-API-Key header.

    If API_KEY setting is empty, the check is bypassed (development mode).
    Returns None on success; raises UnauthorizedError (HTTP 401) on failure.
    """
    settings = get_settings()
    expected = settings.API_KEY

    # Dev mode: no key configured → open access
    if not expected:
        return

    if not api_key or api_key != expected:
        raise UnauthorizedError()
