"""
Application settings for BSF-LoopTech waste treatment system.
"""

import logging
import os
from typing import Optional

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load .env.local, fallback to .env
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env.local")
if not os.path.exists(dotenv_path):
    dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(dotenv_path=dotenv_path)


class Settings:
    """Application settings loaded from environment variables."""

    def __init__(self):
        # PostgreSQL
        self.POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
        self.POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
        self.POSTGRES_USER: str = os.getenv("POSTGRES_USER", "bsf_user")
        self.POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "bsf_password")
        self.POSTGRES_DB: str = os.getenv("POSTGRES_DB", "bsf_system")
        self.DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")

        # Security
        self.SECRET_KEY: str = os.getenv("SECRET_KEY", "")
        self.ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
        if not self.SECRET_KEY:
            if self.ENVIRONMENT == "production":
                raise RuntimeError(
                    "SECRET_KEY must be set in production. "
                    "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
                )
            logger.warning(
                "SECRET_KEY is not set. Using a random key (sessions will not persist across restarts)."
            )
            import secrets as _secrets
            self.SECRET_KEY = _secrets.token_urlsafe(32)
        self.LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

        # CORS (comma-separated origins)
        self.CORS_ORIGINS: str = os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000,http://localhost:3003",
        )

        # ML model registry
        self.MODEL_REGISTRY_PATH: str = os.getenv("MODEL_REGISTRY_PATH", "model_registry/models")

        # Rate limiting
        self.RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))

        # LLM (LM Studio)
        self.LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "http://127.0.0.1:1234/v1")
        self.LLM_MODEL: str = os.getenv("LLM_MODEL", "openai/gpt-oss-20b")

        # Batch processing (Phase 5)
        self.BATCH_ENABLED: bool = os.getenv("BATCH_ENABLED", "true").lower() == "true"
        self.BATCH_TIMEZONE: str = os.getenv("BATCH_TIMEZONE", "Asia/Tokyo")

        # Fail-fast: reject default DB password in production
        if self.ENVIRONMENT == "production" and self.POSTGRES_PASSWORD == "bsf_password":
            raise RuntimeError(
                "Default POSTGRES_PASSWORD must not be used in production. "
                "Set POSTGRES_PASSWORD to a secure value."
            )

        # Construct DATABASE_URL if not provided
        if not self.DATABASE_URL:
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )


settings = Settings()
