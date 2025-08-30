"""
Authentication and user management models.
Defines user, role, and permission models for the BSF monitoring system.
"""

from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, Table, Integer
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.database.postgresql import Base
import uuid
from enum import Enum as PyEnum


class UserRole(str, PyEnum):
    """User roles in the system."""
    ADMIN = "admin"
    MANAGER = "manager"
    OPERATOR = "operator"
    VIEWER = "viewer"


class Permission(str, PyEnum):
    """System permissions."""
    # Farm management
    FARM_VIEW = "farm:view"
    FARM_EDIT = "farm:edit"
    FARM_DELETE = "farm:delete"
    
    # Device management
    DEVICE_VIEW = "device:view"
    DEVICE_EDIT = "device:edit"
    DEVICE_DELETE = "device:delete"
    DEVICE_CONTROL = "device:control"
    
    # Data access
    DATA_VIEW = "data:view"
    DATA_EXPORT = "data:export"
    DATA_DELETE = "data:delete"
    
    # Alert management
    ALERT_VIEW = "alert:view"
    ALERT_MANAGE = "alert:manage"
    ALERT_CONFIG = "alert:config"
    
    # User management
    USER_VIEW = "user:view"
    USER_EDIT = "user:edit"
    USER_DELETE = "user:delete"
    
    # System administration
    SYSTEM_CONFIG = "system:config"
    SYSTEM_LOGS = "system:logs"
    SYSTEM_BACKUP = "system:backup"
    
    # Analytics and reporting
    VIEW_ANALYTICS = "view_analytics"
    MANAGE_ANALYTICS = "manage_analytics"


# Role-Permission association table
role_permissions = Table(
    'role_permissions',
    Base.metadata,
    Column('role', String(50), primary_key=True),
    Column('permission', String(100), primary_key=True)
)

# User-Farm association table for multi-farm access control
user_farms = Table(
    'user_farms',
    Base.metadata,
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id'), primary_key=True),
    Column('farm_id', String(100), primary_key=True),
    Column('granted_at', DateTime(timezone=True), server_default=func.now()),
    Column('granted_by', UUID(as_uuid=True), ForeignKey('users.id'))
)


class User(Base):
    """User model for authentication and authorization."""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    
    # User status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    
    # Role and permissions
    role = Column(String(50), nullable=False, default=UserRole.VIEWER)
    
    # Profile information
    phone = Column(String(20))
    department = Column(String(100))
    position = Column(String(100))
    location = Column(String(200))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))
    password_changed_at = Column(DateTime(timezone=True))
    
    # Security settings
    force_password_change = Column(Boolean, default=False)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True))
    
    # Additional settings
    preferences = Column(JSON)  # User preferences like dashboard settings
    
    # Relationships
    granted_farm_access = relationship(
        "User",
        secondary=user_farms,
        primaryjoin=id == user_farms.c.granted_by,
        secondaryjoin=id == user_farms.c.user_id,
        back_populates="granted_by_users"
    )
    granted_by_users = relationship(
        "User",
        secondary=user_farms,
        primaryjoin=id == user_farms.c.user_id,
        secondaryjoin=id == user_farms.c.granted_by,
        back_populates="granted_farm_access"
    )

    def __repr__(self):
        return f"<User(username='{self.username}', role='{self.role}')>"


class UserSession(Base):
    """User session tracking for security monitoring."""
    __tablename__ = "user_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    
    # Session information
    ip_address = Column(String(45))  # IPv6 compatible
    user_agent = Column(Text)
    device_info = Column(JSON)
    
    # Session status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_activity = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True))
    revoked_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    revoked_by_user = relationship("User", foreign_keys=[revoked_by])

    def __repr__(self):
        return f"<UserSession(user_id='{self.user_id}', active='{self.is_active}')>"


class LoginAttempt(Base):
    """Login attempt logging for security monitoring."""
    __tablename__ = "login_attempts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))  # Null if user doesn't exist
    
    # Attempt details
    success = Column(Boolean, nullable=False)
    failure_reason = Column(String(100))  # "invalid_password", "user_not_found", "account_locked", etc.
    
    # Request information
    ip_address = Column(String(45), nullable=False)
    user_agent = Column(Text)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Additional context
    request_metadata = Column(JSON)  # Additional context like geolocation, etc.
    
    # Relationships
    user = relationship("User")

    def __repr__(self):
        return f"<LoginAttempt(username='{self.username}', success='{self.success}')>"


class APIKey(Base):
    """API key model for service-to-service authentication."""
    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    
    # Key details
    key_hash = Column(String(255), unique=True, nullable=False, index=True)
    key_prefix = Column(String(10), nullable=False)  # First few characters for identification
    
    # Ownership and permissions
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    permissions = Column(JSON)  # List of allowed permissions
    allowed_ips = Column(JSON)  # List of allowed IP addresses
    
    # Status and lifecycle
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))
    last_used = Column(DateTime(timezone=True))
    usage_count = Column(Integer, default=0)
    
    # Rate limiting
    rate_limit_per_hour = Column(Integer)
    
    # Relationships
    creator = relationship("User")

    def __repr__(self):
        return f"<APIKey(name='{self.name}', active='{self.is_active}')>"


# Default role permissions mapping
DEFAULT_ROLE_PERMISSIONS = {
    UserRole.ADMIN: [
        # Full access to everything
        Permission.FARM_VIEW, Permission.FARM_EDIT, Permission.FARM_DELETE,
        Permission.DEVICE_VIEW, Permission.DEVICE_EDIT, Permission.DEVICE_DELETE, Permission.DEVICE_CONTROL,
        Permission.DATA_VIEW, Permission.DATA_EXPORT, Permission.DATA_DELETE,
        Permission.ALERT_VIEW, Permission.ALERT_MANAGE, Permission.ALERT_CONFIG,
        Permission.USER_VIEW, Permission.USER_EDIT, Permission.USER_DELETE,
        Permission.SYSTEM_CONFIG, Permission.SYSTEM_LOGS, Permission.SYSTEM_BACKUP,
        Permission.VIEW_ANALYTICS, Permission.MANAGE_ANALYTICS
    ],
    UserRole.MANAGER: [
        # Farm and device management, data access, alert management
        Permission.FARM_VIEW, Permission.FARM_EDIT,
        Permission.DEVICE_VIEW, Permission.DEVICE_EDIT, Permission.DEVICE_CONTROL,
        Permission.DATA_VIEW, Permission.DATA_EXPORT,
        Permission.ALERT_VIEW, Permission.ALERT_MANAGE, Permission.ALERT_CONFIG,
        Permission.USER_VIEW,
        Permission.VIEW_ANALYTICS, Permission.MANAGE_ANALYTICS
    ],
    UserRole.OPERATOR: [
        # Device operation, data viewing, basic alert management
        Permission.FARM_VIEW,
        Permission.DEVICE_VIEW, Permission.DEVICE_CONTROL,
        Permission.DATA_VIEW,
        Permission.ALERT_VIEW, Permission.ALERT_MANAGE,
        Permission.VIEW_ANALYTICS
    ],
    UserRole.VIEWER: [
        # Read-only access
        Permission.FARM_VIEW,
        Permission.DEVICE_VIEW,
        Permission.DATA_VIEW,
        Permission.ALERT_VIEW,
        Permission.VIEW_ANALYTICS
    ]
}