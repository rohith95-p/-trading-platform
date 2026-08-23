"""
Unit tests for RBAC (Role-Based Access Control) system.

Tests cover:
- Role creation and management
- Permission checking
- Role assignment and removal
- User permissions
- Permission inheritance
- Security constraints
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.orm import Session

from src.rbac.models import (
    Role,
    RoleCreate,
    RoleUpdate,
    RoleResponse,
    UserRole,
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
    has_all_permissions,
    get_effective_permissions,
)


class TestPermissionChecking:
    """Test permission checking logic."""
    
    def test_check_permission_exact_match(self):
        """Test exact permission match."""
        user_perms = ["strategies:create", "trades:read"]
        assert check_permission(user_perms, "strategies:create") is True
        assert check_permission(user_perms, "trades:read") is True
        assert check_permission(user_perms, "trades:execute") is False
    
    def test_check_permission_admin_wildcard(self):
        """Test admin wildcard permission."""
        user_perms = ["*"]
        assert check_permission(user_perms, "strategies:create") is True
        assert check_permission(user_perms, "trades:execute") is True
        assert check_permission(user_perms, "anything:anything") is True
    
    def test_check_permission_resource_wildcard(self):
        """Test resource wildcard permission."""
        user_perms = ["strategies:*"]
        assert check_permission(user_perms, "strategies:create") is True
        assert check_permission(user_perms, "strategies:read") is True
        assert check_permission(user_perms, "strategies:delete") is True
        assert check_permission(user_perms, "trades:read") is False
    
    def test_has_any_permission(self):
        """Test checking for any of multiple permissions."""
        user_perms = ["strategies:read", "trades:read"]
        required = ["strategies:create", "strategies:read"]
        assert has_any_permission(user_perms, required) is True
        
        required = ["strategies:create", "trades:execute"]
        assert has_any_permission(user_perms, required) is False
    
    def test_has_all_permissions(self):
        """Test checking for all permissions."""
        user_perms = ["strategies:read", "trades:read", "positions:read"]
        required = ["strategies:read", "trades:read"]
        assert has_all_permissions(user_perms, required) is True
        
        required = ["strategies:read", "trades:execute"]
        assert has_all_permissions(user_perms, required) is False
    
    def test_get_effective_permissions(self):
        """Test getting effective permissions from multiple roles."""
        role1_perms = ["strategies:read", "trades:read"]
        role2_perms = ["trades:read", "positions:read"]
        
        effective = get_effective_permissions([role1_perms, role2_perms])
        
        assert "strategies:read" in effective
        assert "trades:read" in effective
        assert "positions:read" in effective
        assert len(effective) == 3  # No duplicates


class TestRoleModels:
    """Test role Pydantic models."""
    
    def test_role_create_valid(self):
        """Test creating valid role."""
        role = RoleCreate(
            name="admin",
            description="Admin role",
            permissions=["*"]
        )
        assert role.name == "admin"
        assert role.permissions == ["*"]
    
    def test_role_create_invalid_name(self):
        """Test creating role with invalid name."""
        with pytest.raises(ValueError, match="Role name must be one of"):
            RoleCreate(
                name="invalid_role",
                description="Invalid",
                permissions=[]
            )
    
    def test_role_update_valid(self):
        """Test updating role."""
        update = RoleUpdate(
            description="Updated description",
            permissions=["strategies:*"]
        )
        assert update.description == "Updated description"
        assert update.permissions == ["strategies:*"]


@pytest.fixture
def mock_db():
    """Create mock database session."""
    db = Mock(spec=Session)
    db.execute = Mock()
    db.commit = Mock()
    return db


@pytest.fixture
def rbac_service(mock_db):
    """Create RBAC service with mock database."""
    return RBACService(mock_db)


class TestRBACService:
    """Test RBAC service."""
    
    @pytest.mark.asyncio
    async def test_create_role(self, rbac_service, mock_db):
        """Test creating a new role."""
        # Mock get_role_by_name to return None (role doesn't exist)
        with patch.object(rbac_service, 'get_role_by_name', return_value=None):
            # Mock database execute
            mock_result = Mock()
            mock_result.fetchone.return_value = (
                "role-id",
                "trader",
                "Trader role",
                ["strategies:*"],
                datetime.utcnow()
            )
            mock_db.execute.return_value = mock_result
            
            role_create = RoleCreate(
                name="trader",
                description="Trader role",
                permissions=["strategies:*"]
            )
            
            role = await rbac_service.create_role(role_create)
            
            assert role.name == "trader"
            assert role.description == "Trader role"
            assert role.permissions == ["strategies:*"]
            mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_role_already_exists(self, rbac_service):
        """Test creating role that already exists."""
        existing_role = RoleResponse(
            id="role-id",
            name="trader",
            description="Existing",
            permissions=[],
            created_at=datetime.utcnow()
        )
        
        with patch.object(rbac_service, 'get_role_by_name', return_value=existing_role):
            role_create = RoleCreate(
                name="trader",
                description="New",
                permissions=[]
            )
            
            with pytest.raises(ValueError, match="already exists"):
                await rbac_service.create_role(role_create)
    
    @pytest.mark.asyncio
    async def test_get_role_by_id(self, rbac_service, mock_db):
        """Test getting role by ID."""
        mock_result = Mock()
        mock_result.fetchone.return_value = (
            "role-id",
            "admin",
            "Admin role",
            ["*"],
            datetime.utcnow()
        )
        mock_db.execute.return_value = mock_result
        
        role = await rbac_service.get_role_by_id("role-id")
        
        assert role is not None
        assert role.name == "admin"
        assert role.permissions == ["*"]
    
    @pytest.mark.asyncio
    async def test_get_role_by_id_not_found(self, rbac_service, mock_db):
        """Test getting non-existent role."""
        mock_result = Mock()
        mock_result.fetchone.return_value = None
        mock_db.execute.return_value = mock_result
        
        role = await rbac_service.get_role_by_id("nonexistent")
        
        assert role is None
    
    @pytest.mark.asyncio
    async def test_list_roles(self, rbac_service, mock_db):
        """Test listing all roles."""
        mock_result = Mock()
        mock_result.fetchall.return_value = [
            ("role-1", "admin", "Admin", ["*"], datetime.utcnow()),
            ("role-2", "trader", "Trader", ["strategies:*"], datetime.utcnow()),
            ("role-3", "viewer", "Viewer", ["*:read"], datetime.utcnow()),
        ]
        mock_db.execute.return_value = mock_result
        
        roles = await rbac_service.list_roles()
        
        assert len(roles) == 3
        assert roles[0].name == "admin"
        assert roles[1].name == "trader"
        assert roles[2].name == "viewer"
    
    @pytest.mark.asyncio
    async def test_assign_role_to_user(self, rbac_service, mock_db):
        """Test assigning role to user."""
        # Mock get_role_by_id
        role = RoleResponse(
            id="role-id",
            name="trader",
            description="Trader",
            permissions=["strategies:*"],
            created_at=datetime.utcnow()
        )
        
        with patch.object(rbac_service, 'get_role_by_id', return_value=role):
            with patch.object(rbac_service, 'get_user_role', return_value=None):
                with patch.object(rbac_service, '_log_role_assignment', return_value=None):
                    mock_result = Mock()
                    mock_result.fetchone.return_value = (
                        "user-id",
                        "role-id",
                        datetime.utcnow(),
                        "admin-id"
                    )
                    mock_db.execute.return_value = mock_result
                    
                    user_role = await rbac_service.assign_role_to_user(
                        "user-id",
                        "role-id",
                        "admin-id"
                    )
                    
                    assert user_role.user_id == "user-id"
                    assert user_role.role_id == "role-id"
                    mock_db.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_assign_role_already_assigned(self, rbac_service):
        """Test assigning role that's already assigned."""
        role = RoleResponse(
            id="role-id",
            name="trader",
            description="Trader",
            permissions=[],
            created_at=datetime.utcnow()
        )
        
        existing_assignment = UserRole(
            user_id="user-id",
            role_id="role-id",
            assigned_at=datetime.utcnow(),
            assigned_by="admin-id"
        )
        
        with patch.object(rbac_service, 'get_role_by_id', return_value=role):
            with patch.object(rbac_service, 'get_user_role', return_value=existing_assignment):
                with pytest.raises(ValueError, match="already assigned"):
                    await rbac_service.assign_role_to_user(
                        "user-id",
                        "role-id",
                        "admin-id"
                    )
    
    @pytest.mark.asyncio
    async def test_remove_role_from_user(self, rbac_service, mock_db):
        """Test removing role from user."""
        existing_assignment = UserRole(
            user_id="user-id",
            role_id="role-id",
            assigned_at=datetime.utcnow(),
            assigned_by="admin-id"
        )
        
        with patch.object(rbac_service, 'get_user_role', return_value=existing_assignment):
            with patch.object(rbac_service, '_log_role_assignment', return_value=None):
                result = await rbac_service.remove_role_from_user(
                    "user-id",
                    "role-id",
                    "admin-id"
                )
                
                assert result is True
                mock_db.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_user_roles(self, rbac_service, mock_db):
        """Test getting user's roles."""
        mock_result = Mock()
        mock_result.fetchall.return_value = [
            ("role-1", "trader", "Trader", ["strategies:*"], datetime.utcnow()),
            ("role-2", "viewer", "Viewer", ["*:read"], datetime.utcnow()),
        ]
        mock_db.execute.return_value = mock_result
        
        roles = await rbac_service.get_user_roles("user-id")
        
        assert len(roles) == 2
        assert roles[0].name == "trader"
        assert roles[1].name == "viewer"
    
    @pytest.mark.asyncio
    async def test_get_user_permissions(self, rbac_service):
        """Test getting user's effective permissions."""
        roles = [
            RoleResponse(
                id="role-1",
                name="trader",
                description="Trader",
                permissions=["strategies:create", "trades:read"],
                created_at=datetime.utcnow()
            ),
            RoleResponse(
                id="role-2",
                name="viewer",
                description="Viewer",
                permissions=["trades:read", "positions:read"],
                created_at=datetime.utcnow()
            ),
        ]
        
        with patch.object(rbac_service, 'get_user_roles', return_value=roles):
            user_perms = await rbac_service.get_user_permissions("user-id")
            
            assert user_perms.user_id == "user-id"
            assert len(user_perms.roles) == 2
            assert "strategies:create" in user_perms.effective_permissions
            assert "trades:read" in user_perms.effective_permissions
            assert "positions:read" in user_perms.effective_permissions
            assert user_perms.has_admin is False
    
    @pytest.mark.asyncio
    async def test_get_user_permissions_with_admin(self, rbac_service):
        """Test getting permissions for admin user."""
        roles = [
            RoleResponse(
                id="role-1",
                name="admin",
                description="Admin",
                permissions=["*"],
                created_at=datetime.utcnow()
            ),
        ]
        
        with patch.object(rbac_service, 'get_user_roles', return_value=roles):
            user_perms = await rbac_service.get_user_permissions("admin-id")
            
            assert user_perms.has_admin is True
            assert "*" in user_perms.effective_permissions
    
    @pytest.mark.asyncio
    async def test_check_user_permission(self, rbac_service):
        """Test checking if user has specific permission."""
        user_perms = UserPermissionsResponse(
            user_id="user-id",
            roles=[],
            effective_permissions=["strategies:create", "trades:read"],
            has_admin=False
        )
        
        with patch.object(rbac_service, 'get_user_permissions', return_value=user_perms):
            has_perm = await rbac_service.check_user_permission("user-id", "strategies:create")
            assert has_perm is True
            
            has_perm = await rbac_service.check_user_permission("user-id", "trades:execute")
            assert has_perm is False
    
    @pytest.mark.asyncio
    async def test_check_user_role(self, rbac_service):
        """Test checking if user has specific role."""
        roles = [
            RoleResponse(
                id="role-1",
                name="trader",
                description="Trader",
                permissions=[],
                created_at=datetime.utcnow()
            ),
        ]
        
        with patch.object(rbac_service, 'get_user_roles', return_value=roles):
            has_role = await rbac_service.check_user_role("user-id", "trader")
            assert has_role is True
            
            has_role = await rbac_service.check_user_role("user-id", "admin")
            assert has_role is False
    
    @pytest.mark.asyncio
    async def test_assign_default_role(self, rbac_service):
        """Test assigning default viewer role to new user."""
        viewer_role = RoleResponse(
            id="viewer-role-id",
            name="viewer",
            description="Viewer",
            permissions=["*:read"],
            created_at=datetime.utcnow()
        )
        
        user_role = UserRole(
            user_id="new-user-id",
            role_id="viewer-role-id",
            assigned_at=datetime.utcnow(),
            assigned_by="system"
        )
        
        with patch.object(rbac_service, 'get_role_by_name', return_value=viewer_role):
            with patch.object(rbac_service, 'assign_role_to_user', return_value=user_role):
                result = await rbac_service.assign_default_role("new-user-id")
                
                assert result.user_id == "new-user-id"
                assert result.role_id == "viewer-role-id"


class TestDefaultPermissions:
    """Test default permission sets."""
    
    def test_admin_permissions(self):
        """Test admin has wildcard permission."""
        assert ADMIN_PERMISSIONS == ["*"]
    
    def test_trader_permissions(self):
        """Test trader has appropriate permissions."""
        assert "strategies:create" in TRADER_PERMISSIONS
        assert "trades:execute" in TRADER_PERMISSIONS
        assert "api_keys:create" in TRADER_PERMISSIONS
        assert "signals:read" in TRADER_PERMISSIONS
    
    def test_viewer_permissions(self):
        """Test viewer has only read permissions."""
        for perm in VIEWER_PERMISSIONS:
            assert perm.endswith(":read"), f"Viewer permission {perm} is not read-only"
