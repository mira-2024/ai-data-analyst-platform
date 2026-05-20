"""
Core application configuration.

Single source of truth for all environment-dependent settings.
Uses Pydantic Settings for type-safe env var parsing with validation.
All other modules import from here — never from os.environ directly.
"""

from __future__ import annotations

from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class StorageBackend(str, Enum):
    LOCAL = "local"
    S3 = "s3"
    MINIO = "minio"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────────
    APP_NAME: str = "Multi-Agent Data Analyst"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: Environment = Environment.DEVELOPMENT
    DEBUG: bool = False
    SECRET_KEY: str = Field(
        default="CHANGE_ME_IN_PRODUCTION_USE_openssl_rand_hex_32",
        description="Used for signing tokens. Must be overridden in production.",
    )

    # ── API ───────────────────────────────────────────────────────────────────
    API_V1_PREFIX: str = "/api/v1"
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | List[str]) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://analyst:analyst@localhost:5432/analyst_db",
        description="Async PostgreSQL connection string.",
    )
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_ECHO: bool = False

    # ── Storage ───────────────────────────────────────────────────────────────
    STORAGE_BACKEND: StorageBackend = StorageBackend.LOCAL
    STORAGE_LOCAL_ROOT: Path = Path("storage")
    STORAGE_S3_BUCKET: str = ""
    STORAGE_S3_REGION: str = "us-east-1"
    STORAGE_S3_ACCESS_KEY: str = ""
    STORAGE_S3_SECRET_KEY: str = ""
    STORAGE_S3_ENDPOINT_URL: str = ""
    STORAGE_PREFIX_DATASETS: str = "datasets"
    STORAGE_PREFIX_REPORTS: str = "reports"
    STORAGE_PREFIX_CHARTS: str = "charts"
    STORAGE_PREFIX_ARTIFACTS: str = "artifacts"

    # ── File Upload ───────────────────────────────────────────────────────────
    UPLOAD_MAX_FILE_SIZE_MB: int = 100
    UPLOAD_ALLOWED_EXTENSIONS: List[str] = [
        "csv", "xlsx", "xls", "json", "parquet", "pdf",
    ]

    @property
    def upload_max_bytes(self) -> int:
        return self.UPLOAD_MAX_FILE_SIZE_MB * 1024 * 1024

    # ── AI / LLM ──────────────────────────────────────────────────────────────
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""

    # Primary model for agents
    LLM_PROVIDER: str = "gemini"  # "anthropic" | "gemini" | "openai"
    LLM_MODEL: str = "gemini-2.0-flash"
    LLM_MAX_TOKENS: int = 4096
    LLM_TEMPERATURE: float = 0.0

    # ── Agent Execution ───────────────────────────────────────────────────────
    AGENT_MAX_RETRIES: int = 2
    AGENT_RETRY_DELAY_SECONDS: float = 2.0
    AGENT_EXECUTION_TIMEOUT_SECONDS: int = 300

    # ── SSE Streaming ─────────────────────────────────────────────────────────
    SSE_KEEPALIVE_INTERVAL_SECONDS: int = 15
    SSE_MAX_QUEUE_SIZE: int = 1000

    # ── Logging ───────────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    # ── Auth (stubbed — ready for future implementation) ──────────────────────
    AUTH_ENABLED: bool = False
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == Environment.PRODUCTION

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == Environment.DEVELOPMENT


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return cached Settings instance.

    Use this function everywhere:
        from app.core.config import get_settings
        settings = get_settings()

    The lru_cache ensures .env is only parsed once per process.
    In tests, call get_settings.cache_clear() to reload.
    """
    return Settings()
