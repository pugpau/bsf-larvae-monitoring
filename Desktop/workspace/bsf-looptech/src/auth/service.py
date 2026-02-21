"""
Authentication service layer.
Handles business logic for authentication and user management.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from src.auth.repository import (
    UserRepository, SessionRepository, 
    LoginAttemptRepository, APIKeyRepository
)
from src.auth.models import User, UserRole, Permission
from src.auth.security import (
    create_access_token, create_refresh_token, verify_token,
    generate_api_key, SecurityConfig
)
from src.auth.schemas import (
    UserCreate, UserUpdate, LoginRequest, APIKeyCreate,
    PasswordChange, SecurityStatusResponse
)
from src.utils.logging import get_logger

logger = get_logger(__name__)


class AuthenticationService:
    """Service for authentication operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.session_repo = SessionRepository(session)
        self.login_repo = LoginAttemptRepository(session)
        self.api_key_repo = APIKeyRepository(session)
    
    async def authenticate_user(
        self,
        login_request: LoginRequest,
        ip_address: str,
        user_agent: str = None
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Authenticate user with username/password.
        Returns (token_data, error_message).
        """
        username = login_request.username
        password = login_request.password
        
        try:
            # Check if user exists and get user object
            user = await self.user_repo.get_user_by_username(username)
            if not user:
                # Try by email
                user = await self.user_repo.get_user_by_email(username)
            
            # Check account lockout
            locked_until = user.locked_until if user else None
            if locked_until and locked_until.tzinfo is None:
                locked_until = locked_until.replace(tzinfo=timezone.utc)
            if user and locked_until and locked_until > datetime.now(timezone.utc):
                await self.login_repo.log_login_attempt(
                    username=username,
                    success=False,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    user_id=str(user.id) if user else None,
                    failure_reason="account_locked"
                )
                return None, "Account is temporarily locked. Please try again later."
            
            # Authenticate
            authenticated_user = await self.user_repo.authenticate_user(username, password)
            
            if not authenticated_user:
                # Log failed attempt
                await self.login_repo.log_login_attempt(
                    username=username,
                    success=False,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    user_id=str(user.id) if user else None,
                    failure_reason="invalid_credentials"
                )
                
                # Increment failed login attempts
                if user:
                    await self.user_repo.increment_failed_login(username)
                
                return None, "Invalid username or password"
            
            # Check if account is active
            if not authenticated_user.is_active:
                await self.login_repo.log_login_attempt(
                    username=username,
                    success=False,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    user_id=str(authenticated_user.id),
                    failure_reason="account_inactive"
                )
                return None, "Account is inactive"
            
            # Create tokens
            access_token_expires = timedelta(minutes=SecurityConfig.ACCESS_TOKEN_EXPIRE_MINUTES)
            refresh_token_expires = timedelta(days=SecurityConfig.REFRESH_TOKEN_EXPIRE_DAYS)

            if login_request.remember_me:
                # Extend refresh token (not access token) for "remember me"
                refresh_token_expires = timedelta(days=30)
            
            token_data = {
                "sub": str(authenticated_user.id),
                "username": authenticated_user.username,
                "role": authenticated_user.role,
                "permissions": [p.value for p in await self._get_user_permissions(authenticated_user)]
            }
            
            access_token = create_access_token(token_data, access_token_expires)
            refresh_token = create_refresh_token({"sub": str(authenticated_user.id)}, refresh_token_expires)
            
            # Create session
            session_token = str(uuid.uuid4())
            await self.session_repo.create_session(
                user_id=str(authenticated_user.id),
                session_token=session_token,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            # Log successful attempt
            await self.login_repo.log_login_attempt(
                username=username,
                success=True,
                ip_address=ip_address,
                user_agent=user_agent,
                user_id=str(authenticated_user.id)
            )
            
            logger.info(f"User authenticated successfully: {username}")
            
            # Convert user to dict for serialization
            user_dict = {
                "id": str(authenticated_user.id),
                "username": authenticated_user.username,
                "email": authenticated_user.email,
                "full_name": authenticated_user.full_name,
                "role": authenticated_user.role,
                "is_active": authenticated_user.is_active,
                "is_verified": authenticated_user.is_verified,
                "is_superuser": authenticated_user.is_superuser,
                "created_at": authenticated_user.created_at,
                "updated_at": authenticated_user.updated_at,
                "last_login": authenticated_user.last_login,
                "force_password_change": authenticated_user.force_password_change,
                "failed_login_attempts": authenticated_user.failed_login_attempts,
                "locked_until": authenticated_user.locked_until,
                "preferences": authenticated_user.preferences,
                "phone": authenticated_user.phone,
                "department": authenticated_user.department,
                "position": authenticated_user.position,
                "location": authenticated_user.location
            }
            
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": int(access_token_expires.total_seconds()),
                "user": user_dict
            }, None
            
        except Exception as e:
            logger.error(f"Authentication error for user {username}: {e}")
            return None, "Authentication failed"
    
    async def refresh_access_token(self, refresh_token: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Refresh access token using refresh token.
        Returns (token_data, error_message).
        """
        try:
            # Verify refresh token
            payload = verify_token(refresh_token, "refresh")
            if not payload:
                return None, "Invalid refresh token"
            
            user_id = payload.get("sub")
            if not user_id:
                return None, "Invalid refresh token"
            
            # Get user
            user = await self.user_repo.get_user_by_id(user_id)
            if not user or not user.is_active:
                return None, "User not found or inactive"
            
            # Create new access token
            token_data = {
                "sub": str(user.id),
                "username": user.username,
                "role": user.role,
                "permissions": [p.value for p in await self._get_user_permissions(user)]
            }
            
            access_token_expires = timedelta(minutes=SecurityConfig.ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_access_token(token_data, access_token_expires)
            
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": int(access_token_expires.total_seconds())
            }, None
            
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return None, "Token refresh failed"
    
    async def logout_user(self, user_id: str, session_token: str = None) -> bool:
        """Logout user by revoking session(s)."""
        try:
            if session_token:
                # Revoke specific session
                await self.session_repo.revoke_session(session_token, user_id)
            else:
                # Revoke all user sessions
                await self.session_repo.revoke_user_sessions(user_id)
            
            logger.info(f"User logged out: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Logout error for user {user_id}: {e}")
            return False
    
    async def _get_user_permissions(self, user: User) -> List[Permission]:
        """Get user permissions based on role."""
        from src.auth.models import DEFAULT_ROLE_PERMISSIONS
        return DEFAULT_ROLE_PERMISSIONS.get(user.role, [])


class UserManagementService:
    """Service for user management operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
    
    async def create_user(self, user_data: UserCreate, created_by: str = None) -> User:
        """Create a new user."""
        try:
            # Check if username or email already exists
            existing_user = await self.user_repo.get_user_by_username(user_data.username)
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already exists"
                )
            
            existing_email = await self.user_repo.get_user_by_email(user_data.email)
            if existing_email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already exists"
                )
            
            # Create user
            user = await self.user_repo.create_user(
                username=user_data.username,
                email=user_data.email,
                password=user_data.password,
                full_name=user_data.full_name,
                role=user_data.role,
                phone=user_data.phone,
                department=user_data.department,
                position=user_data.position,
                location=user_data.location,
                is_active=user_data.is_active,
                force_password_change=user_data.force_password_change
            )
            
            logger.info(f"User created: {user_data.username} by {created_by}")
            return user
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"User creation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user"
            )
    
    async def update_user(self, user_id: str, user_data: UserUpdate, updated_by: str = None) -> Optional[User]:
        """Update user information."""
        try:
            # Check if email is being changed and already exists
            if user_data.email:
                existing_email = await self.user_repo.get_user_by_email(user_data.email)
                if existing_email and str(existing_email.id) != user_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Email already exists"
                    )
            
            # Update user
            update_data = user_data.dict(exclude_unset=True)
            user = await self.user_repo.update_user(user_id, **update_data)
            
            if user:
                logger.info(f"User updated: {user_id} by {updated_by}")
            
            return user
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"User update error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update user"
            )
    
    async def change_password(
        self,
        user_id: str,
        password_change: PasswordChange,
        current_user: User
    ) -> bool:
        """Change user password."""
        try:
            # Verify current password
            user = await self.user_repo.get_user_by_id(user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Check if user can change this password
            if str(user.id) != user_id and current_user.role != UserRole.ADMIN:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to change this password"
                )
            
            # For self password change, verify current password
            if str(user.id) == user_id:
                from src.auth.security import verify_password
                if not verify_password(password_change.current_password, user.hashed_password):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Current password is incorrect"
                    )
            
            # Change password
            success = await self.user_repo.change_password(user_id, password_change.new_password)
            
            if success:
                logger.info(f"Password changed for user: {user_id}")
                
                # Revoke all user sessions except current one
                from src.auth.repository import SessionRepository
                session_repo = SessionRepository(self.session)
                await session_repo.revoke_user_sessions(user_id)
            
            return success
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Password change error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to change password"
            )
    
    async def get_users(
        self,
        skip: int = 0,
        limit: int = 100,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None
    ) -> List[User]:
        """Get list of users with filters."""
        return await self.user_repo.get_users(skip, limit, role, is_active)
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return await self.user_repo.get_user_by_id(user_id)
    
    async def delete_user(self, user_id: str, deleted_by: str = None) -> bool:
        """Delete user (soft delete)."""
        try:
            success = await self.user_repo.delete_user(user_id)
            
            if success:
                logger.info(f"User deleted: {user_id} by {deleted_by}")
                
                # Revoke all user sessions
                from src.auth.repository import SessionRepository
                session_repo = SessionRepository(self.session)
                await session_repo.revoke_user_sessions(user_id)
            
            return success
            
        except Exception as e:
            logger.error(f"User deletion error: {e}")
            return False
    
    async def lock_user_account(self, user_id: str, duration_minutes: int = None) -> bool:
        """Lock user account."""
        return await self.user_repo.lock_user_account(user_id, duration_minutes)
    
    async def unlock_user_account(self, user_id: str) -> bool:
        """Unlock user account."""
        return await self.user_repo.unlock_user_account(user_id)


class APIKeyService:
    """Service for API key management."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.api_key_repo = APIKeyRepository(session)
    
    async def create_api_key(self, key_data: APIKeyCreate, created_by: str) -> Tuple[str, str]:
        """
        Create new API key.
        Returns (api_key, key_id).
        """
        try:
            # Generate API key
            full_key, hashed_key = generate_api_key()
            key_prefix = full_key.split("_")[1]
            
            # Create in database
            api_key_obj = await self.api_key_repo.create_api_key(
                name=key_data.name,
                key_hash=hashed_key,
                key_prefix=key_prefix,
                created_by=created_by,
                description=key_data.description,
                permissions=[p.value for p in key_data.permissions],
                allowed_ips=key_data.allowed_ips,
                expires_at=key_data.expires_at,
                rate_limit_per_hour=key_data.rate_limit_per_hour
            )
            
            logger.info(f"API key created: {key_data.name} by {created_by}")
            return full_key, str(api_key_obj.id)
            
        except Exception as e:
            logger.error(f"API key creation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create API key"
            )
    
    async def verify_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Verify API key and return key information."""
        try:
            api_key_obj = await self.api_key_repo.verify_api_key(api_key)
            
            if api_key_obj:
                return {
                    "id": str(api_key_obj.id),
                    "name": api_key_obj.name,
                    "permissions": api_key_obj.permissions,
                    "allowed_ips": api_key_obj.allowed_ips,
                    "created_by": str(api_key_obj.created_by)
                }
            
            return None
            
        except Exception as e:
            logger.error(f"API key verification error: {e}")
            return None
    
    async def revoke_api_key(self, key_id: str) -> bool:
        """Revoke API key."""
        return await self.api_key_repo.revoke_api_key(key_id)
    
    async def get_user_api_keys(self, user_id: str) -> List:
        """Get user's API keys."""
        return await self.api_key_repo.get_user_api_keys(user_id)


class SecurityService:
    """Service for security monitoring and management."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.session_repo = SessionRepository(session)
        self.login_repo = LoginAttemptRepository(session)
    
    async def get_security_status(self) -> SecurityStatusResponse:
        """Get overall security status."""
        try:
            # This would normally query various tables for metrics
            # For now, return mock data
            return SecurityStatusResponse(
                active_sessions=0,
                recent_login_attempts=0,
                failed_login_attempts=0,
                locked_accounts=0,
                api_keys_active=0,
                security_events_today=0,
                system_health="healthy"
            )
            
        except Exception as e:
            logger.error(f"Security status error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get security status"
            )
    
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions."""
        return await self.session_repo.cleanup_expired_sessions()
    
    async def get_recent_login_attempts(
        self,
        username: str = None,
        hours: int = 24,
        limit: int = 100
    ) -> List:
        """Get recent login attempts."""
        return await self.login_repo.get_recent_attempts(username, None, hours, limit)