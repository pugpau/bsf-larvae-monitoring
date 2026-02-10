"""
PostgreSQL database client for BSF-LoopTech waste treatment system.
Handles relational data: users, waste records, material types.
"""

from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator
import logging
import uuid

from sqlalchemy import Column, DateTime, Float, Index, Integer, String, Text, JSON, Boolean, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from src.config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=300,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── Waste Treatment Tables ──


class WasteRecord(Base):
    """Waste treatment incoming record — delivery through formulation to elution testing."""
    __tablename__ = "waste_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source = Column(String(200), nullable=False, index=True)
    delivery_date = Column(DateTime, nullable=False, index=True)
    waste_type = Column(String(100), nullable=False, index=True)
    weight = Column(Float, nullable=True)
    weight_unit = Column(String(10), nullable=False, default="t")

    status = Column(String(20), nullable=False, default="pending")

    analysis = Column(JSON, nullable=True)
    formulation = Column(JSON, nullable=True)
    elution_result = Column(JSON, nullable=True)

    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_waste_records_source_date", "source", "delivery_date"),
    )


class MaterialType(Base):
    """Material type master — solidifiers, elution suppressors, waste type definitions."""
    __tablename__ = "material_types"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False, unique=True, index=True)
    category = Column(String(50), nullable=False, index=True)
    description = Column(Text, nullable=True)
    supplier = Column(String(200), nullable=True)
    unit_cost = Column(Float, nullable=True)
    unit = Column(String(20), nullable=True)
    attributes = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ── Database utilities ──


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session for dependency injection."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()


async def init_database():
    """Create all tables if they don't exist."""
    try:
        from src.auth.models import User, UserSession, LoginAttempt, APIKey

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to initialise database: {e}")
        raise


async def close_database():
    """Close database connections."""
    await engine.dispose()
    logger.info("Database connections closed")


async def check_database_health() -> bool:
    """Check if database is accessible."""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
