"""
Pydantic models for RBAC.
"""

from typing import List, Dict, Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator


class Permission(BaseModel):
    """Permission model in format 'resource:action'."""
    resource: str = Field(..., description="Resource name (e.g., 'strategies', 'trades')")
    action: str = Field(..., description="Action name (e.g., 'create', 'read', 'update', 'delete', 'execute')")
    
    @property
    def permission_string(self) -> str:
        """Get permission as string in format 'resource:action'."""
        return f"{self.resource}:{self.action}"
    
    @classmethod
    def from_string(cls, permission: str) -> "Permission":
        """Create Permission from string format 'resource:action'."""
        parts = permission.split(":")
        if len(parts) != 2:
            raise ValueError(f"Invalid permission format: {permission}. Expected 'resource:action'")
        return cls(resource=parts[0], action=parts[1])


class Role(BaseModel):
    """Role model."""
    id: Optional[str] = None
    name: str = Field(..., description="Role name (admin, trader, viewer)")
    description: Optional[str] = Field(None, description="Role description")
    permissions: List[str] = Field(default_factory=list, description="List of permissions in 'resource:action' format")
    created_at: Optional[datetime] = None
    
    @validator("name")
    def validate_name(cls, v):
        """Validate role name."""
        allowed_roles = ["admin", "trader", "viewer"]
        if v.lower() not in allowed_roles:
            raise ValueError(f"Role name must be one of: {', '.join(allowed_roles)}")
        return v.lower()
    
    @validator("permissions")
    def validate_permissions(cls, v):
        """Validate permission format."""
        for perm in v:
            if perm != "*" and ":" not in perm:
                raise ValueError(f"Invalid permission format: {perm}. Expected 'resource:action' or '*'")
        return v


class RoleCreate(BaseModel):
    """Model for creating a new role."""
    name: str = Field(..., description="Role name")
    description: Optional[str] = Field(None, description="Role description")
    permissions: List[str] = Field(default_factory=list, description="List of permissions")
    
    @validator("name")
    def validate_name(cls, v):
        """Validate role name."""
        allowed_roles = ["admin", "trader", "viewer"]
        if v.lower() not in allowed_roles:
            raise ValueError(f"Role name must be one of: {', '.join(allowed_roles)}")
        return v.lower()


class RoleUpdate(BaseModel):
    """Model for updating a role."""
    description: Optional[str] = None
    permissions: Optional[List[str]] = None
    
    @validator("permissions")
    def validate_permissions(cls, v):
        """Validate permission format."""
        if v is not None:
            for perm in v:
                if perm != "*" and ":" not in perm:
                    raise ValueError(f"Invalid permission format: {perm}. Expected 'resource:action' or '*'")
        return v


class RoleResponse(BaseModel):
    """Response model for role."""
    id: str
    name: str
    description: Optional[str]
    permissions: List[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserRole(BaseModel):
    """User role assignment model."""
    user_id: str
    role_id: str
    assigned_at: Optional[datetime] = None
    assigned_by: Optional[str] = None


class UserRoleAssignment(BaseModel):
    """Model for assigning role to user."""
    role_id: str = Field(..., description="Role ID to assign")


class UserPermissionsResponse(BaseModel):
    """Response model for user permissions."""
    user_id: str
    roles: List[RoleResponse]
    effective_permissions: List[str] = Field(..., description="All permissions from all roles")
    has_admin: bool = Field(..., description="Whether user has admin role")
