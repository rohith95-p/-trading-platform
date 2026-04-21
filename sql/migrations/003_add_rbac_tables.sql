-- Migration: Add RBAC tables
-- Version: 003
-- Description: Add roles and user_roles tables for role-based access control

-- ============================================================================
-- ROLES TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL CHECK (name IN ('admin', 'trader', 'viewer')),
    description TEXT,
    permissions JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL
);

-- Create index on role name for faster lookups
CREATE INDEX IF NOT EXISTS idx_roles_name ON roles(name);

-- ============================================================================
-- USER_ROLES TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_roles (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP DEFAULT NOW() NOT NULL,
    assigned_by UUID REFERENCES users(id) ON DELETE SET NULL,
    PRIMARY KEY (user_id, role_id)
);

-- Create indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_user_roles_user_id ON user_roles(user_id);
CREATE INDEX IF NOT EXISTS idx_user_roles_role_id ON user_roles(role_id);

-- ============================================================================
-- INSERT DEFAULT ROLES
-- ============================================================================

-- Admin role: Full system access
INSERT INTO roles (name, description, permissions)
VALUES (
    'admin',
    'Full system access, can manage users, roles, and all resources',
    '["*"]'::jsonb
)
ON CONFLICT (name) DO NOTHING;

-- Trader role: Can create strategies, execute trades, manage own API keys
INSERT INTO roles (name, description, permissions)
VALUES (
    'trader',
    'Can create strategies, execute trades, manage own API keys',
    '[
        "strategies:create", "strategies:read", "strategies:update", "strategies:delete", "strategies:execute",
        "trades:create", "trades:read", "trades:update", "trades:delete", "trades:execute",
        "positions:create", "positions:read", "positions:update", "positions:delete",
        "api_keys:create", "api_keys:read", "api_keys:update", "api_keys:delete",
        "signals:read"
    ]'::jsonb
)
ON CONFLICT (name) DO NOTHING;

-- Viewer role: Read-only access to own data
INSERT INTO roles (name, description, permissions)
VALUES (
    'viewer',
    'Read-only access to own data, cannot execute trades',
    '[
        "strategies:read",
        "trades:read",
        "positions:read",
        "api_keys:read",
        "signals:read",
        "users:read"
    ]'::jsonb
)
ON CONFLICT (name) DO NOTHING;

-- ============================================================================
-- ASSIGN DEFAULT VIEWER ROLE TO EXISTING USERS
-- ============================================================================

-- Get the viewer role ID and assign it to all existing users who don't have a role
INSERT INTO user_roles (user_id, role_id, assigned_by)
SELECT 
    u.id,
    (SELECT id FROM roles WHERE name = 'viewer'),
    NULL  -- System assignment
FROM users u
WHERE NOT EXISTS (
    SELECT 1 FROM user_roles ur WHERE ur.user_id = u.id
)
ON CONFLICT (user_id, role_id) DO NOTHING;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE roles IS 'Roles for role-based access control';
COMMENT ON TABLE user_roles IS 'User role assignments';
COMMENT ON COLUMN roles.permissions IS 'JSONB array of permissions in format ["resource:action"]';
COMMENT ON COLUMN user_roles.assigned_by IS 'User ID who assigned the role, NULL for system assignments';
