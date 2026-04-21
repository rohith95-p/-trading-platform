"""
Authentication middleware for FastAPI.
"""

from functools import wraps
from typing import Optional, Callable
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

from src.auth.jwt_handler import JWTHandler

logger = logging.getLogger(__name__)

# Security scheme for Swagger UI
security = HTTPBearer()

# Initialize JWT handler
jwt_handler = JWTHandler()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Get current authenticated user from JWT token.
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        User information from token
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    token = credentials.credentials
    
    try:
        payload = jwt_handler.verify_token(token, token_type="access")
        return {
            "user_id": payload["sub"],
            "email": payload["email"],
        }
    except Exception as e:
        logger.warning(f"Authentication failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[dict]:
    """
    Get current user if authenticated, None otherwise.
    
    Args:
        credentials: HTTP authorization credentials (optional)
        
    Returns:
        User information or None
    """
    if not credentials:
        return None
    
    try:
        token = credentials.credentials
        payload = jwt_handler.verify_token(token, token_type="access")
        return {
            "user_id": payload["sub"],
            "email": payload["email"],
        }
    except Exception:
        return None


def auth_required(func: Callable) -> Callable:
    """
    Decorator to require authentication for a route.
    
    Usage:
        @app.get("/protected")
        @auth_required
        async def protected_route(current_user: dict = Depends(get_current_user)):
            return {"user": current_user}
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)
    return wrapper


def optional_auth(func: Callable) -> Callable:
    """
    Decorator for optional authentication.
    
    Usage:
        @app.get("/public")
        @optional_auth
        async def public_route(current_user: Optional[dict] = Depends(get_current_user_optional)):
            if current_user:
                return {"message": f"Hello {current_user['email']}"}
            return {"message": "Hello guest"}
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)
    return wrapper


def require_verified_email(func: Callable) -> Callable:
    """
    Decorator to require verified email.
    
    Usage:
        @app.get("/verified-only")
        @require_verified_email
        async def verified_route(current_user: dict = Depends(get_current_user)):
            return {"message": "Email verified"}
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # TODO: Check if user's email is verified
        return await func(*args, **kwargs)
    return wrapper


def require_premium(func: Callable) -> Callable:
    """
    Decorator to require premium subscription.
    
    Usage:
        @app.get("/premium-only")
        @require_premium
        async def premium_route(current_user: dict = Depends(get_current_user)):
            return {"message": "Premium feature"}
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # TODO: Check if user has premium subscription
        return await func(*args, **kwargs)
    return wrapper
