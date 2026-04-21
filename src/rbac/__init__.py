"""
Role-Based Access Control (RBAC) module.

This module provides role and permission management for the trading platform.
"""

from src.rbac.models import (
    Role,
    Permission,
    UserRole,
    RoleCreate,
    RoleUpdate,
    RoleResponse,
    UserRoleAssignment,
    UserPermissionsResponse,
)
from src.rbac.rbac_service import RBACService
from src.rbac.permissions import (
    ADMIN_PERMISSIONS,
    TRADER_PERMISSIONS,
    VIEWER_PERMISSIONS,
    check_permission,
    has_any_permission,
)
from src.rbac.decorators import (
    require_role,
    require_permission,
    require_any_permission,
    get_current_user_with_permissions,
)

__all__ = [
    # Models
    "Role",
    "Permission",
    "UserRole",
    "RoleCreate",
    "RoleUpdate",
    "RoleResponse",
    "UserRoleAssignment",
    "UserPermissionsResponse",
    # Service
    "RBACService",
    # Permissions
    "ADMIN_PERMISSIONS",
    "TRADER_PERMISSIONS",
    "VIEWER_PERMISSIONS",
    "check_permission",
    "has_any_permission",
    # Decorators
    "require_role",
    "require_permission",
    "require_any_permission",
    "get_current_user_with_permissions",
]
