"""Alembic migration environment for BSF-LoopTech."""

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import create_engine, pool

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment
env_file = os.getenv("ALEMBIC_ENV_FILE", ".env.local")
env_path = Path(__file__).parent.parent / env_file
if not env_path.exists():
    env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

from src.config import settings

config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import models so Base.metadata contains all tables
from src.database.postgresql import (
    Base, WasteRecord, MaterialType,
    Supplier, SolidificationMaterial, LeachingSuppressant,
    Recipe, RecipeDetail,
)
from src.auth.models import User, UserSession, LoginAttempt, APIKey

target_metadata = Base.metadata


def _sync_url(url: str) -> str:
    """Convert async driver URL to sync for Alembic."""
    return url.replace("postgresql+asyncpg://", "postgresql://").replace(
        "sqlite+aiosqlite://", "sqlite://"
    )


def run_migrations_offline() -> None:
    context.configure(
        url=_sync_url(config.get_main_option("sqlalchemy.url")),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(
        _sync_url(config.get_main_option("sqlalchemy.url")),
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
