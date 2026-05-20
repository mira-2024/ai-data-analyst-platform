"""
Storage layer factory.

Returns the correct backend based on STORAGE_BACKEND env var.
All application code imports get_storage() — never a specific backend directly.

Usage:
    from app.storage import get_storage
    storage = get_storage()
    obj = await storage.store("datasets/uuid/raw.csv", data)
"""

from __future__ import annotations

from functools import lru_cache

from app.core.config import StorageBackend, get_settings
from app.storage.base import BaseStorageBackend

_settings = get_settings()


@lru_cache(maxsize=1)
def get_storage() -> BaseStorageBackend:
    """
    Return the configured storage backend singleton.

    Cached after first call — backend is created once per process.
    """
    backend = _settings.STORAGE_BACKEND

    if backend == StorageBackend.LOCAL:
        from app.storage.local import LocalStorageBackend
        return LocalStorageBackend()

    if backend == StorageBackend.S3:
        # Future: from app.storage.s3 import S3StorageBackend
        raise NotImplementedError("S3 storage backend not yet implemented.")

    if backend == StorageBackend.MINIO:
        # Future: from app.storage.minio import MinIOStorageBackend
        raise NotImplementedError("MinIO storage backend not yet implemented.")

    raise ValueError(f"Unknown storage backend: {backend!r}")


__all__ = ["get_storage", "BaseStorageBackend"]
