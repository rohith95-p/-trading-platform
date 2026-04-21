"""
FastAPI middleware for session validation.
"""

import logging
from typing import Optional
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware

from src.auth.jwt_handler import JWTHandler
from src.session.session_service import SessionService

logger = logging.getLogger(__name__)

# Security scheme for Swagger UI
security = HTTPBearer()


class SessionMiddleware(BaseHTTPMiddleware):
    """Middleware to validate sessions on each request."""
    
    def __init__(self, app, db_connection):
        """
        Initialize session middleware.
        
        Args:
            app: FastAPI application
            db_connection: Database connection
        """
        super().__init__(app)
        self.session_service = SessionService(db_connection)
        self.jwt_handler = JWTHandler()
        
        # Paths that don't require session validation
        self.excluded_paths = [
            "/api/v1/auth/register",
            "/api/v1/auth/login",
            "/api/v1/auth/password-reset",
            "/api/v1/auth/verify-email",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
        ]
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request and validate session.
        
        Args:
            request: FastAPI request
            call_next: Next middleware/route handler
            
        Returns:
            Response from next handler
        """
        # Skip session validation for excluded paths
        if any(request.url.path.startswith(path) for path in self.excluded_paths):
            return await call_next(request)
        
        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            # No token provided, let the route handler decide if auth is required
            return await call_next(request)
        
        token = auth_header.replace("Bearer ", "")
        
        try:
            # Validate JWT token first
            payload = self.jwt_handler.verify_token(token, token_type="access")
            
            # Validate session
            validation_result = await self.session_service.validate_session(
                token=token,
                update_activity=True
            )
            
            if not validation_result.is_valid:
                logger.warning(f"Invalid session: {validation_result.reason}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Session invalid: {validation_result.reason}",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Add session info to request state
            request.state.user_id = validation_result.user_id
            request.state.session_id = validation_result.session_id
            request.state.token_payload = payload
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Session validation error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session validation failed",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return await call_next(request)


async def get_current_session(request: Request) -> dict:
    """
    Get current session information from request state.
    
    Args:
        request: FastAPI request
        
    Returns:
        Dictionary with user_id, session_id, and token payload
        
    Raises:
        HTTPException: If session not found in request state
    """
    if not hasattr(request.state, "user_id"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No active session",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return {
        "user_id": request.state.user_id,
        "session_id": request.state.session_id,
        "token_payload": request.state.token_payload,
    }


async def get_current_user_from_session(request: Request) -> str:
    """
    Get current user ID from session.
    
    Args:
        request: FastAPI request
        
    Returns:
        User ID string
        
    Raises:
        HTTPException: If session not found
    """
    session_info = await get_current_session(request)
    return session_info["user_id"]


def require_active_session(func):
    """
    Decorator to require active session for a route.
    
    Usage:
        @app.get("/protected")
        @require_active_session
        async def protected_route(request: Request):
            user_id = request.state.user_id
            return {"user_id": user_id}
    """
    async def wrapper(*args, **kwargs):
        request = kwargs.get("request") or args[0]
        if not hasattr(request.state, "user_id"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Active session required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return await func(*args, **kwargs)
    return wrapper
