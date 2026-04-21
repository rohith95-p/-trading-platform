"""
RBAC service for role and permission management.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import text

from src.rbac.models import (
    Role,
    RoleCreate,
    RoleUpdate,
    RoleResponse,
    UserRole,
    UserRoleAssignment,
    UserPermissionsResponse,
)
from src.rbac.permissions import (
    DEFAULT_ROLE_PERMISSIONS,
    check_permission,
    has_any_permission,
    get_effective_permissions,
)

logger = logging.getLogger(__name__)


class RBACService:
    """Service for managing roles and permissions."""
    
    def __init__(self, db: Session):
        """
        Initialize RBAC service.
        
        Args:
            db: Database session
        """
        self.db = db
    
    async def initialize_default_roles(self) -> None:
        """Initialize default roles if they don't exist."""
        default_roles = [
            {
                "name": "admin",
                "description": "Full system access, can manage users, roles, and all resources",
                "permissions": DEFAULT_ROLE_PERMISSIONS["admin"],
            },
            {
                "name": "trader",
                "description": "Can create strategies, execute trades, manage own API keys",
                "permissions": DEFAULT_ROLE_PERMISSIONS["trader"],
            },
            {
                "name": "viewer",
                "description": "Read-only access to own data, cannot execute trades",
                "permissions": DEFAULT_ROLE_PERMISSIONS["viewer"],
            },
        ]
        
        for role_data in default_roles:
            existing = await self.get_role_by_name(role_data["name"])
            if not existing:
                await self.create_role(RoleCreate(**role_data))
                logger.info(f"Created default role: {role_data['name']}")
    
    async def create_role(self, role: RoleCreate) -> RoleResponse:
        """
        Create a new role.
        
        Args:
            role: Role creation data
            
        Returns:
            Created role
            
        Raises:
            ValueError: If role already exists
        """
        # Check if role already exists
        existing = await self.get_role_by_name(role.name)
        if existing:
            raise ValueError(f"Role '{role.name}' already exists")
        
        # Create role
        role_id = str(uuid.uuid4())
        query = text("""
            INSERT INTO roles (id, name, description, permissions, created_at)
            VALUES (:id, :name, :description, :permissions, :created_at)
            RETURNING id, name, description, permissions, created_at
        """)
        
        result = self.db.execute(
            query,
            {
                "id": role_id,
                "name": role.name,
                "description": role.description,
                "permissions": role.permissions,
                "created_at": datetime.utcnow(),
            }
        )
        self.db.commit()
        
        row = result.fetchone()
        return RoleResponse(
            id=row[0],
            name=row[1],
            description=row[2],
            permissions=row[3],
            created_at=row[4],
        )
    
    async def get_role_by_id(self, role_id: str) -> Optional[RoleResponse]:
        """
        Get role by ID.
        
        Args:
            role_id: Role ID
            
        Returns:
            Role or None if not found
        """
        query = text("""
            SELECT id, name, description, permissions, created_at
            FROM roles
            WHERE id = :role_id
        """)
        
        result = self.db.execute(query, {"role_id": role_id})
        row = result.fetchone()
        
        if not row:
            return None
        
        return RoleResponse(
            id=row[0],
            name=row[1],
            description=row[2],
            permissions=row[3],
            created_at=row[4],
        )
    
    async def get_role_by_name(self, name: str) -> Optional[RoleResponse]:
        """
        Get role by name.
        
        Args:
            name: Role name
            
        Returns:
            Role or None if not found
        """
        query = text("""
            SELECT id, name, description, permissions, created_at
            FROM roles
            WHERE name = :name
        """)
        
        result = self.db.execute(query, {"name": name})
        row = result.fetchone()
        
        if not row:
            return None
        
        return RoleResponse(
            id=row[0],
            name=row[1],
            description=row[2],
            permissions=row[3],
            created_at=row[4],
        )
    
    async def list_roles(self) -> List[RoleResponse]:
        """
        List all roles.
        
        Returns:
            List of roles
        """
        query = text("""
            SELECT id, name, description, permissions, created_at
            FROM roles
            ORDER BY name
        """)
        
        result = self.db.execute(query)
        rows = result.fetchall()
        
        return [
            RoleResponse(
                id=row[0],
                name=row[1],
                description=row[2],
                permissions=row[3],
                created_at=row[4],
            )
            for row in rows
        ]
    
    async def update_role(self, role_id: str, role_update: RoleUpdate) -> RoleResponse:
        """
        Update a role.
        
        Args:
            role_id: Role ID
            role_update: Role update data
            
        Returns:
            Updated role
            
        Raises:
            ValueError: If role not found
        """
        # Check if role exists
        existing = await self.get_role_by_id(role_id)
        if not existing:
            raise ValueError(f"Role with ID '{role_id}' not found")
        
        # Build update query
        updates = []
        params = {"role_id": role_id}
        
        if role_update.description is not None:
            updates.append("description = :description")
            params["description"] = role_update.description
        
        if role_update.permissions is not None:
            updates.append("permissions = :permissions")
            params["permissions"] = role_update.permissions
        
        if not updates:
            return existing
        
        query = text(f"""
            UPDATE roles
            SET {', '.join(updates)}
            WHERE id = :role_id
            RETURNING id, name, description, permissions, created_at
        """)
        
        result = self.db.execute(query, params)
        self.db.commit()
        
        row = result.fetchone()
        return RoleResponse(
            id=row[0],
            name=row[1],
            description=row[2],
            permissions=row[3],
            created_at=row[4],
        )
    
    async def assign_role_to_user(
        self,
        user_id: str,
        role_id: str,
        assigned_by: str
    ) -> UserRole:
        """
        Assign a role to a user.
        
        Args:
            user_id: User ID
            role_id: Role ID
            assigned_by: ID of user assigning the role
            
        Returns:
            User role assignment
            
        Raises:
            ValueError: If role not found or already assigned
        """
        # Check if role exists
        role = await self.get_role_by_id(role_id)
        if not role:
            raise ValueError(f"Role with ID '{role_id}' not found")
        
        # Check if already assigned
        existing = await self.get_user_role(user_id, role_id)
        if existing:
            raise ValueError(f"Role '{role.name}' already assigned to user")
        
        # Assign role
        query = text("""
            INSERT INTO user_roles (user_id, role_id, assigned_at, assigned_by)
            VALUES (:user_id, :role_id, :assigned_at, :assigned_by)
            RETURNING user_id, role_id, assigned_at, assigned_by
        """)
        
        result = self.db.execute(
            query,
            {
                "user_id": user_id,
                "role_id": role_id,
                "assigned_at": datetime.utcnow(),
                "assigned_by": assigned_by,
            }
        )
        self.db.commit()
        
        # Log to audit log
        await self._log_role_assignment(user_id, role_id, assigned_by, "assign")
        
        row = result.fetchone()
        return UserRole(
            user_id=row[0],
            role_id=row[1],
            assigned_at=row[2],
            assigned_by=row[3],
        )
    
    async def remove_role_from_user(
        self,
        user_id: str,
        role_id: str,
        removed_by: str
    ) -> bool:
        """
        Remove a role from a user.
        
        Args:
            user_id: User ID
            role_id: Role ID
            removed_by: ID of user removing the role
            
        Returns:
            True if removed successfully
            
        Raises:
            ValueError: If role not assigned to user
        """
        # Check if role is assigned
        existing = await self.get_user_role(user_id, role_id)
        if not existing:
            raise ValueError("Role not assigned to user")
        
        # Remove role
        query = text("""
            DELETE FROM user_roles
            WHERE user_id = :user_id AND role_id = :role_id
        """)
        
        self.db.execute(query, {"user_id": user_id, "role_id": role_id})
        self.db.commit()
        
        # Log to audit log
        await self._log_role_assignment(user_id, role_id, removed_by, "remove")
        
        return True
    
    async def get_user_role(self, user_id: str, role_id: str) -> Optional[UserRole]:
        """
        Get user role assignment.
        
        Args:
            user_id: User ID
            role_id: Role ID
            
        Returns:
            User role or None if not found
        """
        query = text("""
            SELECT user_id, role_id, assigned_at, assigned_by
            FROM user_roles
            WHERE user_id = :user_id AND role_id = :role_id
        """)
        
        result = self.db.execute(query, {"user_id": user_id, "role_id": role_id})
        row = result.fetchone()
        
        if not row:
            return None
        
        return UserRole(
            user_id=row[0],
            role_id=row[1],
            assigned_at=row[2],
            assigned_by=row[3],
        )
    
    async def get_user_roles(self, user_id: str) -> List[RoleResponse]:
        """
        Get all roles assigned to a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of roles
        """
        query = text("""
            SELECT r.id, r.name, r.description, r.permissions, r.created_at
            FROM roles r
            JOIN user_roles ur ON r.id = ur.role_id
            WHERE ur.user_id = :user_id
            ORDER BY r.name
        """)
        
        result = self.db.execute(query, {"user_id": user_id})
        rows = result.fetchall()
        
        return [
            RoleResponse(
                id=row[0],
                name=row[1],
                description=row[2],
                permissions=row[3],
                created_at=row[4],
            )
            for row in rows
        ]
    
    async def get_user_permissions(self, user_id: str) -> UserPermissionsResponse:
        """
        Get all effective permissions for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            User permissions response
        """
        roles = await self.get_user_roles(user_id)
        
        # Get effective permissions
        all_permissions = [role.permissions for role in roles]
        effective_permissions = list(get_effective_permissions(all_permissions))
        
        # Check if user has admin role
        has_admin = any(role.name == "admin" for role in roles)
        
        return UserPermissionsResponse(
            user_id=user_id,
            roles=roles,
            effective_permissions=effective_permissions,
            has_admin=has_admin,
        )
    
    async def check_user_permission(self, user_id: str, permission: str) -> bool:
        """
        Check if user has a specific permission.
        
        Args:
            user_id: User ID
            permission: Required permission
            
        Returns:
            True if user has the permission
        """
        user_perms = await self.get_user_permissions(user_id)
        return check_permission(user_perms.effective_permissions, permission)
    
    async def check_user_role(self, user_id: str, role_name: str) -> bool:
        """
        Check if user has a specific role.
        
        Args:
            user_id: User ID
            role_name: Role name
            
        Returns:
            True if user has the role
        """
        roles = await self.get_user_roles(user_id)
        return any(role.name == role_name for role in roles)
    
    async def assign_default_role(self, user_id: str) -> UserRole:
        """
        Assign default 'viewer' role to a new user.
        
        Args:
            user_id: User ID
            
        Returns:
            User role assignment
        """
        viewer_role = await self.get_role_by_name("viewer")
        if not viewer_role:
            raise ValueError("Default 'viewer' role not found. Run initialize_default_roles first.")
        
        return await self.assign_role_to_user(user_id, viewer_role.id, "system")
    
    async def _log_role_assignment(
        self,
        user_id: str,
        role_id: str,
        performed_by: str,
        action: str
    ) -> None:
        """
        Log role assignment/removal to audit log.
        
        Args:
            user_id: User ID
            role_id: Role ID
            performed_by: ID of user performing the action
            action: Action type ('assign' or 'remove')
        """
        try:
            query = text("""
                INSERT INTO audit_log (
                    id, user_id, action, resource_type, resource_id,
                    details, ip_address, user_agent, created_at
                )
                VALUES (
                    :id, :user_id, :action, :resource_type, :resource_id,
                    :details, :ip_address, :user_agent, :created_at
                )
            """)
            
            self.db.execute(
                query,
                {
                    "id": str(uuid.uuid4()),
                    "user_id": performed_by,
                    "action": f"role_{action}",
                    "resource_type": "user_role",
                    "resource_id": user_id,
                    "details": {"role_id": role_id, "target_user_id": user_id},
                    "ip_address": None,
                    "user_agent": None,
                    "created_at": datetime.utcnow(),
                }
            )
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to log role assignment: {str(e)}")
