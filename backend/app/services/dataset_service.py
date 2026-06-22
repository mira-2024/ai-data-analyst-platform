"""
DatasetService — full dataset lifecycle management.

Responsibilities:
  - Validate uploaded files (type, size)
  - Store raw file in object storage
  - Create and persist Dataset DB record
  - Trigger async dataset profiling
  - CRUD operations (list, get, update, delete)

Architecture note:
  Processing (loader, profiler) runs in a threadpool via asyncio.to_thread()
  so it never blocks the async event loop, even for large CSV files.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import (
    DatasetNotFoundError,
    FileTooLargeError,
    UnsupportedFileTypeError,
    DataProcessingError,
)
from app.core.logging import get_logger
from app.models.dataset import Dataset, DatasetStatus
from app.processing.loader import load_from_bytes
from app.processing.profiler import profile
from app.schemas.dataset import DatasetUpdateRequest
from app.storage import get_storage

logger = get_logger(__name__)
settings = get_settings()


class DatasetService:
    """
    All dataset operations flow through this service.

    Instantiated per-request with the request's DB session.
    Background tasks (profiling) use a fresh session via get_session().
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.storage = get_storage()

    # ── Upload ────────────────────────────────────────────────────────────────

    async def upload(
        self,
        file: UploadFile,
        name: str,
        description: str | None = None,
    ) -> Dataset:
        """
        Handle a dataset file upload end-to-end.

        Steps:
        1. Read file bytes
        2. Validate size and extension
        3. Store file in object storage
        4. Create Dataset record in DB (status=pending)
        5. Launch profiling as a background task
        6. Return Dataset record immediately
        """
        # 1. Read file into memory (enforces size limit)
        data = await file.read()
        file_size = len(data)

        # 2. Validate
        self._validate_size(file_size)
        ext = self._validate_extension(file.filename or "")

        # 3. Store raw file
        dataset_id = uuid.uuid4()
        file_key = self.storage.build_key(
            settings.STORAGE_PREFIX_DATASETS,
            str(dataset_id),
            f"raw.{ext}",
        )
        stored = await self.storage.store(
            key=file_key,
            data=data,
            content_type=file.content_type or "application/octet-stream",
        )

        logger.info(
            "dataset_file_stored",
            dataset_id=str(dataset_id),
            file_key=file_key,
            size_bytes=file_size,
        )

        # 4. Create DB record
        dataset = Dataset(
            id=dataset_id,
            name=name,
            description=description,
            original_filename=file.filename or f"upload.{ext}",
            file_key=file_key,
            file_size_bytes=stored.size_bytes,
            mime_type=file.content_type or "application/octet-stream",
            file_extension=ext,
            status=DatasetStatus.PENDING,
        )
        self.db.add(dataset)
        await self.db.flush()

        logger.info(
            "dataset_record_created",
            dataset_id=str(dataset_id),
            name=name,
        )

        # 5. Launch profiling in background (non-blocking)
        asyncio.create_task(
            self._profile_in_background(dataset_id=dataset_id, data=data, filename=file.filename or f"upload.{ext}")
        )

        return dataset

    async def _profile_in_background(
        self,
        dataset_id: uuid.UUID,
        data: bytes,
        filename: str,
    ) -> None:
        """
        Profile the dataset in a background task.

        Uses a fresh DB session (not the request session which may be closed).
        Runs CPU-bound pandas work in a threadpool via asyncio.to_thread().
        Updates dataset record with profiling results.
        """
        from app.core.database import get_session

        logger.info("dataset_profiling_started", dataset_id=str(dataset_id))

        async with get_session() as db:
            try:
                # Mark as profiling
                await self._update_status(db, dataset_id, DatasetStatus.PROFILING)

                # Run pandas loading + profiling in threadpool (non-blocking)
                df = await asyncio.to_thread(load_from_bytes, data, filename)
                dataset_profile = await asyncio.to_thread(profile, df)

                # Update dataset record with profiling results
                result = await db.execute(
                    select(Dataset).where(Dataset.id == dataset_id)
                )
                dataset = result.scalar_one_or_none()
                if dataset is None:
                    logger.error(
                        "dataset_not_found_during_profiling",
                        dataset_id=str(dataset_id),
                    )
                    return

                dataset.status = DatasetStatus.READY
                dataset.row_count = dataset_profile.row_count
                dataset.column_count = dataset_profile.column_count

                # Merge ColumnSchema + ColumnStatistics so each column dict has
                # both null_count (from schema) and null_pct + numeric stats (from stats)
                row_count = dataset_profile.row_count
                merged_columns = []
                for col_schema, col_stats in zip(
                    dataset_profile.columns, dataset_profile.statistics
                ):
                    col_dict = col_schema.model_dump()
                    col_dict["null_pct"] = col_stats.null_pct
                    if col_stats.mean is not None:
                        col_dict["mean"] = col_stats.mean
                        col_dict["std"] = col_stats.std
                        col_dict["min"] = col_stats.min
                        col_dict["max"] = col_stats.max
                    merged_columns.append(col_dict)
                dataset.schema_json = merged_columns

                dataset.preview_json = dataset_profile.preview_rows

                # Build a summary dict (not a list) for statistics_json so the
                # frontend DatasetProfile type is satisfied
                total_cells = row_count * dataset_profile.column_count
                null_cells = sum(
                    int((s.null_pct / 100) * row_count)
                    for s in dataset_profile.statistics
                )
                overall_null_rate = (
                    round(null_cells / total_cells * 100, 2) if total_cells > 0 else 0.0
                )
                quality_score = round(max(0.0, (100.0 - overall_null_rate) / 100.0), 3)

                likely_datetime = [
                    col.name for col in dataset_profile.columns
                    if any(
                        kw in col.name.lower()
                        for kw in ("date", "time", "timestamp", "created", "updated")
                    )
                ]
                likely_id = [
                    col.name for col in dataset_profile.columns
                    if col.unique_count is not None
                    and col.unique_count == row_count
                    and row_count > 0
                    and (
                        col.name.lower() in ("id", "uuid", "key")
                        or col.name.lower().endswith("_id")
                        or col.name.lower().endswith("_key")
                        or col.name.lower().endswith("uuid")
                    )
                ]
                dataset.statistics_json = {
                    "quality_score": quality_score,
                    "row_count": row_count,
                    "column_count": dataset_profile.column_count,
                    "likely_datetime_columns": likely_datetime,
                    "likely_id_columns": likely_id,
                    "overall_null_rate_pct": overall_null_rate,
                }
                dataset.updated_at = datetime.now(tz=timezone.utc)

                logger.info(
                    "dataset_profiling_completed",
                    dataset_id=str(dataset_id),
                    rows=dataset_profile.row_count,
                    columns=dataset_profile.column_count,
                )

            except (DataProcessingError, UnsupportedFileTypeError) as exc:
                logger.warning(
                    "dataset_profiling_failed",
                    dataset_id=str(dataset_id),
                    error=str(exc),
                )
                await self._update_status(
                    db, dataset_id, DatasetStatus.ERROR,
                    error_message=str(exc),
                )
            except Exception as exc:
                logger.exception(
                    "dataset_profiling_unexpected_error",
                    dataset_id=str(dataset_id),
                    error=str(exc),
                )
                await self._update_status(
                    db, dataset_id, DatasetStatus.ERROR,
                    error_message=f"Unexpected profiling error: {exc}",
                )

    # ── Queries ───────────────────────────────────────────────────────────────

    async def get_by_id(self, dataset_id: uuid.UUID) -> Dataset:
        result = await self.db.execute(
            select(Dataset).where(Dataset.id == dataset_id)
        )
        dataset = result.scalar_one_or_none()
        if dataset is None:
            raise DatasetNotFoundError(dataset_id=str(dataset_id))
        return dataset

    async def list_datasets(
        self,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Dataset], int]:
        offset = (page - 1) * page_size

        total_result = await self.db.execute(
            select(func.count()).select_from(Dataset)
        )
        total = total_result.scalar_one()

        result = await self.db.execute(
            select(Dataset)
            .order_by(Dataset.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        datasets = list(result.scalars().all())

        return datasets, total

    # ── Mutations ─────────────────────────────────────────────────────────────

    async def update(
        self,
        dataset_id: uuid.UUID,
        body: DatasetUpdateRequest,
    ) -> Dataset:
        dataset = await self.get_by_id(dataset_id)
        if body.name is not None:
            dataset.name = body.name
        if body.description is not None:
            dataset.description = body.description
        dataset.updated_at = datetime.now(tz=timezone.utc)
        await self.db.flush()
        return dataset

    async def delete(self, dataset_id: uuid.UUID) -> None:
        dataset = await self.get_by_id(dataset_id)

        # Delete file from storage
        try:
            await self.storage.delete(dataset.file_key)
        except Exception as exc:
            # Log but don't block DB deletion
            logger.warning(
                "dataset_storage_delete_failed",
                dataset_id=str(dataset_id),
                file_key=dataset.file_key,
                error=str(exc),
            )

        await self.db.delete(dataset)
        await self.db.flush()

        logger.info("dataset_deleted", dataset_id=str(dataset_id))

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _validate_size(self, size_bytes: int) -> None:
        if size_bytes > settings.upload_max_bytes:
            raise FileTooLargeError(
                size_bytes=size_bytes,
                max_bytes=settings.upload_max_bytes,
            )

    def _validate_extension(self, filename: str) -> str:
        from pathlib import Path
        ext = Path(filename).suffix.lower().lstrip(".")
        if ext not in settings.UPLOAD_ALLOWED_EXTENSIONS:
            raise UnsupportedFileTypeError(
                filename=filename,
                allowed=settings.UPLOAD_ALLOWED_EXTENSIONS,
            )
        return ext

    @staticmethod
    async def _update_status(
        db: AsyncSession,
        dataset_id: uuid.UUID,
        status: DatasetStatus,
        error_message: str | None = None,
    ) -> None:
        result = await db.execute(
            select(Dataset).where(Dataset.id == dataset_id)
        )
        dataset = result.scalar_one_or_none()
        if dataset:
            dataset.status = status
            dataset.error_message = error_message
            dataset.updated_at = datetime.now(tz=timezone.utc)
