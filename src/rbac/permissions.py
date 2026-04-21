"""
Permission definitions and checking logic.
"""

from typing import List, Set

# Default permissions for each role
ADMIN_PERMISSIONS = ["*"]  # Wildcard - all permissions

TRADER_PERMISSIONS = [
    # Strategies
    "strategies:create",
    "strategies:read",
    "strategies:update",
    "strategies:delete",
    "strategies:execute",
    # Trades
    "trades:create",
    "trades:read",
    "trades:update",
    "trades:delete",
    "trades:execute",
    # Positions
    "positions:create",
    "positions:read",
    "positions:update",
    "positions:delete",
    # API Keys
    "api_keys:create",
    "api_keys:read",
    "api_keys:update",
    "api_keys:delete",
    # Signals (read only)
    "signals:read",
]

VIEWER_PERMISSIONS = [
    # Read-only access to all resources
    "strategies:read",
    "trades:read",
    "positions:read",
    "api_keys:read",
    "signals:read",
    "users:read",
]

# Map role names to their default permissions
DEFAULT_ROLE_PERMISSIONS = {
    "admin": ADMIN_PERMISSIONS,
    "trader": TRADER_PERMISSIONS,
    "viewer": VIEWER_PERMISSIONS,
}


def check_permission(user_permissions: List[str], required_permission: str) -> bool:
    """
    Check if user has a specific permission.
    
    Args:
        user_permissions: List of user's permissions
        required_permission: Required permission in format 'resource:action'
        
    Returns:
        True if user has the permission
    """
    # Admin wildcard check
    if "*" in user_permissions:
        return True
    
    # Exact match
    if required_permission in user_permissions:
        return True
    
    # Check for resource wildcard (e.g., "strategies:*")
    if ":" in required_permission:
        resource, action = required_permission.split(":", 1)
        resource_wildcard = f"{resource}:*"
        if resource_wildcard in user_permissions:
            return True
    
    return False


def has_any_permission(user_permissions: List[str], required_permissions: List[str]) -> bool:
    """
    Check if user has any of the required permissions.
    
    Args:
        user_permissions: List of user's permissions
        required_permissions: List of required permissions
        
    Returns:
        True if user has at least one of the required permissions
    """
    for perm in required_permissions:
        if check_permission(user_permissions, perm):
            return True
    return False


def has_all_permissions(user_permissions: List[str], required_permissions: List[str]) -> bool:
    """
    Check if user has all of the required permissions.
    
    Args:
        user_permissions: List of user's permissions
        required_permissions: List of required permissions
        
    Returns:
        True if user has all required permissions
    """
    for perm in required_permissions:
        if not check_permission(user_permissions, perm):
            return False
    return True


def get_effective_permissions(roles_permissions: List[List[str]]) -> Set[str]:
    """
    Get effective permissions from multiple roles.
    
    Args:
        roles_permissions: List of permission lists from different roles
        
    Returns:
        Set of unique permissions
    """
    effective = set()
    for role_perms in roles_permissions:
        effective.update(role_perms)
    return effective
