"""
Storage abstraction interface.

All storage operations go through this interface — never direct filesystem
or boto3 calls from business logic. This allows transparent backend swapping:
  Local → S3 → MinIO → Supabase Storage
with zero changes to calling code.

Keys are logical paths (e.g. "datasets/uuid/raw.csv"), not filesystem paths.
The backend resolves them to actual locations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator, BinaryIO


@dataclass(frozen=True)
class StoredObject:
    """Metadata returned after a successful store operation."""
    key: str           # Logical storage key
    size_bytes: int
    content_type: str
    url: str | None    # Public URL if available (None for private/local)


class BaseStorageBackend(ABC):
    """
    Abstract base class for all storage backends.

    All methods are async to support non-blocking I/O regardless
    of whether the backend is local (file I/O) or remote (S3 API calls).
    """

    @abstractmethod
    async def store(
        self,
        key: str,
        data: bytes | BinaryIO,
        content_type: str = "application/octet-stream",
    ) -> StoredObject:
        """
        Store data at the given key.

        Args:
            key: Logical storage key (e.g. "datasets/abc123/raw.csv")
            data: File contents as bytes or file-like object
            content_type: MIME type of the content

        Returns:
            StoredObject with metadata about the stored file

        Raises:
            StorageError: If the store operation fails
        """
        ...

    @abstractmethod
    async def retrieve(self, key: str) -> bytes:
        """
        Retrieve file contents by key.

        Raises:
            StorageError: If key does not exist or retrieval fails
        """
        ...

    @abstractmethod
    async def stream(self, key: str) -> AsyncIterator[bytes]:
        """
        Stream file contents in chunks (for large files).

        Yields:
            Byte chunks of the file content
        """
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        """
        Delete the object at key.

        Raises:
            StorageError: If key does not exist or deletion fails
        """
        ...

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Return True if an object exists at key."""
        ...

    @abstractmethod
    async def get_size(self, key: str) -> int:
        """Return file size in bytes for the object at key."""
        ...

    @abstractmethod
    def build_key(self, prefix: str, *parts: str) -> str:
        """
        Construct a storage key from prefix and path parts.

        Example:
            build_key("datasets", "uuid-123", "raw.csv")
            → "datasets/uuid-123/raw.csv"
        """
        ...
