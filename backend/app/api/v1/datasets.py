"""
Datasets API router.

Thin controller layer — validates input, delegates to DatasetService,
returns typed responses. No business logic here.

Endpoints:
    POST   /datasets/upload          Upload a dataset file
    GET    /datasets                  List all datasets (paginated)
    GET    /datasets/{id}             Get single dataset with schema/preview
    PATCH  /datasets/{id}             Update name/description
    DELETE /datasets/{id}             Delete dataset and all analysis sessions
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.exceptions import FileTooLargeError, UnsupportedFileTypeError
from app.schemas.dataset import (
    DatasetListResponse,
    DatasetResponse,
    DatasetUpdateRequest,
)

router = APIRouter()
settings = get_settings()


@router.post("/upload", response_model=DatasetResponse, status_code=201)
async def upload_dataset(
    file: UploadFile = File(...),
    name: str | None = Form(default=None),
    description: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
) -> DatasetResponse:
    """
    Upload a dataset file (CSV, Excel, JSON, Parquet, PDF).

    The file is stored in object storage and profiled asynchronously.
    Returns immediately with status=pending — poll GET /datasets/{id}
    or subscribe to SSE stream for profiling completion.
    """
    # ── Validate file extension ───────────────────────────────────────────────
    filename = file.filename or ""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in settings.UPLOAD_ALLOWED_EXTENSIONS:
        raise UnsupportedFileTypeError(
            filename=filename,
            allowed=settings.UPLOAD_ALLOWED_EXTENSIONS,
        )

    # ── Validate file size ────────────────────────────────────────────────────
    # Read content once so we can check the size before storage.
    content = await file.read()
    if len(content) > settings.upload_max_bytes:
        raise FileTooLargeError(
            size_bytes=len(content),
            max_bytes=settings.upload_max_bytes,
        )
    # Seek back so DatasetService can read from the beginning.
    await file.seek(0)

    from app.services.dataset_service import DatasetService
    service = DatasetService(db)
    dataset = await service.upload(
        file=file,
        name=name or file.filename or "Untitled Dataset",
        description=description,
    )
    return DatasetResponse.model_validate(dataset)


@router.get("", response_model=DatasetListResponse)
async def list_datasets(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> DatasetListResponse:
    from app.services.dataset_service import DatasetService
    service = DatasetService(db)
    datasets, total = await service.list_datasets(page=page, page_size=page_size)
    return DatasetListResponse(
        items=[DatasetResponse.model_validate(d) for d in datasets],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(
    dataset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> DatasetResponse:
    from app.services.dataset_service import DatasetService
    service = DatasetService(db)
    dataset = await service.get_by_id(dataset_id)
    return DatasetResponse.model_validate(dataset)


@router.patch("/{dataset_id}", response_model=DatasetResponse)
async def update_dataset(
    dataset_id: uuid.UUID,
    body: DatasetUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> DatasetResponse:
    from app.services.dataset_service import DatasetService
    service = DatasetService(db)
    dataset = await service.update(dataset_id, body)
    return DatasetResponse.model_validate(dataset)


@router.delete("/{dataset_id}", status_code=200)
async def delete_dataset(
    dataset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    from app.services.dataset_service import DatasetService
    service = DatasetService(db)
    await service.delete(dataset_id)
    return {"deleted": True}
