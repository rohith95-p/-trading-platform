# Role-Based Access Control (RBAC) Documentation

## Overview

The Unified Trading Intelligence Platform implements a comprehensive Role-Based Access Control (RBAC) system to manage user permissions and access to resources. This document describes the RBAC architecture, roles, permissions, and usage.

## Table of Contents

1. [Architecture](#architecture)
2. [Roles](#roles)
3. [Permissions](#permissions)
4. [API Endpoints](#api-endpoints)
5. [Usage Examples](#usage-examples)
6. [Security Considerations](#security-considerations)
7. [Database Schema](#database-schema)

## Architecture

The RBAC system consists of the following components:

- **Roles**: Named collections of permissions (admin, trader, viewer)
- **Permissions**: Granular access rights in format `resource:action`
- **User Roles**: Many-to-many relationship between users and roles
- **Permission Checking**: Middleware and decorators for enforcing permissions

### Key Features

- **Hierarchical Permissions**: Admin role has wildcard access to all resources
- **Resource-Based**: Permissions are scoped to specific resources (strategies, trades, etc.)
- **Action-Based**: Each permission specifies an action (create, read, update, delete, execute)
- **Flexible Assignment**: Users can have multiple roles
- **Audit Logging**: All role assignments/removals are logged

## Roles

### Admin

**Description**: Full system access, can manage users, roles, and all resources

**Permissions**: `["*"]` (wildcard - all permissions)

**Capabilities**:
- Manage all users and their roles
- Access all resources across the platform
- Assign/remove roles from users
- View and modify all data

**Use Cases**:
- System administrators
- Platform operators
- Support staff with elevated access

### Trader

**Description**: Can create strategies, execute trades, manage own API keys

**Permissions**:
```json
[
  "strategies:create", "strategies:read", "strategies:update", "strategies:delete", "strategies:execute",
  "trades:create", "trades:read", "trades:update", "trades:delete", "trades:execute",
  "positions:create", "positions:read", "positions:update", "positions:delete",
  "api_keys:create", "api_keys:read", "api_keys:update", "api_keys:delete",
  "signals:read"
]
```

**Capabilities**:
- Create and manage trading strategies
- Execute trades and manage positions
- Add and manage API keys for exchanges
- View trading signals
- Full control over own trading activities

**Use Cases**:
- Active traders
- Strategy developers
- Users who need full trading capabilities

### Viewer

**Description**: Read-only access to own data, cannot execute trades

**Permissions**:
```json
[
  "strategies:read",
  "trades:read",
  "positions:read",
  "api_keys:read",
  "signals:read",
  "users:read"
]
```

**Capabilities**:
- View strategies, trades, and positions
- View API keys (encrypted)
- View trading signals
- Monitor portfolio performance
- No ability to create, modify, or execute

**Use Cases**:
- Portfolio observers
- Auditors
- Users who want read-only access
- New users (default role)

## Permissions

### Permission Format

Permissions follow the format: `resource:action`

**Examples**:
- `strategies:create` - Create new strategies
- `trades:execute` - Execute trades
- `api_keys:read` - View API keys
- `*` - Admin wildcard (all permissions)
- `strategies:*` - All actions on strategies

### Resources

- `strategies` - Trading strategies
- `trades` - Trade execution and history
- `positions` - Open positions
- `api_keys` - Exchange API keys
- `signals` - Trading signals
- `users` - User management

### Actions

- `create` - Create new resources
- `read` - View resources
- `update` - Modify existing resources
- `delete` - Remove resources
- `execute` - Execute actions (trades, strategies)

### Permission Checking

The system supports three types of permission checks:

1. **Exact Match**: `strategies:create` matches exactly
2. **Wildcard**: `*` matches all permissions
3. **Resource Wildcard**: `strategies:*` matches all actions on strategies

## API Endpoints

### List All Roles

```http
GET /api/v1/roles
Authorization: Bearer <token>
```

**Response**:
```json
[
  {
    "id": "role-id",
    "name": "admin",
    "description": "Full system access",
    "permissions": ["*"],
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

### Get Role Details

```http
GET /api/v1/roles/{role_id}
Authorization: Bearer <token>
```

**Response**:
```json
{
  "id": "role-id",
  "name": "trader",
  "description": "Can create strategies and execute trades",
  "permissions": ["strategies:*", "trades:*"],
  "created_at": "2024-01-01T00:00:00Z"
}
```

### Assign Role to User (Admin Only)

```http
POST /api/v1/roles/users/{user_id}/roles
Authorization: Bearer <admin-token>
Content-Type: application/json

{
  "role_id": "role-id"
}
```

**Response**:
```json
{
  "message": "Role assigned successfully",
  "user_id": "user-id",
  "role_id": "role-id",
  "assigned_at": "2024-01-01T00:00:00Z"
}
```

### Remove Role from User (Admin Only)

```http
DELETE /api/v1/roles/users/{user_id}/roles/{role_id}
Authorization: Bearer <admin-token>
```

**Response**:
```json
{
  "message": "Role removed successfully",
  "user_id": "user-id",
  "role_id": "role-id"
}
```

### Get User Permissions

```http
GET /api/v1/roles/users/{user_id}/permissions
Authorization: Bearer <token>
```

**Response**:
```json
{
  "user_id": "user-id",
  "roles": [
    {
      "id": "role-id",
      "name": "trader",
      "description": "Trader role",
      "permissions": ["strategies:*", "trades:*"],
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "effective_permissions": ["strategies:create", "strategies:read", "trades:execute"],
  "has_admin": false
}
```

### Get User Roles

```http
GET /api/v1/roles/users/{user_id}/roles
Authorization: Bearer <token>
```

**Response**:
```json
[
  {
    "id": "role-id",
    "name": "trader",
    "description": "Trader role",
    "permissions": ["strategies:*"],
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

## Usage Examples

### Protecting API Endpoints

#### Require Specific Role

```python
from fastapi import APIRouter, Depends
from src.rbac.decorators import require_role

router = APIRouter()

@router.get("/admin-only")
async def admin_endpoint(user: dict = Depends(require_role("admin"))):
    return {"message": "Admin access granted"}
```

#### Require Specific Permission

```python
from src.rbac.decorators import require_permission

@router.post("/strategies")
async def create_strategy(user: dict = Depends(require_permission("strategies:create"))):
    return {"message": "Strategy created"}
```

#### Require Any of Multiple Permissions

```python
from src.rbac.decorators import require_any_permission

@router.get("/trades")
async def get_trades(
    user: dict = Depends(require_any_permission(["trades:read", "trades:execute"]))
):
    return {"trades": []}
```

#### Get User with Permissions

```python
from src.rbac.decorators import get_current_user_with_permissions

@router.get("/profile")
async def get_profile(user: dict = Depends(get_current_user_with_permissions)):
    return {
        "user_id": user["user_id"],
        "roles": user["roles"],
        "permissions": user["permissions"],
        "has_admin": user["has_admin"]
    }
```

### Programmatic Permission Checking

```python
from src.rbac.rbac_service import RBACService
from src.database import get_db

db = next(get_db())
rbac_service = RBACService(db)

# Check if user has specific permission
has_perm = await rbac_service.check_user_permission(user_id, "strategies:create")

# Check if user has specific role
has_role = await rbac_service.check_user_role(user_id, "admin")

# Get all user permissions
user_perms = await rbac_service.get_user_permissions(user_id)
```

### Assigning Roles Programmatically

```python
from src.rbac.rbac_service import RBACService

rbac_service = RBACService(db)

# Assign default viewer role to new user
await rbac_service.assign_default_role(new_user_id)

# Assign specific role
await rbac_service.assign_role_to_user(
    user_id=user_id,
    role_id=trader_role_id,
    assigned_by=admin_user_id
)

# Remove role
await rbac_service.remove_role_from_user(
    user_id=user_id,
    role_id=role_id,
    removed_by=admin_user_id
)
```

## Security Considerations

### Default Role Assignment

- **New users are automatically assigned the "viewer" role** upon registration
- This ensures least-privilege access by default
- Admins must explicitly grant elevated permissions

### Self-Privilege Escalation Prevention

- **Users cannot modify their own roles**
- Role assignment/removal requires admin privileges
- API endpoints enforce this constraint

### Audit Logging

- **All role assignments and removals are logged** to the audit_log table
- Logs include:
  - User who performed the action
  - Target user
  - Role affected
  - Timestamp
  - IP address and user agent (when available)

### Permission Inheritance

- **Admin role has wildcard access** (`*`)
- Admin permissions override all other checks
- Users with multiple roles get the union of all permissions

### API Security

- **All role management endpoints require authentication**
- Role assignment/removal requires admin role
- Users can view their own permissions
- Admins can view any user's permissions

## Database Schema

### roles Table

```sql
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL CHECK (name IN ('admin', 'trader', 'viewer')),
    description TEXT,
    permissions JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL
);
```

### user_roles Table

```sql
CREATE TABLE user_roles (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP DEFAULT NOW() NOT NULL,
    assigned_by UUID REFERENCES users(id) ON DELETE SET NULL,
    PRIMARY KEY (user_id, role_id)
);
```

### Indexes

```sql
CREATE INDEX idx_roles_name ON roles(name);
CREATE INDEX idx_user_roles_user_id ON user_roles(user_id);
CREATE INDEX idx_user_roles_role_id ON user_roles(role_id);
```

## Migration

To apply the RBAC schema:

```bash
# PostgreSQL
psql -U postgres -d trading_platform -f sql/migrations/003_add_rbac_tables.sql

# Or using the migration script
cd sql/migrations
./migrate.sh  # Linux/Mac
./migrate.ps1  # Windows
```

## Best Practices

1. **Principle of Least Privilege**: Start users with viewer role, grant additional permissions as needed
2. **Regular Audits**: Review role assignments periodically
3. **Separation of Duties**: Don't grant admin role unnecessarily
4. **Permission Granularity**: Use specific permissions rather than wildcards when possible
5. **Audit Logging**: Monitor audit logs for suspicious role changes
6. **Testing**: Test permission checks thoroughly in development
7. **Documentation**: Document custom roles and permissions clearly

## Troubleshooting

### User Cannot Access Resource

1. Check user's roles: `GET /api/v1/roles/users/{user_id}/roles`
2. Check user's permissions: `GET /api/v1/roles/users/{user_id}/permissions`
3. Verify required permission for the endpoint
4. Check if user has the required permission in their effective permissions

### Role Assignment Fails

1. Verify admin authentication
2. Check if role exists
3. Verify user is not trying to modify their own roles
4. Check database constraints

### Permission Check Always Fails

1. Verify permission format: `resource:action`
2. Check if user has any roles assigned
3. Verify default roles were initialized
4. Check database connection

## Future Enhancements

- Custom role creation (beyond admin/trader/viewer)
- Time-based role assignments (temporary elevated access)
- Role templates for common permission sets
- Permission groups for easier management
- Role hierarchy (role inheritance)
- Fine-grained resource-level permissions (e.g., own vs. all resources)

## Support

For questions or issues with RBAC:
- Check the API documentation: `/docs`
- Review audit logs for role changes
- Contact platform administrators
