"""
PostgreSQL database client and operations for BSF Larvae Monitoring System.
Handles relational data including users, sensor devices, substrate management.
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, Text, ForeignKey, JSON
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


class User(Base):
    """User model for authentication and authorization."""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    full_name = Column(String(100), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


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
    category = Column(String(50), nullable=False)  # sewage_sludge, pig_manure, chicken_manure, sawdust, other
    description = Column(Text, nullable=True)
    
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
    metadata = Column(JSON, nullable=True)  # Additional metadata
    
    # Relationship
    rule = relationship("AnomalyRule", backref="detections")


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
            await session.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False