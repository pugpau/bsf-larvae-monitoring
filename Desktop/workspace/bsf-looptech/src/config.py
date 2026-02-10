"""
Application settings for BSF-LoopTech waste treatment system.
"""

import os
from typing import Optional

from dotenv import load_dotenv

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
        self.SECRET_KEY: str = os.getenv("SECRET_KEY", "default_secret_key")
        self.LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

        # CORS (comma-separated origins)
        self.CORS_ORIGINS: str = os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000,http://localhost:3001",
        )

        # Construct DATABASE_URL if not provided
        if not self.DATABASE_URL:
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )


settings = Settings()
