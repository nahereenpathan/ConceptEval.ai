"""
Application Configuration
Loads strongly-typed settings from environment variables and .env files using Pydantic Settings.
"""

from pathlib import Path
from typing import List, Optional, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _resolve_canonical_sqlite_url(url: str) -> str:
    """Ensure relative SQLite database paths resolve to canonical root database regardless of working directory."""
    if url and url.startswith("sqlite") and ":///" in url:
        prefix, path_part = url.split(":///", 1)
        # Check if already an absolute Windows (e.g. C:/) or Posix path (/...)
        is_windows_abs = len(path_part) > 2 and path_part[1] == ":"
        is_posix_abs = path_part.startswith("/")
        if not is_windows_abs and not is_posix_abs:
            current = Path(__file__).resolve()
            root_dir = None
            for parent in current.parents:
                if (parent / "alembic.ini").exists():
                    root_dir = parent
                    break
            if not root_dir:
                root_dir = current.parents[4]
            rel_clean = path_part.lstrip("./\\")
            abs_db = (root_dir / rel_clean).resolve()
            return f"{prefix}:///{abs_db.as_posix()}"
    return url


class Settings(BaseSettings):
    """Global configuration settings for the API backend."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_ENV: str = "development"
    PROJECT_NAME: str = "Concept-Aware Code Evaluation Platform"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    API_V1_STR: str = "/api/v1"

    # Authentication & Security
    APP_SECRET_KEY: str = Field(
        default="09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7",
        description="Cryptographic secret key for signing JWTs and session cookies"
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ALGORITHM: str = "HS256"

    @field_validator("APP_SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        env = info.data.get("APP_ENV", "development")
        if env == "production" and v == "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7":
            raise ValueError("Insecure default APP_SECRET_KEY cannot be used in production environment!")
        return v

    # Frontend Origin / CORS
    FRONTEND_ORIGIN: Union[str, List[str]] = (
        "http://localhost:5173,http://localhost:5174,http://127.0.0.1:5173,http://127.0.0.1:5174"
    )

    @property
    def cors_origins(self) -> List[str]:
        if isinstance(self.FRONTEND_ORIGIN, list):
            return self.FRONTEND_ORIGIN
        return [o.strip() for o in self.FRONTEND_ORIGIN.split(",") if o.strip()]

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./concept_eval_dev.db"
    DATABASE_URL_SYNC: str = "sqlite:///./concept_eval_dev.db"

    @field_validator("DATABASE_URL", "DATABASE_URL_SYNC", mode="after")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        return _resolve_canonical_sqlite_url(v)

    # Redis & Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    CELERY_TASK_ALWAYS_EAGER: bool = True

    # Execution Runner Sandbox Settings
    EXECUTION_RUNNER_MODE: str = "subprocess"
    EXECUTION_TIMEOUT_SECONDS: float = 5.0
    EXECUTION_MEMORY_LIMIT_MB: int = 128
    EXECUTION_MAX_OUTPUT_BYTES: int = 65536

    # Billing
    BILLING_PROVIDER: str = "stripe"
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    STRIPE_PUBLISHABLE_KEY: Optional[str] = None

    # NLP Intent Provider
    NLP_PROVIDER: str = "baseline"
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None


settings = Settings()
