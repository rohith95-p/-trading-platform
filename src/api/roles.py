"""
Role management API endpoints.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import logging

from src.database import get_db
from src.auth.middleware import get_current_user
from src.rbac.models import (
    RoleResponse,
    RoleCreate,
    RoleUpdate,
    UserRoleAssignment,
    UserPermissionsResponse,
)
from src.rbac.rbac_service import RBACService
from src.rbac.decorators import require_admin, get_current_user_with_permissions

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/roles", tags=["roles"])


@router.get("", response_model=List[RoleResponse])
async def list_roles(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all available roles.
    
    Returns:
        List of roles
    """
    rbac_service = RBACService(db)
    roles = await rbac_service.list_roles()
    return roles


@router.get("/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get role details by ID.
    
    Args:
        role_id: Role ID
        
    Returns:
        Role details
        
    Raises:
        HTTPException: If role not found
    """
    rbac_service = RBACService(db)
    role = await rbac_service.get_role_by_id(role_id)
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role with ID '{role_id}' not found"
        )
    
    return role


@router.post("/{role_id}/update", response_model=RoleResponse)
async def update_role(
    role_id: str,
    role_update: RoleUpdate,
    current_user: dict = Depends(require_admin()),
    db: Session = Depends(get_db)
):
    """
    Update a role (admin only).
    
    Args:
        role_id: Role ID
        role_update: Role update data
        
    Returns:
        Updated role
        
    Raises:
        HTTPException: If role not found
    """
    rbac_service = RBACService(db)
    
    try:
        role = await rbac_service.update_role(role_id, role_update)
        logger.info(f"Role {role_id} updated by user {current_user['user_id']}")
        return role
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/users/{user_id}/roles", response_model=dict)
async def assign_role_to_user(
    user_id: str,
    assignment: UserRoleAssignment,
    current_user: dict = Depends(require_admin()),
    db: Session = Depends(get_db)
):
    """
    Assign a role to a user (admin only).
    
    Args:
        user_id: User ID
        assignment: Role assignment data
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If role not found or already assigned
    """
    # Prevent users from elevating their own privileges
    if user_id == current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify your own roles"
        )
    
    rbac_service = RBACService(db)
    
    try:
        user_role = await rbac_service.assign_role_to_user(
            user_id=user_id,
            role_id=assignment.role_id,
            assigned_by=current_user["user_id"]
        )
        
        logger.info(
            f"Role {assignment.role_id} assigned to user {user_id} by {current_user['user_id']}"
        )
        
        return {
            "message": "Role assigned successfully",
            "user_id": user_role.user_id,
            "role_id": user_role.role_id,
            "assigned_at": user_role.assigned_at
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/users/{user_id}/roles/{role_id}", response_model=dict)
async def remove_role_from_user(
    user_id: str,
    role_id: str,
    current_user: dict = Depends(require_admin()),
    db: Session = Depends(get_db)
):
    """
    Remove a role from a user (admin only).
    
    Args:
        user_id: User ID
        role_id: Role ID
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If role not assigned to user
    """
    # Prevent users from modifying their own roles
    if user_id == current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify your own roles"
        )
    
    rbac_service = RBACService(db)
    
    try:
        await rbac_service.remove_role_from_user(
            user_id=user_id,
            role_id=role_id,
            removed_by=current_user["user_id"]
        )
        
        logger.info(
            f"Role {role_id} removed from user {user_id} by {current_user['user_id']}"
        )
        
        return {
            "message": "Role removed successfully",
            "user_id": user_id,
            "role_id": role_id
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/users/{user_id}/permissions", response_model=UserPermissionsResponse)
async def get_user_permissions(
    user_id: str,
    current_user: dict = Depends(get_current_user_with_permissions),
    db: Session = Depends(get_db)
):
    """
    Get user's effective permissions.
    
    Users can view their own permissions.
    Admins can view any user's permissions.
    
    Args:
        user_id: User ID
        
    Returns:
        User permissions
        
    Raises:
        HTTPException: If user not authorized
    """
    # Users can only view their own permissions unless they're admin
    if user_id != current_user["user_id"] and not current_user.get("has_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot view other users' permissions"
        )
    
    rbac_service = RBACService(db)
    user_perms = await rbac_service.get_user_permissions(user_id)
    
    return user_perms


@router.get("/users/{user_id}/roles", response_model=List[RoleResponse])
async def get_user_roles(
    user_id: str,
    current_user: dict = Depends(get_current_user_with_permissions),
    db: Session = Depends(get_db)
):
    """
    Get all roles assigned to a user.
    
    Users can view their own roles.
    Admins can view any user's roles.
    
    Args:
        user_id: User ID
        
    Returns:
        List of roles
        
    Raises:
        HTTPException: If user not authorized
    """
    # Users can only view their own roles unless they're admin
    if user_id != current_user["user_id"] and not current_user.get("has_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot view other users' roles"
        )
    
    rbac_service = RBACService(db)
    roles = await rbac_service.get_user_roles(user_id)
    
    return roles
