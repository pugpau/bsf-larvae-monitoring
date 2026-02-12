"""
Security utilities for authentication and authorization.
Handles JWT tokens, password hashing, and security validations.
"""

import os
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional, Union, Dict, Any, Set
import jwt
from jwt.exceptions import PyJWTError
from passlib.context import CryptContext
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.postgresql import get_async_session
from src.auth.models import User, UserSession, LoginAttempt, APIKey, Permission
from src.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Security configuration — single source of truth from settings
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# Development mode - skip authentication (set SKIP_AUTH=true)
SKIP_AUTH = os.getenv("SKIP_AUTH", "false").lower() == "true"

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer token security
# auto_error=False allows requests without token when SKIP_AUTH is enabled
security = HTTPBearer(auto_error=False)

# In-memory token blacklist (JTI set).
# NOTE: Not shared across workers; acceptable for single-process closed-network deployment.
# For multi-worker setups, replace with Redis-backed blacklist.
_token_blacklist: Set[str] = set()


def blacklist_token(jti: str) -> None:
    """Add a token's JTI to the blacklist (called on logout)."""
    _token_blacklist.add(jti)


def is_token_blacklisted(jti: str) -> bool:
    """Check if a token's JTI has been blacklisted."""
    return jti in _token_blacklist


class SecurityConfig:
    """Security configuration and constants."""
    
    # Token settings
    SECRET_KEY = SECRET_KEY
    ALGORITHM = ALGORITHM
    ACCESS_TOKEN_EXPIRE_MINUTES = ACCESS_TOKEN_EXPIRE_MINUTES
    REFRESH_TOKEN_EXPIRE_DAYS = REFRESH_TOKEN_EXPIRE_DAYS
    
    # Password policy
    MIN_PASSWORD_LENGTH = 8
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_NUMBERS = True
    REQUIRE_SPECIAL_CHARS = True
    
    # Security limits
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 30
    SESSION_TIMEOUT_MINUTES = 60
    
    # API Key settings
    API_KEY_PREFIX_LENGTH = 8
    API_KEY_LENGTH = 32


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash."""
    return pwd_context.hash(password)


def validate_password_strength(password: str) -> Dict[str, Any]:
    """
    Validate password against security policy.
    Returns validation result and any error messages.
    """
    errors = []
    
    if len(password) < SecurityConfig.MIN_PASSWORD_LENGTH:
        errors.append(f"Password must be at least {SecurityConfig.MIN_PASSWORD_LENGTH} characters long")
    
    if SecurityConfig.REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter")
    
    if SecurityConfig.REQUIRE_LOWERCASE and not any(c.islower() for c in password):
        errors.append("Password must contain at least one lowercase letter")
    
    if SecurityConfig.REQUIRE_NUMBERS and not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one number")
    
    if SecurityConfig.REQUIRE_SPECIAL_CHARS and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        errors.append("Password must contain at least one special character")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors
    }


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token with unique JTI for blacklisting support."""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=SecurityConfig.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "type": "access", "jti": str(uuid.uuid4())})

    encoded_jwt = jwt.encode(to_encode, SecurityConfig.SECRET_KEY, algorithm=SecurityConfig.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT refresh token with unique JTI for blacklisting support."""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=SecurityConfig.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({"exp": expire, "type": "refresh", "jti": str(uuid.uuid4())})

    encoded_jwt = jwt.encode(to_encode, SecurityConfig.SECRET_KEY, algorithm=SecurityConfig.ALGORITHM)
    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
    """
    Verify and decode JWT token.
    Returns payload if valid, None if invalid.
    Checks the in-memory blacklist for revoked tokens.
    """
    try:
        payload = jwt.decode(token, SecurityConfig.SECRET_KEY, algorithms=[SecurityConfig.ALGORITHM])

        # Check token type
        if payload.get("type") != token_type:
            return None

        # Check expiration
        exp = payload.get("exp")
        if exp is None or datetime.utcfromtimestamp(exp) < datetime.utcnow():
            return None

        # Check blacklist
        jti = payload.get("jti")
        if jti and is_token_blacklisted(jti):
            return None

        return payload

    except PyJWTError as e:
        logger.warning(f"JWT verification failed: {e}")
        return None


def generate_api_key() -> tuple[str, str]:
    """
    Generate API key and return (full_key, hashed_key).
    Full key is shown to user once, hashed key is stored in database.
    """
    # Generate random key
    key = secrets.token_urlsafe(SecurityConfig.API_KEY_LENGTH)
    
    # Create prefix for identification
    prefix = key[:SecurityConfig.API_KEY_PREFIX_LENGTH]
    
    # Full key with prefix
    full_key = f"bsf_{prefix}_{key}"
    
    # Hash for storage
    hashed_key = get_password_hash(full_key)
    
    return full_key, hashed_key


def verify_api_key(api_key: str, hashed_key: str) -> bool:
    """Verify API key against its hash."""
    return verify_password(api_key, hashed_key)


def _create_dev_user() -> User:
    """Create a development user for SKIP_AUTH mode."""
    from uuid import uuid4
    dev_user = User(
        id=uuid4(),
        username="dev_user",
        email="dev@localhost",
        hashed_password="",
        full_name="Development User",
        role="admin",
        is_active=True,
        is_verified=True,
        is_superuser=True
    )
    return dev_user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_async_session)
) -> User:
    """
    Get current authenticated user from JWT token.
    Used as FastAPI dependency.
    """
    # Development mode - skip authentication
    if SKIP_AUTH:
        logger.warning("SKIP_AUTH is enabled - authentication bypassed (development mode only!)")
        return _create_dev_user()

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Verify token
        payload = verify_token(credentials.credentials, "access")
        if payload is None:
            raise credentials_exception

        # Get user ID from token
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception

        # Get user from database
        from src.auth.repository import UserRepository
        user_repo = UserRepository(session)
        user = await user_repo.get_user_by_id(user_id)

        if user is None:
            raise credentials_exception

        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Inactive user"
            )

        return user

    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise credentials_exception


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user.
    Additional check for user account status.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


def require_permission(permission: Permission):
    """
    Decorator to require specific permission for endpoint access.
    Returns a dependency function that checks user permissions.
    """
    async def permission_checker(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        """Check if current user has required permission."""
        # Development mode - skip permission check
        if SKIP_AUTH:
            return current_user

        from src.auth.repository import UserRepository

        # Check if user has permission
        if not await UserRepository.user_has_permission(current_user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not enough permissions. Required: {permission.value}"
            )

        return current_user

    return permission_checker


def require_role(required_role: str):
    """
    Decorator to require specific role for endpoint access.
    Returns a dependency function that checks user role.
    """
    async def role_checker(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        """Check if current user has required role."""
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not enough permissions. Required role: {required_role}"
            )
        
        return current_user
    
    return role_checker


async def check_rate_limit(
    user_id: str,
    action: str,
    limit: int,
    window_minutes: int,
    session: AsyncSession
) -> bool:
    """
    Check rate limiting for user actions.
    Returns True if within limit, False if exceeded.
    """
    # This would typically use Redis for performance
    # For now, implement basic check using database
    from sqlalchemy import text
    
    query = text("""
        SELECT COUNT(*)
        FROM login_attempts
        WHERE user_id = :user_id
        AND timestamp > NOW() - INTERVAL '1 minute' * :window_minutes
    """)
    
    result = await session.execute(query, {
        "user_id": user_id,
        "window_minutes": window_minutes
    })
    
    count = result.scalar()
    return count < limit


def mask_sensitive_data(data: str, mask_char: str = "*", visible_chars: int = 4) -> str:
    """
    Mask sensitive data like API keys, showing only first few characters.
    """
    if len(data) <= visible_chars:
        return mask_char * len(data)
    
    return data[:visible_chars] + mask_char * (len(data) - visible_chars)


def sanitize_user_input(input_str: str) -> str:
    """
    Sanitize user input to prevent injection attacks.
    """
    # Basic sanitization - remove null bytes and control characters
    sanitized = input_str.replace('\x00', '').replace('\r', '').replace('\n', ' ')
    
    # Trim whitespace
    sanitized = sanitized.strip()
    
    return sanitized


class SecurityHeaders:
    """Security headers for HTTP responses."""
    
    @staticmethod
    def get_security_headers() -> Dict[str, str]:
        """Get recommended security headers."""
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'",
            "Referrer-Policy": "strict-origin-when-cross-origin"
        }