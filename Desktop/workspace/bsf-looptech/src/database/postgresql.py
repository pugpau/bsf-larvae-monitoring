"""
PostgreSQL database client for BSF-LoopTech waste treatment system.
Handles relational data: users, waste records, material types.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
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

_engine_kwargs: dict = {
    "echo": False,
    "pool_pre_ping": True,
    "pool_recycle": 300,
}
# pool_size / max_overflow only apply to QueuePool (PostgreSQL).
# SQLite uses StaticPool and rejects these kwargs.
if "sqlite" not in settings.DATABASE_URL:
    _engine_kwargs["pool_size"] = 5
    _engine_kwargs["max_overflow"] = 10

engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)

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

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

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

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


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

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    waste_records = relationship("WasteRecord", back_populates="supplier_rel")
    recipes = relationship("Recipe", back_populates="supplier_rel")
    incoming_materials = relationship("IncomingMaterial", back_populates="supplier_rel")


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

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


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

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


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

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    current_version = Column(Integer, nullable=False, default=1, server_default="1")

    # Relationships
    supplier_rel = relationship("Supplier", back_populates="recipes")
    details = relationship("RecipeDetail", back_populates="recipe", cascade="all, delete-orphan")
    versions = relationship("RecipeVersion", back_populates="recipe", cascade="all, delete-orphan")


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


# ── Recipe Versions (バージョン管理) ──


class RecipeVersion(Base):
    """Snapshot of a recipe at a specific version."""
    __tablename__ = "recipe_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipe_id = Column(UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
    version = Column(Integer, nullable=False)
    name = Column(String(200), nullable=False)
    supplier_id = Column(UUID(as_uuid=True), nullable=True)
    waste_type = Column(String(100), nullable=False)
    target_strength = Column(Float, nullable=True)
    target_elution = Column(JSON, nullable=True)
    status = Column(String(20), nullable=False)
    notes = Column(Text, nullable=True)
    change_summary = Column(Text, nullable=True)
    created_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    recipe = relationship("Recipe", back_populates="versions")
    details = relationship("RecipeVersionDetail", back_populates="version_record", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_recipe_versions_recipe_id", "recipe_id"),
        Index("uq_recipe_versions_recipe_version", "recipe_id", "version", unique=True),
    )


class RecipeVersionDetail(Base):
    """Snapshot of a recipe detail line at a specific version."""
    __tablename__ = "recipe_version_details"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version_id = Column(UUID(as_uuid=True), ForeignKey("recipe_versions.id", ondelete="CASCADE"), nullable=False)
    material_id = Column(UUID(as_uuid=True), nullable=False)
    material_type = Column(String(30), nullable=False)
    addition_rate = Column(Float, nullable=False)
    order_index = Column(Integer, nullable=False, default=0)
    notes = Column(Text, nullable=True)

    # Relationships
    version_record = relationship("RecipeVersion", back_populates="details")

    __table_args__ = (
        Index("ix_recipe_version_details_version_id", "version_id"),
    )


# ── Incoming Materials & Delivery Schedules (Phase 6) ──


class IncomingMaterial(Base):
    """搬入物マスター — 3-level hierarchy: Supplier -> Category -> Name."""
    __tablename__ = "incoming_materials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=False)
    material_category = Column(String(100), nullable=False, index=True)
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    default_weight_unit = Column(String(10), nullable=False, default="t")
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    supplier_rel = relationship("Supplier", back_populates="incoming_materials")
    delivery_schedules = relationship("DeliverySchedule", back_populates="incoming_material_rel")

    __table_args__ = (
        Index("ix_incoming_materials_supplier_category", "supplier_id", "material_category"),
    )


class DeliverySchedule(Base):
    """搬入予定 — scheduled delivery with auto WasteRecord creation."""
    __tablename__ = "delivery_schedules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incoming_material_id = Column(UUID(as_uuid=True), ForeignKey("incoming_materials.id"), nullable=False)
    scheduled_date = Column(DateTime, nullable=False, index=True)
    estimated_weight = Column(Float, nullable=True)
    actual_weight = Column(Float, nullable=True)
    weight_unit = Column(String(10), nullable=False, default="t")
    status = Column(String(20), nullable=False, default="scheduled")
    waste_record_id = Column(UUID(as_uuid=True), ForeignKey("waste_records.id"), nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    incoming_material_rel = relationship("IncomingMaterial", back_populates="delivery_schedules")
    waste_record_rel = relationship("WasteRecord", backref="delivery_schedule")

    __table_args__ = (
        Index("ix_delivery_schedules_status_date", "status", "scheduled_date"),
    )


# ── Formulation Workflow (搬入→配合連携) ──


class FormulationRecord(Base):
    """Formulation record linking WasteRecord to Recipe with planned/actual values."""
    __tablename__ = "formulation_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    waste_record_id = Column(UUID(as_uuid=True), ForeignKey("waste_records.id"), nullable=False)
    recipe_id = Column(UUID(as_uuid=True), ForeignKey("recipes.id"), nullable=True)
    recipe_version = Column(Integer, nullable=True)
    prediction_id = Column(UUID(as_uuid=True), ForeignKey("ml_predictions.id"), nullable=True)

    source_type = Column(String(20), nullable=False, default="manual")  # manual, ml, similarity, rule, optimization, recipe
    status = Column(String(20), nullable=False, default="proposed")  # proposed, accepted, applied, verified, rejected

    planned_formulation = Column(JSON, nullable=True)  # {solidifierType, solidifierAmount, suppressorType, suppressorAmount, ...}
    actual_formulation = Column(JSON, nullable=True)
    elution_result = Column(JSON, nullable=True)
    elution_passed = Column(Boolean, nullable=True)

    estimated_cost = Column(Float, nullable=True)
    actual_cost = Column(Float, nullable=True)
    confidence = Column(Float, nullable=True)
    reasoning = Column(JSON, nullable=True)  # list of reasoning strings

    notes = Column(Text, nullable=True)
    created_by = Column(UUID(as_uuid=True), nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    waste_record = relationship("WasteRecord", backref="formulation_records")
    recipe = relationship("Recipe", backref="formulation_records")

    __table_args__ = (
        Index("ix_formulation_records_waste_record", "waste_record_id"),
        Index("ix_formulation_records_status", "status"),
        Index("ix_formulation_records_created", "created_at"),
    )


# ── ML Pipeline Tables (Phase 3) ──


class MLModel(Base):
    """Trained ML model metadata — versioning, metrics, activation status."""
    __tablename__ = "ml_models"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, index=True)
    model_type = Column(String(30), nullable=False)  # classifier, regressor
    version = Column(Integer, nullable=False, default=1)
    file_path = Column(String(500), nullable=False)

    training_records = Column(Integer, nullable=False)
    feature_columns = Column(JSON, nullable=True)
    target_columns = Column(JSON, nullable=True)
    metrics = Column(JSON, nullable=False)

    is_active = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_ml_models_type_active", "model_type", "is_active"),
    )


class MLPrediction(Base):
    """Prediction audit log — tracks each prediction for feedback and accuracy."""
    __tablename__ = "ml_predictions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    waste_record_id = Column(UUID(as_uuid=True), ForeignKey("waste_records.id"), nullable=True)
    model_id = Column(UUID(as_uuid=True), ForeignKey("ml_models.id"), nullable=True)

    input_features = Column(JSON, nullable=False)
    prediction = Column(JSON, nullable=False)
    method = Column(String(20), nullable=False)  # ml, similarity, rule
    confidence = Column(Float, nullable=True)

    actual_formulation = Column(JSON, nullable=True)
    actual_passed = Column(Boolean, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_ml_predictions_waste_record", "waste_record_id"),
        Index("ix_ml_predictions_created", "created_at"),
    )


# ── RAG / Chat Tables (Phase 4) ──


class SubstrateKnowledge(Base):
    """Knowledge base for RAG — chunked text with vector embeddings."""
    __tablename__ = "substrate_knowledge"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(200), nullable=False, index=True)
    content = Column(Text, nullable=False)
    source_type = Column(String(50), nullable=False, default="manual")  # manual, csv_import, web
    metadata_json = Column(JSON, nullable=True)
    embedding = Column(Text, nullable=True)  # pgvector Vector(768) handled at migration level

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class ChatSession(Base):
    """Chat session — groups related chat messages."""
    __tablename__ = "chat_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=True)  # nullable for SKIP_AUTH
    title = Column(String(200), nullable=False, default="New Chat")

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan",
                            order_by="ChatMessage.created_at")


class ChatMessage(Base):
    """Individual chat message within a session."""
    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    context_chunks = Column(JSON, nullable=True)  # referenced knowledge IDs + scores
    token_count = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    session = relationship("ChatSession", back_populates="messages")

    __table_args__ = (
        Index("ix_chat_messages_session_id", "session_id"),
        Index("ix_chat_messages_created", "created_at"),
    )


# ── Batch Processing Tables (Phase 5) ──


class BatchJobRun(Base):
    """Batch job execution record — tracks scheduled and manual job runs."""
    __tablename__ = "batch_job_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_name = Column(String(100), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="running")  # running, success, failed
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)
    result_summary = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_batch_job_runs_name_started", "job_name", "started_at"),
    )


# ── Activity Logs ──


class ActivityLog(Base):
    """Persistent audit trail for workflow events."""
    __tablename__ = "activity_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(50), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action = Column(String(50), nullable=False)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(String(20), nullable=False, default="info")
    metadata_json = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_activity_logs_entity", "entity_type", "entity_id"),
        Index("ix_activity_logs_user_created", "user_id", "created_at"),
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
        # Ensure all models are registered with Base.metadata
        _ = (Supplier, SolidificationMaterial, LeachingSuppressant, Recipe, RecipeDetail,
             FormulationRecord,
             MLModel, MLPrediction, SubstrateKnowledge, ChatSession, ChatMessage,
             BatchJobRun, ActivityLog)

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
