"""
FastAPI dependencies for permission checking.
"""

from typing import List, Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

from src.auth.middleware import get_current_user
from src.database import get_db
from src.rbac.rbac_service import RBACService
from src.rbac.permissions import check_permission, has_any_permission
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

security = HTTPBearer()


async def get_current_user_with_permissions(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get current user with their permissions.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        User dict with permissions
    """
    rbac_service = RBACService(db)
    user_perms = await rbac_service.get_user_permissions(current_user["user_id"])
    
    return {
        **current_user,
        "roles": [role.name for role in user_perms.roles],
        "permissions": user_perms.effective_permissions,
        "has_admin": user_perms.has_admin,
    }


def require_role(role_name: str):
    """
    Dependency to require a specific role.
    
    Args:
        role_name: Required role name
        
    Returns:
        FastAPI dependency function
        
    Example:
        @app.get("/admin-only")
        async def admin_route(user: dict = Depends(require_role("admin"))):
            return {"message": "Admin access granted"}
    """
    async def check_role(
        user: dict = Depends(get_current_user_with_permissions)
    ) -> dict:
        if role_name not in user.get("roles", []):
            logger.warning(
                f"User {user['user_id']} attempted to access resource requiring role '{role_name}'"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {role_name}",
            )
        return user
    
    return check_role


def require_permission(permission: str):
    """
    Dependency to require a specific permission.
    
    Args:
        permission: Required permission in format 'resource:action'
        
    Returns:
        FastAPI dependency function
        
    Example:
        @app.post("/strategies")
        async def create_strategy(user: dict = Depends(require_permission("strategies:create"))):
            return {"message": "Strategy created"}
    """
    async def check_perm(
        user: dict = Depends(get_current_user_with_permissions)
    ) -> dict:
        user_permissions = user.get("permissions", [])
        
        if not check_permission(user_permissions, permission):
            logger.warning(
                f"User {user['user_id']} attempted to access resource requiring permission '{permission}'"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required permission: {permission}",
            )
        return user
    
    return check_perm


def require_any_permission(permissions: List[str]):
    """
    Dependency to require any of the specified permissions.
    
    Args:
        permissions: List of permissions (user needs at least one)
        
    Returns:
        FastAPI dependency function
        
    Example:
        @app.get("/trades")
        async def get_trades(
            user: dict = Depends(require_any_permission(["trades:read", "trades:execute"]))
        ):
            return {"trades": []}
    """
    async def check_perms(
        user: dict = Depends(get_current_user_with_permissions)
    ) -> dict:
        user_permissions = user.get("permissions", [])
        
        if not has_any_permission(user_permissions, permissions):
            logger.warning(
                f"User {user['user_id']} attempted to access resource requiring one of: {permissions}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required one of: {', '.join(permissions)}",
            )
        return user
    
    return check_perms


def require_admin():
    """
    Dependency to require admin role.
    
    Returns:
        FastAPI dependency function
        
    Example:
        @app.post("/users/{user_id}/roles")
        async def assign_role(user: dict = Depends(require_admin())):
            return {"message": "Role assigned"}
    """
    return require_role("admin")
