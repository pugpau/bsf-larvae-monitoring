"""
Authentication API routes.
Handles user authentication, registration, and account management.
"""

from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.postgresql import get_async_session
from src.auth.service import AuthenticationService, UserManagementService, APIKeyService, SecurityService
from src.auth.security import get_current_user, get_current_active_user, require_permission, require_role
from src.auth.models import User, UserRole, Permission
from src.auth.schemas import (
    UserCreate, UserUpdate, UserResponse, UserListResponse,
    LoginRequest, LoginResponse, RefreshTokenRequest, RefreshTokenResponse,
    PasswordChange, APIKeyCreate, APIKeyResponse, APIKeyCreateResponse,
    SessionResponse, SecurityStatusResponse, FarmAccessRequest, FarmAccessResponse
)
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()


# Authentication endpoints

@router.post("/login", response_model=LoginResponse)
async def login(
    login_request: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Authenticate user and return JWT tokens.
    """
    auth_service = AuthenticationService(session)
    
    # Get client information
    ip_address = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("User-Agent")
    
    token_data, error = await auth_service.authenticate_user(
        login_request, ip_address, user_agent
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error
        )
    
    return LoginResponse(**token_data)


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_token(
    refresh_request: RefreshTokenRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Refresh access token using refresh token.
    """
    auth_service = AuthenticationService(session)
    
    token_data, error = await auth_service.refresh_access_token(refresh_request.refresh_token)
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error
        )
    
    return RefreshTokenResponse(**token_data)


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Logout user by revoking sessions.
    """
    auth_service = AuthenticationService(session)
    
    success = await auth_service.logout_user(str(current_user.id))
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to logout"
        )
    
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current user information.
    """
    return UserResponse.from_orm(current_user)


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Update current user information.
    """
    user_service = UserManagementService(session)
    
    # Remove role update for self-update (only admins can change roles)
    update_data = user_update.dict(exclude_unset=True)
    if "role" in update_data:
        del update_data["role"]
    
    updated_user = await user_service.update_user(
        str(current_user.id), 
        UserUpdate(**update_data),
        str(current_user.id)
    )
    
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse.from_orm(updated_user)


@router.post("/change-password")
async def change_password(
    password_change: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Change current user password.
    """
    user_service = UserManagementService(session)
    
    success = await user_service.change_password(
        str(current_user.id), password_change, current_user
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to change password"
        )
    
    return {"message": "Password changed successfully"}


# User management endpoints (Admin only)

@router.post("/users", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(require_permission(Permission.USER_EDIT)),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Create a new user. Requires USER_EDIT permission.
    """
    user_service = UserManagementService(session)
    
    user = await user_service.create_user(user_data, str(current_user.id))
    
    return UserResponse.from_orm(user)


@router.get("/users", response_model=List[UserResponse])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    role: Optional[UserRole] = None,
    is_active: Optional[bool] = None,
    current_user: User = Depends(require_permission(Permission.USER_VIEW)),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get list of users. Requires USER_VIEW permission.
    """
    user_service = UserManagementService(session)
    
    users = await user_service.get_users(skip, limit, role, is_active)
    
    return [UserResponse.from_orm(user) for user in users]


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: User = Depends(require_permission(Permission.USER_VIEW)),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get user by ID. Requires USER_VIEW permission.
    """
    user_service = UserManagementService(session)
    
    user = await user_service.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse.from_orm(user)


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    current_user: User = Depends(require_permission(Permission.USER_EDIT)),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Update user. Requires USER_EDIT permission.
    """
    user_service = UserManagementService(session)
    
    updated_user = await user_service.update_user(
        user_id, user_update, str(current_user.id)
    )
    
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse.from_orm(updated_user)


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: User = Depends(require_permission(Permission.USER_DELETE)),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Delete user (soft delete). Requires USER_DELETE permission.
    """
    if user_id == str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    user_service = UserManagementService(session)
    
    success = await user_service.delete_user(user_id, str(current_user.id))
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {"message": "User deleted successfully"}


@router.post("/users/{user_id}/lock")
async def lock_user_account(
    user_id: str,
    duration_minutes: Optional[int] = None,
    current_user: User = Depends(require_permission(Permission.USER_EDIT)),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Lock user account. Requires USER_EDIT permission.
    """
    if user_id == str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot lock your own account"
        )
    
    user_service = UserManagementService(session)
    
    success = await user_service.lock_user_account(user_id, duration_minutes)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    lock_type = "temporarily" if duration_minutes else "permanently"
    return {"message": f"User account locked {lock_type}"}


@router.post("/users/{user_id}/unlock")
async def unlock_user_account(
    user_id: str,
    current_user: User = Depends(require_permission(Permission.USER_EDIT)),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Unlock user account. Requires USER_EDIT permission.
    """
    user_service = UserManagementService(session)
    
    success = await user_service.unlock_user_account(user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {"message": "User account unlocked successfully"}


# API Key management

@router.post("/api-keys", response_model=APIKeyCreateResponse)
async def create_api_key(
    api_key_data: APIKeyCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Create new API key for current user.
    """
    api_key_service = APIKeyService(session)
    
    full_key, key_id = await api_key_service.create_api_key(
        api_key_data, str(current_user.id)
    )
    
    # Get the created key object
    api_key_obj = await api_key_service.api_key_repo.get_api_key_by_prefix(
        full_key.split("_")[1]
    )
    
    response = APIKeyCreateResponse.from_orm(api_key_obj)
    response.api_key = full_key
    
    return response


@router.get("/api-keys", response_model=List[APIKeyResponse])
async def get_api_keys(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get current user's API keys.
    """
    api_key_service = APIKeyService(session)
    
    api_keys = await api_key_service.get_user_api_keys(str(current_user.id))
    
    return [APIKeyResponse.from_orm(key) for key in api_keys]


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Revoke API key.
    """
    api_key_service = APIKeyService(session)
    
    success = await api_key_service.revoke_api_key(key_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    return {"message": "API key revoked successfully"}


# Farm access management

@router.post("/farm-access", response_model=FarmAccessResponse)
async def grant_farm_access(
    access_request: FarmAccessRequest,
    current_user: User = Depends(require_permission(Permission.FARM_EDIT)),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Grant user access to farm. Requires FARM_EDIT permission.
    """
    from src.auth.repository import UserRepository
    
    user_repo = UserRepository(session)
    
    success = await user_repo.grant_farm_access(
        access_request.user_id,
        access_request.farm_id,
        str(current_user.id)
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to grant farm access"
        )
    
    return FarmAccessResponse(
        user_id=access_request.user_id,
        farm_id=access_request.farm_id,
        granted_at=datetime.utcnow(),
        granted_by=str(current_user.id)
    )


@router.delete("/farm-access")
async def revoke_farm_access(
    user_id: str,
    farm_id: str,
    current_user: User = Depends(require_permission(Permission.FARM_EDIT)),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Revoke user access to farm. Requires FARM_EDIT permission.
    """
    from src.auth.repository import UserRepository
    
    user_repo = UserRepository(session)
    
    success = await user_repo.revoke_farm_access(user_id, farm_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Farm access not found"
        )
    
    return {"message": "Farm access revoked successfully"}


@router.get("/users/{user_id}/farms")
async def get_user_farms(
    user_id: str,
    current_user: User = Depends(require_permission(Permission.USER_VIEW)),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get farms user has access to. Requires USER_VIEW permission.
    """
    from src.auth.repository import UserRepository
    
    user_repo = UserRepository(session)
    
    farms = await user_repo.get_user_farms(user_id)
    
    return {"user_id": user_id, "farms": farms}


# Security and monitoring endpoints

@router.get("/security/status", response_model=SecurityStatusResponse)
async def get_security_status(
    current_user: User = Depends(require_permission(Permission.SYSTEM_LOGS)),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get system security status. Requires SYSTEM_LOGS permission.
    """
    security_service = SecurityService(session)
    
    return await security_service.get_security_status()


@router.post("/security/cleanup-sessions")
async def cleanup_expired_sessions(
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Clean up expired sessions. Admin only.
    """
    security_service = SecurityService(session)
    
    cleaned_count = await security_service.cleanup_expired_sessions()
    
    return {"message": f"Cleaned up {cleaned_count} expired sessions"}


@router.get("/security/login-attempts")
async def get_recent_login_attempts(
    username: Optional[str] = None,
    hours: int = 24,
    limit: int = 100,
    current_user: User = Depends(require_permission(Permission.SYSTEM_LOGS)),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get recent login attempts. Requires SYSTEM_LOGS permission.
    """
    security_service = SecurityService(session)
    
    attempts = await security_service.get_recent_login_attempts(username, hours, limit)
    
    return {"attempts": attempts}


# Health check for authentication system

@router.get("/health")
async def auth_health():
    """
    Authentication system health check.
    """
    return {
        "status": "healthy",
        "service": "authentication",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }