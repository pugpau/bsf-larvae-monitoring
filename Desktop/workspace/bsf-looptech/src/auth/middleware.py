"""
Authentication middleware for FastAPI.
Handles request authentication and authorization.
"""

import time
from typing import Optional, Callable, Dict, Any
from fastapi import Request, Response, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.postgresql import get_async_session
from src.auth.security import verify_token, SecurityHeaders, SKIP_AUTH
from src.auth.repository import UserRepository, SessionRepository, APIKeyRepository
from src.auth.models import User, Permission
from src.utils.logging import get_logger
from src.utils.request import get_client_ip

logger = get_logger(__name__)

if SKIP_AUTH:
    logger.warning("SKIP_AUTH is enabled — authentication middleware will pass all requests")

# HTTP Bearer for API key authentication
api_key_bearer = HTTPBearer(auto_error=False)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle authentication for all requests.
    Supports JWT tokens and API keys.
    """
    
    def __init__(self, app, exempt_paths: list = None):
        super().__init__(app)
        self.exempt_paths = exempt_paths or [
            "/docs",
            "/redoc", 
            "/openapi.json",
            "/health",
            "/auth/login",
            "/auth/register",
            "/auth/refresh",
            "/",
            "/favicon.ico"
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request through authentication middleware."""
        start_time = time.time()

        try:
            # Always pass CORS preflight requests through to CORSMiddleware
            if request.method == "OPTIONS":
                response = await call_next(request)
                return response

            # Skip authentication for exempt paths
            if self._is_exempt_path(request.url.path):
                response = await call_next(request)
                return self._add_security_headers(response)

            # Development mode — bypass authentication entirely
            if SKIP_AUTH:
                response = await call_next(request)
                return self._add_security_headers(response)
            
            # Get database session
            session = None
            try:
                session_gen = get_async_session()
                session = await session_gen.__anext__()
                
                # Perform authentication
                auth_result = await self._authenticate_request(request, session)
                
                if not auth_result["success"]:
                    return JSONResponse(
                        status_code=auth_result["status_code"],
                        content={"detail": auth_result["message"]}
                    )
                
                # Add authentication info to request state
                request.state.user = auth_result.get("user")
                request.state.api_key = auth_result.get("api_key")
                request.state.permissions = auth_result.get("permissions", [])
                
                # Process request
                response = await call_next(request)
                
                # Log successful request
                processing_time = time.time() - start_time
                await self._log_request(request, response.status_code, processing_time, session)
                
                return self._add_security_headers(response)
                
            finally:
                if session:
                    await session.close()
                    
        except Exception as e:
            logger.error(f"Authentication middleware error: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Internal server error"}
            )
    
    def _is_exempt_path(self, path: str) -> bool:
        """Check if path is exempt from authentication."""
        return any(path.startswith(exempt_path) for exempt_path in self.exempt_paths)
    
    async def _authenticate_request(self, request: Request, session: AsyncSession) -> Dict[str, Any]:
        """
        Authenticate request using JWT token or API key.
        Returns authentication result.
        """
        # Try JWT authentication first
        auth_header = request.headers.get("Authorization")
        
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            
            # Check if it's a JWT token or API key
            if token.startswith("bsf_"):
                # API Key authentication
                return await self._authenticate_api_key(token, request, session)
            else:
                # JWT token authentication
                return await self._authenticate_jwt_token(token, request, session)
        
        # No authentication provided
        return {
            "success": False,
            "status_code": status.HTTP_401_UNAUTHORIZED,
            "message": "Authentication required"
        }
    
    async def _authenticate_jwt_token(
        self, 
        token: str, 
        request: Request, 
        session: AsyncSession
    ) -> Dict[str, Any]:
        """Authenticate using JWT token."""
        try:
            # Verify token
            payload = verify_token(token, "access")
            if not payload:
                return {
                    "success": False,
                    "status_code": status.HTTP_401_UNAUTHORIZED,
                    "message": "Invalid or expired token"
                }
            
            user_id = payload.get("sub")
            if not user_id:
                return {
                    "success": False,
                    "status_code": status.HTTP_401_UNAUTHORIZED,
                    "message": "Invalid token"
                }
            
            # Get user from database
            user_repo = UserRepository(session)
            user = await user_repo.get_user_by_id(user_id)
            
            if not user:
                return {
                    "success": False,
                    "status_code": status.HTTP_401_UNAUTHORIZED,
                    "message": "User not found"
                }
            
            if not user.is_active:
                return {
                    "success": False,
                    "status_code": status.HTTP_401_UNAUTHORIZED,
                    "message": "Account is inactive"
                }
            
            # Check account lockout
            if user.locked_until and user.locked_until > time.time():
                return {
                    "success": False,
                    "status_code": status.HTTP_401_UNAUTHORIZED,
                    "message": "Account is temporarily locked"
                }
            
            return {
                "success": True,
                "user": user,
                "permissions": payload.get("permissions", []),
                "auth_type": "jwt"
            }
            
        except Exception as e:
            logger.error(f"JWT authentication error: {e}")
            return {
                "success": False,
                "status_code": status.HTTP_401_UNAUTHORIZED,
                "message": "Authentication failed"
            }
    
    async def _authenticate_api_key(
        self, 
        api_key: str, 
        request: Request, 
        session: AsyncSession
    ) -> Dict[str, Any]:
        """Authenticate using API key."""
        try:
            api_key_repo = APIKeyRepository(session)
            api_key_obj = await api_key_repo.verify_api_key(api_key)
            
            if not api_key_obj:
                return {
                    "success": False,
                    "status_code": status.HTTP_401_UNAUTHORIZED,
                    "message": "Invalid API key"
                }
            
            # Check IP restrictions
            client_ip = get_client_ip(request)
            if api_key_obj.allowed_ips and client_ip not in api_key_obj.allowed_ips:
                logger.warning(f"API key access denied from IP {client_ip}")
                return {
                    "success": False,
                    "status_code": status.HTTP_403_FORBIDDEN,
                    "message": "Access denied from this IP address"
                }
            
            # Check rate limiting (basic implementation)
            if api_key_obj.rate_limit_per_hour:
                # This would normally use Redis for proper rate limiting
                # For now, just log the usage
                logger.info(f"API key used: {api_key_obj.name} (usage: {api_key_obj.usage_count})")
            
            return {
                "success": True,
                "api_key": api_key_obj,
                "permissions": api_key_obj.permissions,
                "auth_type": "api_key"
            }
            
        except Exception as e:
            logger.error(f"API key authentication error: {e}")
            return {
                "success": False,
                "status_code": status.HTTP_401_UNAUTHORIZED,
                "message": "Authentication failed"
            }
    
    async def _log_request(
        self, 
        request: Request, 
        status_code: int, 
        processing_time: float,
        session: AsyncSession
    ):
        """Log request for audit and monitoring."""
        try:
            user_id = getattr(request.state, "user", None)
            api_key = getattr(request.state, "api_key", None)
            
            log_data = {
                "method": request.method,
                "url": str(request.url),
                "status_code": status_code,
                "processing_time": processing_time,
                "user_id": str(user_id.id) if user_id else None,
                "api_key_id": str(api_key.id) if api_key else None,
                "ip_address": get_client_ip(request),
                "user_agent": request.headers.get("User-Agent")
            }
            
            # This would normally go to a proper audit log table
            logger.info(f"Request logged: {log_data}")
            
        except Exception as e:
            logger.error(f"Request logging error: {e}")
    
    def _add_security_headers(self, response: Response) -> Response:
        """Add security headers to response."""
        security_headers = SecurityHeaders.get_security_headers()
        
        for header, value in security_headers.items():
            response.headers[header] = value
        
        return response


class PermissionMiddleware:
    """
    Middleware to check permissions for specific endpoints.
    Used as a dependency in route handlers.
    """
    
    def __init__(self, required_permission: Permission):
        self.required_permission = required_permission
    
    async def __call__(self, request: Request) -> bool:
        """Check if user has required permission."""
        # Get authentication info from request state
        user = getattr(request.state, "user", None)
        api_key = getattr(request.state, "api_key", None)
        permissions = getattr(request.state, "permissions", [])
        
        # Check permission
        if self.required_permission.value in permissions:
            return True
        
        # For users, check role-based permissions
        if user:
            from src.auth.repository import UserRepository
            if await UserRepository.user_has_permission(user, self.required_permission):
                return True
        
        # Permission denied
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions. Required: {self.required_permission.value}"
        )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Basic in-memory rate limiting middleware.

    KNOWN LIMITATIONS (closed-network deployment accepted):
    - In-memory dict: state is lost on restart and not shared across workers.
    - Single-process only: Blue-Green slots each maintain independent counters.
    - No persistence: a restart resets all rate limit windows.
    For distributed or multi-worker deployments, replace with Redis-backed
    rate limiting (e.g. fastapi-limiter + Redis).
    """

    _CLEANUP_INTERVAL = 100  # Run cleanup every N requests

    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_counts: dict[str, dict[int, int]] = {}
        self._request_counter = 0
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply rate limiting to requests."""
        client_ip = get_client_ip(request)
        current_time = int(time.time() / 60)  # Current minute

        # Periodic cleanup of stale IP entries to prevent memory growth
        self._request_counter += 1
        if self._request_counter >= self._CLEANUP_INTERVAL:
            self._request_counter = 0
            stale_ips = [
                ip for ip, minutes in self.request_counts.items()
                if all(m < current_time - 1 for m in minutes)
            ]
            for ip in stale_ips:
                del self.request_counts[ip]

        # Initialize or clean up old entries
        if client_ip not in self.request_counts:
            self.request_counts[client_ip] = {}

        # Remove old minute entries
        self.request_counts[client_ip] = {
            minute: count for minute, count in self.request_counts[client_ip].items()
            if minute >= current_time - 1
        }
        
        # Count requests in current minute
        current_requests = self.request_counts[client_ip].get(current_time, 0)
        
        if current_requests >= self.requests_per_minute:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded",
                    "retry_after": 60
                },
                headers={"Retry-After": "60"}
            )
        
        # Increment request count
        self.request_counts[client_ip][current_time] = current_requests + 1
        
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(
            self.requests_per_minute - self.request_counts[client_ip][current_time]
        )
        response.headers["X-RateLimit-Reset"] = str((current_time + 1) * 60)
        
        return response