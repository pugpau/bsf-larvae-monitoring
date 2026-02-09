"""
PostgreSQL database client and operations for BSF Larvae Monitoring System.
Handles relational data including users, sensor devices, substrate management.
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, Text, ForeignKey, JSON, text, Numeric, Index
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from typing import Optional
from datetime import datetime
from typing import AsyncGenerator
import uuid
import logging

from src.config import settings

logger = logging.getLogger(__name__)

# SQLAlchemy Base
Base = declarative_base()

# Database Engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,  # Set to False in production
    pool_pre_ping=True,
    pool_recycle=300,
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class SensorDevice(Base):
    """Sensor device model for device management."""
    __tablename__ = "sensor_devices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(String(50), unique=True, nullable=False, index=True)
    device_type = Column(String(50), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    farm_id = Column(String(50), nullable=False, index=True)
    location = Column(String(100), nullable=True)
    
    # 3D position coordinates
    position_x = Column(Float, nullable=True)
    position_y = Column(Float, nullable=True)
    position_z = Column(Float, nullable=True)
    
    # Device status
    status = Column(String(20), nullable=False, default="active")  # active, inactive, maintenance
    is_online = Column(Boolean, default=False)
    last_seen = Column(DateTime, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship with substrate batches
    substrate_batch_id = Column(UUID(as_uuid=True), ForeignKey("substrate_batches.id"), nullable=True)
    substrate_batch = relationship("SubstrateBatch", back_populates="sensor_devices")


class SubstrateType(Base):
    """Substrate type model for material definitions."""
    __tablename__ = "substrate_types"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True, index=True)
    category = Column(String(50), nullable=False)  # sewage_sludge, pig_manure, chicken_manure, sawdust, solidifier, elution_suppressor, other
    description = Column(Text, nullable=True)

    # Extended material information (Rev.2)
    material_category = Column(String(50), nullable=True)  # raw_material, additive, solidifier, elution_suppressor
    supplier = Column(String(200), nullable=True)
    unit_cost = Column(Numeric(12, 2), nullable=True)  # cost per unit (e.g., per kg)

    # Custom attributes stored as JSON (for flexibility)
    # This will be handled in the repository layer with JSON serialization
    custom_attributes = Column(Text, nullable=True)  # JSON string

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    batch_components = relationship("SubstrateBatchComponent", back_populates="substrate_type")


class SubstrateBatch(Base):
    """Substrate batch model for batch management."""
    __tablename__ = "substrate_batches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    farm_id = Column(String(50), nullable=False, index=True)
    batch_name = Column(String(100), nullable=False)
    batch_number = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    
    # Batch properties
    total_weight = Column(Float, nullable=False)
    weight_unit = Column(String(10), nullable=False, default="kg")
    storage_location = Column(String(100), nullable=True)
    
    # Status and lifecycle
    status = Column(String(20), nullable=False, default="active")  # active, processing, completed, archived
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    components = relationship("SubstrateBatchComponent", back_populates="substrate_batch", cascade="all, delete-orphan")
    sensor_devices = relationship("SensorDevice", back_populates="substrate_batch")


class SubstrateBatchComponent(Base):
    """Junction table for substrate batch composition."""
    __tablename__ = "substrate_batch_components"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    substrate_batch_id = Column(UUID(as_uuid=True), ForeignKey("substrate_batches.id"), nullable=False)
    substrate_type_id = Column(UUID(as_uuid=True), ForeignKey("substrate_types.id"), nullable=False)
    
    # Component properties
    ratio_percentage = Column(Float, nullable=False)  # Should sum to 100% for a batch
    weight = Column(Float, nullable=True)  # Calculated from ratio and total batch weight
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    substrate_batch = relationship("SubstrateBatch", back_populates="components")
    substrate_type = relationship("SubstrateType", back_populates="batch_components")


class AlertRule(Base):
    """Alert rule model for threshold-based monitoring."""
    __tablename__ = "alert_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    # Rule configuration
    farm_id = Column(String(50), nullable=True, index=True)  # Null means global rule
    device_id = Column(String(50), nullable=True, index=True)  # Null means applies to all devices
    measurement_type = Column(String(50), nullable=False)  # temperature, humidity, pressure, etc.
    
    # Threshold configuration
    min_threshold = Column(Float, nullable=True)
    max_threshold = Column(Float, nullable=True)
    operator = Column(String(10), nullable=False)  # >, <, >=, <=, ==, !=
    
    # Alert configuration
    severity = Column(String(20), nullable=False, default="warning")  # info, warning, error, critical
    is_active = Column(Boolean, default=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AnomalyRule(Base):
    """Anomaly detection rule model."""
    __tablename__ = "anomaly_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    # Scope
    farm_id = Column(String(50), nullable=True, index=True)
    device_id = Column(String(50), nullable=True, index=True)
    device_type = Column(String(50), nullable=True)
    
    # Rule definition
    conditions = Column(JSON, nullable=False)  # List of threshold conditions
    condition_logic = Column(String(10), default="AND")  # AND/OR
    
    # Configuration
    severity = Column(String(20), nullable=False)  # info, warning, error, critical
    status = Column(String(20), default="active")  # active, inactive, testing
    evaluation_window = Column(JSON, nullable=True)  # Time window config
    cooldown_period = Column(JSON, nullable=True)  # Cooldown config
    dynamic_threshold = Column(JSON, nullable=True)  # Dynamic threshold config
    
    # Actions
    send_alert = Column(Boolean, default=True)
    auto_control = Column(Boolean, default=False)
    control_commands = Column(JSON, nullable=True)  # Control commands to execute
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(50), nullable=True)
    tags = Column(JSON, nullable=True)  # List of tags


class AnomalyDetection(Base):
    """Anomaly detection instance model."""
    __tablename__ = "anomaly_detections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id = Column(UUID(as_uuid=True), ForeignKey("anomaly_rules.id"), nullable=False)
    rule_name = Column(String(100), nullable=False)
    
    # Detection details
    detected_at = Column(DateTime, default=datetime.utcnow)
    measurement_type = Column(String(50), nullable=False)
    actual_value = Column(Float, nullable=False)
    threshold_value = Column(JSON, nullable=False)  # Can be single value or range
    threshold_type = Column(String(20), nullable=False)
    
    # Context
    farm_id = Column(String(50), nullable=True, index=True)
    device_id = Column(String(50), nullable=True, index=True)
    device_type = Column(String(50), nullable=True)
    location = Column(String(100), nullable=True)
    
    # Status
    severity = Column(String(20), nullable=False)
    status = Column(String(20), default="open")  # open, acknowledged, resolved, false_positive
    
    # Resolution
    acknowledged_by = Column(String(50), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    resolved_by = Column(String(50), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolution_notes = Column(Text, nullable=True)
    
    # Additional data
    sensor_data = Column(JSON, nullable=True)  # Related sensor data
    detection_metadata = Column(JSON, nullable=True)  # Additional metadata
    
    # Relationship
    rule = relationship("AnomalyRule", backref="detections")


# ============================================================
# Rev.2 Tables: Quality, Process, Recipe, Audit
# ============================================================


class QualityTestItem(Base):
    """Quality test item master - defines what can be tested (Cd, Pb, As, F, Cr6+, moisture, etc.)."""
    __tablename__ = "quality_test_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True, index=True)  # e.g. "Cd", "Pb", "含水率"
    display_name = Column(String(200), nullable=True)  # e.g. "カドミウム", "鉛"
    unit = Column(String(30), nullable=False)  # mg/L, mg/kg, %
    regulatory_limit = Column(Float, nullable=True)  # legal limit value
    warning_threshold = Column(Float, nullable=True)  # internal warning value
    test_method = Column(String(200), nullable=True)  # e.g. "JIS K 0102"
    category = Column(String(50), nullable=False, default="heavy_metal")  # heavy_metal, physical, chemical
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    test_results = relationship("QualityTestResult", back_populates="test_item")


class QualityTest(Base):
    """Quality test record - a single test session for a batch/process."""
    __tablename__ = "quality_tests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("substrate_batches.id"), nullable=True, index=True)
    process_record_id = Column(UUID(as_uuid=True), ForeignKey("process_records.id"), nullable=True, index=True)

    test_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    test_type = Column(String(30), nullable=False)  # receiving, in_process, final_product
    sample_id = Column(String(100), nullable=True)  # physical sample identifier
    tested_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)

    status = Column(String(20), nullable=False, default="draft")  # draft, submitted, approved, rejected
    rejection_reason = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    batch = relationship("SubstrateBatch", backref="quality_tests")
    process_record = relationship("ProcessRecord", back_populates="quality_tests")
    tester = relationship("User", foreign_keys=[tested_by])
    approver = relationship("User", foreign_keys=[approved_by])
    results = relationship("QualityTestResult", back_populates="quality_test", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_quality_tests_date_type", "test_date", "test_type"),
    )


class QualityTestResult(Base):
    """Individual test result for one item within a quality test."""
    __tablename__ = "quality_test_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quality_test_id = Column(UUID(as_uuid=True), ForeignKey("quality_tests.id"), nullable=False, index=True)
    quality_test_item_id = Column(UUID(as_uuid=True), ForeignKey("quality_test_items.id"), nullable=False, index=True)

    measured_value = Column(Float, nullable=False)
    is_within_limit = Column(Boolean, nullable=True)  # auto-computed against regulatory_limit
    judgment = Column(String(20), nullable=True)  # pass, fail, warning

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    quality_test = relationship("QualityTest", back_populates="results")
    test_item = relationship("QualityTestItem", back_populates="test_results")


class RecipeTemplate(Base):
    """Recipe template for material blending formulations."""
    __tablename__ = "recipe_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    description = Column(Text, nullable=True)
    target_product_type = Column(String(100), nullable=True)  # e.g. "solidified_sludge", "compost"

    # JSON fields for flexible configuration
    components = Column(JSON, nullable=True)  # [{substrate_type_id, ratio_min, ratio_max, ratio_default}]
    process_parameters = Column(JSON, nullable=True)  # {drying_temp, drying_time, mixing_speed, ...}
    quality_targets = Column(JSON, nullable=True)  # {Cd: {max: 0.45}, Pb: {max: 0.1}, ...}
    constraints = Column(JSON, nullable=True)  # {total_weight_min, total_weight_max, ...}

    status = Column(String(20), nullable=False, default="draft")  # draft, active, deprecated
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    process_records = relationship("ProcessRecord", back_populates="recipe_template")

    __table_args__ = (
        Index("ix_recipe_templates_name_version", "name", "version", unique=True),
    )


class ProcessRecord(Base):
    """Process record for tracking manufacturing steps."""
    __tablename__ = "process_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lot_number = Column(String(50), nullable=False, unique=True, index=True)  # LOT-YYYYMMDD-NNN
    recipe_template_id = Column(UUID(as_uuid=True), ForeignKey("recipe_templates.id"), nullable=True, index=True)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("substrate_batches.id"), nullable=True, index=True)

    process_type = Column(String(30), nullable=False)  # mixing, drying, solidifying, packaging
    status = Column(String(20), nullable=False, default="planned")  # planned, in_progress, completed, aborted
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    operator_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Material tracking
    input_materials = Column(JSON, nullable=True)  # [{substrate_type_id, weight, ...}]
    output_weight = Column(Float, nullable=True)

    # Process parameters recorded
    actual_parameters = Column(JSON, nullable=True)  # {temperature, duration, ...}
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    recipe_template = relationship("RecipeTemplate", back_populates="process_records")
    batch = relationship("SubstrateBatch", backref="process_records")
    operator = relationship("User", foreign_keys=[operator_id])
    quality_tests = relationship("QualityTest", back_populates="process_record")

    __table_args__ = (
        Index("ix_process_records_type_status", "process_type", "status"),
    )


class AuditLog(Base):
    """Audit log for tracking all data operations (Rev.2 compliance)."""
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    username = Column(String(50), nullable=True)

    action = Column(String(20), nullable=False)  # CREATE, UPDATE, DELETE, APPROVE, REJECT, LOGIN, EXPORT
    resource_type = Column(String(50), nullable=False, index=True)  # quality_test, process_record, recipe, etc.
    resource_id = Column(String(50), nullable=True)

    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    changes_summary = Column(Text, nullable=True)  # human-readable summary

    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
        Index("ix_audit_logs_user_time", "user_id", "timestamp"),
    )


# Database dependency for FastAPI
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


# Database initialization functions
async def init_database():
    """Initialize database tables."""
    try:
        # Import all models to ensure they're registered with Base
        from src.auth.models import User, UserSession, LoginAttempt, APIKey
        # Rev.2 models are defined in this file (QualityTestItem, QualityTest, etc.)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


async def close_database():
    """Close database connections."""
    await engine.dispose()
    logger.info("Database connections closed")


# Health check function
async def check_database_health() -> bool:
    """Check if database is accessible."""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False