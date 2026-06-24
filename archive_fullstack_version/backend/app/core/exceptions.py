"""
Application exception hierarchy.

All custom exceptions inherit from AppError.
FastAPI exception handlers in middleware.py catch these and
convert them to consistent JSON error responses.

Pattern:
    raise DatasetNotFoundError(dataset_id="abc-123")
    → HTTP 404 { "error": "DATASET_NOT_FOUND", "detail": "...", "meta": {...} }
"""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base class for all application exceptions."""

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"
    message: str = "An unexpected error occurred."

    def __init__(
        self,
        message: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> None:
        self.message = message or self.__class__.message
        self.meta = meta or {}
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": self.error_code,
            "detail": self.message,
            "meta": self.meta,
        }


# ── 400 Bad Request ───────────────────────────────────────────────────────────

class ValidationError(AppError):
    status_code = 400
    error_code = "VALIDATION_ERROR"
    message = "Request validation failed."


class UnsupportedFileTypeError(AppError):
    status_code = 400
    error_code = "UNSUPPORTED_FILE_TYPE"

    def __init__(self, filename: str, allowed: list[str]) -> None:
        super().__init__(
            message=f"File '{filename}' has an unsupported type.",
            meta={"allowed_extensions": allowed},
        )


class FileTooLargeError(AppError):
    status_code = 400
    error_code = "FILE_TOO_LARGE"

    def __init__(self, size_bytes: int, max_bytes: int) -> None:
        super().__init__(
            message=f"File size {size_bytes / 1e6:.1f} MB exceeds limit of {max_bytes / 1e6:.0f} MB.",
            meta={"size_bytes": size_bytes, "max_bytes": max_bytes},
        )


class InvalidDatasetError(AppError):
    status_code = 400
    error_code = "INVALID_DATASET"
    message = "Dataset could not be parsed or is malformed."


# ── 404 Not Found ─────────────────────────────────────────────────────────────

class NotFoundError(AppError):
    status_code = 404
    error_code = "NOT_FOUND"
    message = "Resource not found."


class DatasetNotFoundError(NotFoundError):
    error_code = "DATASET_NOT_FOUND"

    def __init__(self, dataset_id: str) -> None:
        super().__init__(
            message=f"Dataset '{dataset_id}' not found.",
            meta={"dataset_id": dataset_id},
        )


class AnalysisSessionNotFoundError(NotFoundError):
    error_code = "SESSION_NOT_FOUND"

    def __init__(self, session_id: str) -> None:
        super().__init__(
            message=f"Analysis session '{session_id}' not found.",
            meta={"session_id": session_id},
        )


class ReportNotFoundError(NotFoundError):
    error_code = "REPORT_NOT_FOUND"

    def __init__(self, report_id: str) -> None:
        super().__init__(
            message=f"Report '{report_id}' not found.",
            meta={"report_id": report_id},
        )


# ── 401 Unauthorized ─────────────────────────────────────────────────────────

class UnauthorizedError(AppError):
    status_code = 401
    error_code = "UNAUTHORIZED"
    message = "Missing or invalid API key. Set X-API-Key header."


# ── 409 Conflict ──────────────────────────────────────────────────────────────

class ConflictError(AppError):
    status_code = 409
    error_code = "CONFLICT"
    message = "Resource state conflict."


class AnalysisAlreadyRunningError(ConflictError):
    error_code = "ANALYSIS_ALREADY_RUNNING"

    def __init__(self, session_id: str) -> None:
        super().__init__(
            message=f"Analysis session '{session_id}' is already running.",
            meta={"session_id": session_id},
        )


# ── 422 Unprocessable ─────────────────────────────────────────────────────────

class DataProcessingError(AppError):
    status_code = 422
    error_code = "DATA_PROCESSING_ERROR"
    message = "Failed to process dataset."


# ── 500 Internal ──────────────────────────────────────────────────────────────

class StorageError(AppError):
    status_code = 500
    error_code = "STORAGE_ERROR"
    message = "File storage operation failed."


class AgentExecutionError(AppError):
    status_code = 500
    error_code = "AGENT_EXECUTION_ERROR"

    def __init__(self, agent_name: str, reason: str) -> None:
        super().__init__(
            message=f"Agent '{agent_name}' failed: {reason}",
            meta={"agent_name": agent_name, "reason": reason},
        )


class LLMError(AppError):
    status_code = 500
    error_code = "LLM_ERROR"
    message = "LLM API call failed."


class OrchestrationError(AppError):
    status_code = 500
    error_code = "ORCHESTRATION_ERROR"
    message = "Workflow orchestration failed."
