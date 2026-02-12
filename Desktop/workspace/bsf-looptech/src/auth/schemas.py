"""
Pydantic schemas for authentication and user management.
Defines request/response models for API endpoints.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, validator
from src.auth.models import UserRole, Permission


class UserBase(BaseModel):
    """Base user schema with common fields."""
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    email: EmailStr = Field(..., description="Email address")
    full_name: str = Field(..., min_length=1, max_length=100, description="Full name")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")
    department: Optional[str] = Field(None, max_length=100, description="Department")
    position: Optional[str] = Field(None, max_length=100, description="Job position")
    location: Optional[str] = Field(None, max_length=200, description="Location")


class UserCreate(UserBase):
    """Schema for creating a new user."""
    password: str = Field(..., min_length=8, max_length=100, description="Password")
    role: UserRole = Field(UserRole.VIEWER, description="User role")
    is_active: bool = Field(True, description="Account active status")
    force_password_change: bool = Field(False, description="Force password change on next login")
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one number')
        
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v):
            raise ValueError('Password must contain at least one special character')
        
        return v


class UserUpdate(BaseModel):
    """Schema for updating user information."""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    department: Optional[str] = Field(None, max_length=100)
    position: Optional[str] = Field(None, max_length=100)
    location: Optional[str] = Field(None, max_length=200)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    preferences: Optional[Dict[str, Any]] = None


class UserProfileResponse(UserBase):
    """Schema for user profile response (self-service endpoints)."""
    id: UUID
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: Optional[datetime]
    last_login: Optional[datetime]
    force_password_change: bool
    preferences: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True
        json_encoders = {
            UUID: str
        }


class UserResponse(UserProfileResponse):
    """Schema for user response (admin endpoints — includes security fields)."""
    is_superuser: bool
    failed_login_attempts: int
    locked_until: Optional[datetime]


class UserListResponse(BaseModel):
    """Schema for paginated user list response."""
    users: List[UserResponse]
    total: int
    page: int
    size: int
    pages: int


class PasswordChange(BaseModel):
    """Schema for password change request."""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, max_length=100, description="New password")
    
    @validator('new_password')
    def validate_new_password(cls, v):
        """Validate new password strength (same rules as UserCreate)."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one number')
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v):
            raise ValueError('Password must contain at least one special character')
        return v


class PasswordReset(BaseModel):
    """Schema for password reset request."""
    email: EmailStr = Field(..., description="Email address")


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation."""
    token: str = Field(..., description="Reset token")
    new_password: str = Field(..., min_length=8, max_length=100, description="New password")

    @validator('new_password')
    def validate_new_password(cls, v):
        """Validate new password strength (same rules as UserCreate)."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one number')
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v):
            raise ValueError('Password must contain at least one special character')
        return v


class LoginRequest(BaseModel):
    """Schema for login request."""
    username: str = Field(..., description="Username or email")
    password: str = Field(..., description="Password")
    remember_me: bool = Field(False, description="Remember login")


class LoginResponse(BaseModel):
    """Schema for login response."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")
    user: UserProfileResponse = Field(..., description="User information")


class RefreshTokenRequest(BaseModel):
    """Schema for token refresh request."""
    refresh_token: str = Field(..., description="Refresh token")


class RefreshTokenResponse(BaseModel):
    """Schema for token refresh response."""
    access_token: str = Field(..., description="New access token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")


class APIKeyCreate(BaseModel):
    """Schema for creating API key."""
    name: str = Field(..., min_length=1, max_length=100, description="API key name")
    description: Optional[str] = Field(None, max_length=500, description="API key description")
    permissions: List[Permission] = Field([], description="Allowed permissions")
    allowed_ips: List[str] = Field([], description="Allowed IP addresses")
    expires_at: Optional[datetime] = Field(None, description="Expiration date")
    rate_limit_per_hour: Optional[int] = Field(None, ge=1, le=10000, description="Rate limit per hour")


class APIKeyResponse(BaseModel):
    """Schema for API key response."""
    id: UUID
    name: str
    description: Optional[str]
    key_prefix: str
    permissions: List[str]
    allowed_ips: List[str]
    is_active: bool
    created_at: datetime
    expires_at: Optional[datetime]
    last_used: Optional[datetime]
    usage_count: int
    rate_limit_per_hour: Optional[int]
    
    class Config:
        from_attributes = True
        json_encoders = {
            UUID: str
        }


class APIKeyCreateResponse(APIKeyResponse):
    """Schema for API key creation response (includes full key)."""
    api_key: str = Field(..., description="Full API key (shown only once)")


class SessionResponse(BaseModel):
    """Schema for user session response."""
    id: UUID
    ip_address: Optional[str]
    user_agent: Optional[str]
    device_info: Optional[Dict[str, Any]]
    is_active: bool
    created_at: datetime
    last_activity: datetime
    expires_at: datetime
    
    class Config:
        from_attributes = True
        json_encoders = {
            UUID: str
        }


class LoginAttemptResponse(BaseModel):
    """Schema for login attempt response."""
    id: UUID
    username: str
    success: bool
    failure_reason: Optional[str]
    ip_address: str
    user_agent: Optional[str]
    timestamp: datetime
    metadata: Optional[Dict[str, Any]]
    
    class Config:
        from_attributes = True
        json_encoders = {
            UUID: str
        }


class SecurityEventResponse(BaseModel):
    """Schema for security event response."""
    event_type: str
    description: str
    user_id: Optional[str]
    username: Optional[str]
    ip_address: Optional[str]
    timestamp: datetime
    severity: str
    metadata: Optional[Dict[str, Any]]


class FarmAccessRequest(BaseModel):
    """Schema for granting farm access."""
    user_id: str = Field(..., description="User ID")
    farm_id: str = Field(..., description="Farm ID")


class FarmAccessResponse(BaseModel):
    """Schema for farm access response."""
    user_id: str
    farm_id: str
    granted_at: datetime
    granted_by: str
    
    class Config:
        from_attributes = True
        json_encoders = {
            UUID: str
        }


class PermissionCheck(BaseModel):
    """Schema for permission check request."""
    permission: Permission = Field(..., description="Permission to check")
    resource_id: Optional[str] = Field(None, description="Resource ID (e.g., farm_id)")


class PermissionResponse(BaseModel):
    """Schema for permission check response."""
    permission: str
    allowed: bool
    reason: Optional[str] = None


class SecuritySettings(BaseModel):
    """Schema for security settings."""
    password_policy: Dict[str, Any]
    session_timeout_minutes: int
    max_login_attempts: int
    lockout_duration_minutes: int
    require_2fa: bool
    allowed_login_hours: Optional[Dict[str, Any]]


class AuditLogEntry(BaseModel):
    """Schema for audit log entry."""
    id: str
    user_id: Optional[str]
    username: Optional[str]
    action: str
    resource_type: str
    resource_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    timestamp: datetime
    details: Optional[Dict[str, Any]]
    
    class Config:
        from_attributes = True
        json_encoders = {
            UUID: str
        }


class AuditLogResponse(BaseModel):
    """Schema for audit log response."""
    entries: List[AuditLogEntry]
    total: int
    page: int
    size: int
    pages: int


class SecurityStatusResponse(BaseModel):
    """Schema for security status response."""
    active_sessions: int
    recent_login_attempts: int
    failed_login_attempts: int
    locked_accounts: int
    api_keys_active: int
    security_events_today: int
    last_password_policy_update: Optional[datetime] = None
    system_health: str


class TokenValidationResponse(BaseModel):
    """Schema for token validation response."""
    valid: bool
    user_id: Optional[str] = None
    username: Optional[str] = None
    role: Optional[str] = None
    permissions: List[str] = []
    expires_at: Optional[datetime] = None
    error: Optional[str] = None