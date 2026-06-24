"""
Local filesystem storage backend.

Implements BaseStorageBackend using the local filesystem.
File structure mirrors the logical key structure:
  storage/datasets/uuid/raw.csv
  storage/reports/uuid/report.pdf
  storage/charts/uuid/chart-001.png

Production note: swap this for S3StorageBackend by changing
STORAGE_BACKEND=s3 in .env. Interface is identical.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import AsyncIterator, BinaryIO

import aiofiles
import aiofiles.os

from app.core.config import get_settings
from app.core.exceptions import StorageError
from app.core.logging import get_logger
from app.storage.base import BaseStorageBackend, StoredObject

logger = get_logger(__name__)
settings = get_settings()

CHUNK_SIZE = 1024 * 1024  # 1 MB streaming chunks


class LocalStorageBackend(BaseStorageBackend):
    """
    Local filesystem storage backend.

    All files stored under settings.STORAGE_LOCAL_ROOT.
    Directory structure is created automatically on first store.
    """

    def __init__(self) -> None:
        self.root = Path(settings.STORAGE_LOCAL_ROOT).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        logger.info("local_storage_initialized", root=str(self.root))

    def _resolve(self, key: str) -> Path:
        """Resolve a logical key to an absolute filesystem path."""
        # Prevent directory traversal attacks
        resolved = (self.root / key).resolve()
        if not str(resolved).startswith(str(self.root)):
            raise StorageError(
                message=f"Invalid storage key: '{key}' escapes storage root."
            )
        return resolved

    async def store(
        self,
        key: str,
        data: bytes | BinaryIO,
        content_type: str = "application/octet-stream",
    ) -> StoredObject:
        path = self._resolve(key)
        try:
            await aiofiles.os.makedirs(path.parent, exist_ok=True)
            if isinstance(data, bytes):
                async with aiofiles.open(path, "wb") as f:
                    await f.write(data)
                size = len(data)
            else:
                # File-like object — read in chunks
                size = 0
                async with aiofiles.open(path, "wb") as f:
                    while chunk := data.read(CHUNK_SIZE):
                        await f.write(chunk)
                        size += len(chunk)

            logger.info("storage_stored", key=key, size_bytes=size)
            return StoredObject(
                key=key,
                size_bytes=size,
                content_type=content_type,
                url=None,  # No public URL for local storage
            )
        except OSError as exc:
            logger.error("storage_store_failed", key=key, error=str(exc))
            raise StorageError(message=f"Failed to store '{key}': {exc}") from exc

    async def retrieve(self, key: str) -> bytes:
        path = self._resolve(key)
        if not path.exists():
            raise StorageError(message=f"Storage key not found: '{key}'")
        try:
            async with aiofiles.open(path, "rb") as f:
                return await f.read()
        except OSError as exc:
            raise StorageError(message=f"Failed to retrieve '{key}': {exc}") from exc

    async def stream(self, key: str) -> AsyncIterator[bytes]:
        path = self._resolve(key)
        if not path.exists():
            raise StorageError(message=f"Storage key not found: '{key}'")
        try:
            async with aiofiles.open(path, "rb") as f:
                while chunk := await f.read(CHUNK_SIZE):
                    yield chunk
        except OSError as exc:
            raise StorageError(message=f"Failed to stream '{key}': {exc}") from exc

    async def delete(self, key: str) -> None:
        path = self._resolve(key)
        if not path.exists():
            raise StorageError(message=f"Storage key not found: '{key}'")
        try:
            await aiofiles.os.remove(path)
            logger.info("storage_deleted", key=key)
        except OSError as exc:
            raise StorageError(message=f"Failed to delete '{key}': {exc}") from exc

    async def exists(self, key: str) -> bool:
        path = self._resolve(key)
        return path.exists()

    async def get_size(self, key: str) -> int:
        path = self._resolve(key)
        if not path.exists():
            raise StorageError(message=f"Storage key not found: '{key}'")
        stat = await aiofiles.os.stat(path)
        return stat.st_size

    def build_key(self, prefix: str, *parts: str) -> str:
        """
        Construct a storage key.

        Example:
            build_key("datasets", "abc-123", "raw.csv")
            → "datasets/abc-123/raw.csv"
        """
        return "/".join([prefix, *parts])
