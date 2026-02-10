"""
PostgreSQL database client for BSF-LoopTech waste treatment system.
Handles relational data: users, waste records, material types.
"""

from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator
import logging
import uuid

from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer, String, Text, JSON, Boolean, text
from sqlalchemy.dialects.postgresql import UUID, ARRAY
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
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=True)
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

    # Relationships
    supplier_rel = relationship("Supplier", back_populates="waste_records")

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

    # Phase 1 拡張フィールド
    specific_gravity = Column(Float, nullable=True)
    particle_size = Column(Float, nullable=True)
    ph = Column(Float, nullable=True)
    moisture_content = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ── Supplier & Recipe Tables (Phase 1) ──


class Supplier(Base):
    """Supplier master — waste sources / delivery origins."""
    __tablename__ = "suppliers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False, index=True)
    contact_person = Column(String(100), nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(200), nullable=True)
    address = Column(Text, nullable=True)
    waste_types = Column(JSON, nullable=True, default=list)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    waste_records = relationship("WasteRecord", back_populates="supplier_rel")
    recipes = relationship("Recipe", back_populates="supplier_rel")


class SolidificationMaterial(Base):
    """Solidification material master — cement-based, calcium-based, etc."""
    __tablename__ = "solidification_materials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False, unique=True, index=True)
    material_type = Column(String(50), nullable=False, index=True)  # cement, calcium,ite, other
    base_material = Column(String(200), nullable=True)
    effective_components = Column(JSON, nullable=True)
    applicable_soil_types = Column(JSON, nullable=True, default=list)
    min_addition_rate = Column(Float, nullable=True)
    max_addition_rate = Column(Float, nullable=True)
    unit_cost = Column(Float, nullable=True)
    unit = Column(String(20), nullable=True, default="kg")
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class LeachingSuppressant(Base):
    """Leaching suppressant master — agents to control heavy metal elution."""
    __tablename__ = "leaching_suppressants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False, unique=True, index=True)
    suppressant_type = Column(String(100), nullable=False, index=True)
    target_metals = Column(JSON, nullable=True, default=list)
    min_addition_rate = Column(Float, nullable=True)
    max_addition_rate = Column(Float, nullable=True)
    ph_range_min = Column(Float, nullable=True)
    ph_range_max = Column(Float, nullable=True)
    unit_cost = Column(Float, nullable=True)
    unit = Column(String(20), nullable=True, default="kg")
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Recipe(Base):
    """Formulation recipe — header with target specifications."""
    __tablename__ = "recipes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False, index=True)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=True)
    waste_type = Column(String(100), nullable=False, index=True)
    target_strength = Column(Float, nullable=True)
    target_elution = Column(JSON, nullable=True)
    status = Column(String(20), nullable=False, default="draft")  # draft, active, archived
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    supplier_rel = relationship("Supplier", back_populates="recipes")
    details = relationship("RecipeDetail", back_populates="recipe", cascade="all, delete-orphan")


class RecipeDetail(Base):
    """Recipe detail line — individual material addition in a recipe."""
    __tablename__ = "recipe_details"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipe_id = Column(UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
    material_id = Column(UUID(as_uuid=True), nullable=False)
    material_type = Column(String(30), nullable=False)  # solidification, suppressant, other
    addition_rate = Column(Float, nullable=False)
    order_index = Column(Integer, nullable=False, default=0)
    notes = Column(Text, nullable=True)

    # Relationships
    recipe = relationship("Recipe", back_populates="details")

    __table_args__ = (
        Index("ix_recipe_details_recipe_id", "recipe_id"),
    )


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
        # Ensure all Phase 1 models are registered with Base.metadata
        _ = (Supplier, SolidificationMaterial, LeachingSuppressant, Recipe, RecipeDetail)

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
