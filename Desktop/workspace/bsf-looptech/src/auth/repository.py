"""
Authentication repository for user and session management.
Handles database operations for authentication and authorization.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, func
from sqlalchemy.orm import selectinload
from src.auth.models import (
    User, UserSession, LoginAttempt, APIKey, 
    UserRole, Permission, DEFAULT_ROLE_PERMISSIONS
)
from src.auth.security import (
    get_password_hash, verify_password, SecurityConfig,
    create_access_token, create_refresh_token, verify_api_key
)
from src.utils.logging import get_logger

logger = get_logger(__name__)


class UserRepository:
    """Repository for user management operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_user(
        self,
        username: str,
        email: str,
        password: str,
        full_name: str,
        role: UserRole = UserRole.VIEWER,
        **kwargs
    ) -> User:
        """Create a new user."""
        hashed_password = get_password_hash(password)
        
        user = User(
            username=username,
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            role=role,
            password_changed_at=datetime.utcnow(),
            **kwargs
        )
        
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        
        logger.info(f"User created: {username} with role {role}")
        return user
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        result = await self.session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user with username/password."""
        user = await self.get_user_by_username(username)
        
        if not user:
            return None
        
        if not verify_password(password, user.hashed_password):
            return None
        
        if not user.is_active:
            return None
        
        # Update last login
        user.last_login = datetime.utcnow()
        user.failed_login_attempts = 0  # Reset failed attempts
        await self.session.commit()
        
        return user
    
    async def update_user(self, user_id: str, **kwargs) -> Optional[User]:
        """Update user information."""
        result = await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(updated_at=datetime.utcnow(), **kwargs)
            .returning(User)
        )
        
        user = result.scalar_one_or_none()
        if user:
            await self.session.commit()
            await self.session.refresh(user)
        
        return user
    
    async def change_password(self, user_id: str, new_password: str) -> bool:
        """Change user password."""
        hashed_password = get_password_hash(new_password)
        
        result = await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                hashed_password=hashed_password,
                password_changed_at=datetime.utcnow(),
                force_password_change=False,
                updated_at=datetime.utcnow()
            )
        )
        
        if result.rowcount > 0:
            await self.session.commit()
            logger.info(f"Password changed for user {user_id}")
            return True
        
        return False
    
    async def lock_user_account(self, user_id: str, duration_minutes: int = None) -> bool:
        """Lock user account temporarily or permanently."""
        if duration_minutes:
            locked_until = datetime.utcnow() + timedelta(minutes=duration_minutes)
        else:
            locked_until = None  # Permanent lock
        
        result = await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                is_active=False if not duration_minutes else True,
                locked_until=locked_until,
                updated_at=datetime.utcnow()
            )
        )
        
        if result.rowcount > 0:
            await self.session.commit()
            logger.warning(f"User account locked: {user_id}")
            return True
        
        return False
    
    async def unlock_user_account(self, user_id: str) -> bool:
        """Unlock user account."""
        result = await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                is_active=True,
                locked_until=None,
                failed_login_attempts=0,
                updated_at=datetime.utcnow()
            )
        )
        
        if result.rowcount > 0:
            await self.session.commit()
            logger.info(f"User account unlocked: {user_id}")
            return True
        
        return False
    
    async def increment_failed_login(self, username: str) -> int:
        """Increment failed login attempts for user."""
        user = await self.get_user_by_username(username)
        if not user:
            return 0
        
        new_count = (user.failed_login_attempts or 0) + 1
        
        # Auto-lock if too many failed attempts
        if new_count >= SecurityConfig.MAX_LOGIN_ATTEMPTS:
            await self.lock_user_account(
                str(user.id), 
                SecurityConfig.LOCKOUT_DURATION_MINUTES
            )
        else:
            await self.session.execute(
                update(User)
                .where(User.id == user.id)
                .values(
                    failed_login_attempts=new_count,
                    updated_at=datetime.utcnow()
                )
            )
            await self.session.commit()
        
        return new_count
    
    async def get_users(
        self,
        skip: int = 0,
        limit: int = 100,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None
    ) -> List[User]:
        """Get list of users with optional filters."""
        query = select(User)
        
        if role:
            query = query.where(User.role == role)
        
        if is_active is not None:
            query = query.where(User.is_active == is_active)
        
        query = query.offset(skip).limit(limit).order_by(User.created_at.desc())
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def delete_user(self, user_id: str) -> bool:
        """Delete user (soft delete by deactivating)."""
        result = await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                is_active=False,
                username=func.concat(User.username, "_deleted_", func.extract('epoch', func.now())),
                email=func.concat(User.email, "_deleted_", func.extract('epoch', func.now())),
                updated_at=datetime.utcnow()
            )
        )
        
        if result.rowcount > 0:
            await self.session.commit()
            logger.info(f"User deleted (soft): {user_id}")
            return True
        
        return False
    
    @staticmethod
    async def user_has_permission(user: User, permission: Permission) -> bool:
        """Check if user has specific permission based on role."""
        role_permissions = DEFAULT_ROLE_PERMISSIONS.get(user.role, [])
        return permission in role_permissions
    
    async def grant_farm_access(self, user_id: str, farm_id: str, granted_by_id: str) -> bool:
        """Grant user access to specific farm."""
        # Check if access already exists
        from src.auth.models import user_farms
        
        existing = await self.session.execute(
            select(user_farms)
            .where(
                and_(
                    user_farms.c.user_id == user_id,
                    user_farms.c.farm_id == farm_id
                )
            )
        )
        
        if existing.first():
            return True  # Already has access
        
        # Grant access
        await self.session.execute(
            user_farms.insert().values(
                user_id=user_id,
                farm_id=farm_id,
                granted_by=granted_by_id,
                granted_at=datetime.utcnow()
            )
        )
        
        await self.session.commit()
        logger.info(f"Farm access granted: user {user_id} to farm {farm_id}")
        return True
    
    async def revoke_farm_access(self, user_id: str, farm_id: str) -> bool:
        """Revoke user access to specific farm."""
        from src.auth.models import user_farms
        
        result = await self.session.execute(
            delete(user_farms)
            .where(
                and_(
                    user_farms.c.user_id == user_id,
                    user_farms.c.farm_id == farm_id
                )
            )
        )
        
        if result.rowcount > 0:
            await self.session.commit()
            logger.info(f"Farm access revoked: user {user_id} from farm {farm_id}")
            return True
        
        return False
    
    async def get_user_farms(self, user_id: str) -> List[str]:
        """Get list of farm IDs user has access to."""
        from src.auth.models import user_farms
        
        result = await self.session.execute(
            select(user_farms.c.farm_id)
            .where(user_farms.c.user_id == user_id)
        )
        
        return [row[0] for row in result.fetchall()]


class SessionRepository:
    """Repository for session management operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_session(
        self,
        user_id: str,
        session_token: str,
        ip_address: str,
        user_agent: str,
        device_info: Dict[str, Any] = None
    ) -> UserSession:
        """Create new user session."""
        expires_at = datetime.utcnow() + timedelta(minutes=SecurityConfig.SESSION_TIMEOUT_MINUTES)
        
        session_obj = UserSession(
            user_id=user_id,
            session_token=session_token,
            ip_address=ip_address,
            user_agent=user_agent,
            device_info=device_info,
            expires_at=expires_at
        )
        
        self.session.add(session_obj)
        await self.session.commit()
        await self.session.refresh(session_obj)
        
        return session_obj
    
    async def get_session(self, session_token: str) -> Optional[UserSession]:
        """Get session by token."""
        result = await self.session.execute(
            select(UserSession)
            .where(
                and_(
                    UserSession.session_token == session_token,
                    UserSession.is_active == True,
                    UserSession.expires_at > datetime.utcnow()
                )
            )
            .options(selectinload(UserSession.user))
        )
        return result.scalar_one_or_none()
    
    async def update_session_activity(self, session_token: str) -> bool:
        """Update session last activity timestamp."""
        result = await self.session.execute(
            update(UserSession)
            .where(UserSession.session_token == session_token)
            .values(last_activity=datetime.utcnow())
        )
        
        if result.rowcount > 0:
            await self.session.commit()
            return True
        
        return False
    
    async def revoke_session(self, session_token: str, revoked_by: str = None) -> bool:
        """Revoke user session."""
        result = await self.session.execute(
            update(UserSession)
            .where(UserSession.session_token == session_token)
            .values(
                is_active=False,
                revoked_at=datetime.utcnow(),
                revoked_by=revoked_by
            )
        )
        
        if result.rowcount > 0:
            await self.session.commit()
            return True
        
        return False
    
    async def revoke_user_sessions(self, user_id: str, except_session: str = None) -> int:
        """Revoke all sessions for a user, optionally except one."""
        query = update(UserSession).where(
            and_(
                UserSession.user_id == user_id,
                UserSession.is_active == True
            )
        )
        
        if except_session:
            query = query.where(UserSession.session_token != except_session)
        
        query = query.values(
            is_active=False,
            revoked_at=datetime.utcnow()
        )
        
        result = await self.session.execute(query)
        await self.session.commit()
        
        return result.rowcount
    
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions."""
        result = await self.session.execute(
            update(UserSession)
            .where(
                and_(
                    UserSession.is_active == True,
                    UserSession.expires_at < datetime.utcnow()
                )
            )
            .values(
                is_active=False,
                revoked_at=datetime.utcnow()
            )
        )
        
        await self.session.commit()
        return result.rowcount


class LoginAttemptRepository:
    """Repository for login attempt tracking."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def log_login_attempt(
        self,
        username: str,
        success: bool,
        ip_address: str,
        user_agent: str = None,
        user_id: str = None,
        failure_reason: str = None,
        metadata: Dict[str, Any] = None
    ) -> LoginAttempt:
        """Log login attempt."""
        attempt = LoginAttempt(
            username=username,
            user_id=user_id,
            success=success,
            failure_reason=failure_reason,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata
        )
        
        self.session.add(attempt)
        await self.session.commit()
        await self.session.refresh(attempt)
        
        return attempt
    
    async def get_recent_attempts(
        self,
        username: str = None,
        ip_address: str = None,
        hours: int = 24,
        limit: int = 100
    ) -> List[LoginAttempt]:
        """Get recent login attempts."""
        query = select(LoginAttempt)
        
        conditions = [
            LoginAttempt.timestamp > datetime.utcnow() - timedelta(hours=hours)
        ]
        
        if username:
            conditions.append(LoginAttempt.username == username)
        
        if ip_address:
            conditions.append(LoginAttempt.ip_address == ip_address)
        
        query = query.where(and_(*conditions))
        query = query.order_by(LoginAttempt.timestamp.desc()).limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()


class APIKeyRepository:
    """Repository for API key management."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_api_key(
        self,
        name: str,
        key_hash: str,
        key_prefix: str,
        created_by: str,
        permissions: List[str] = None,
        expires_at: datetime = None,
        **kwargs
    ) -> APIKey:
        """Create new API key."""
        api_key = APIKey(
            name=name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            created_by=created_by,
            permissions=permissions or [],
            expires_at=expires_at,
            **kwargs
        )
        
        self.session.add(api_key)
        await self.session.commit()
        await self.session.refresh(api_key)
        
        logger.info(f"API key created: {name} by user {created_by}")
        return api_key
    
    async def get_api_key_by_prefix(self, key_prefix: str) -> Optional[APIKey]:
        """Get API key by prefix."""
        result = await self.session.execute(
            select(APIKey)
            .where(
                and_(
                    APIKey.key_prefix == key_prefix,
                    APIKey.is_active == True,
                    or_(
                        APIKey.expires_at.is_(None),
                        APIKey.expires_at > datetime.utcnow()
                    )
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def verify_api_key(self, api_key: str) -> Optional[APIKey]:
        """Verify API key and return key object if valid."""
        # Extract prefix from key
        if not api_key.startswith("bsf_"):
            return None
        
        parts = api_key.split("_", 2)
        if len(parts) != 3:
            return None
        
        key_prefix = parts[1]
        
        # Get key from database
        api_key_obj = await self.get_api_key_by_prefix(key_prefix)
        if not api_key_obj:
            return None
        
        # Verify key hash
        if not verify_api_key(api_key, api_key_obj.key_hash):
            return None
        
        # Update usage statistics
        await self.session.execute(
            update(APIKey)
            .where(APIKey.id == api_key_obj.id)
            .values(
                last_used=datetime.utcnow(),
                usage_count=APIKey.usage_count + 1
            )
        )
        await self.session.commit()
        
        return api_key_obj
    
    async def revoke_api_key(self, key_id: str) -> bool:
        """Revoke API key."""
        result = await self.session.execute(
            update(APIKey)
            .where(APIKey.id == key_id)
            .values(is_active=False)
        )
        
        if result.rowcount > 0:
            await self.session.commit()
            logger.info(f"API key revoked: {key_id}")
            return True
        
        return False
    
    async def get_user_api_keys(self, user_id: str) -> List[APIKey]:
        """Get all API keys created by user."""
        result = await self.session.execute(
            select(APIKey)
            .where(APIKey.created_by == user_id)
            .order_by(APIKey.created_at.desc())
        )
        return result.scalars().all()