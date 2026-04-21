-- Migration: Add sessions table for session management
-- Version: 1.1.0
-- Task: 1.10.1 - Create sessions table in database

-- ============================================================================
-- SESSIONS TABLE
-- ============================================================================
-- Session management table for tracking user sessions and JWT tokens
CREATE TABLE IF NOT EXISTS sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  
  -- Token information
  token_hash TEXT NOT NULL UNIQUE,
  
  -- Client information
  ip_address INET,
  user_agent TEXT,
  
  -- Session lifecycle
  created_at TIMESTAMP DEFAULT NOW(),
  last_activity_at TIMESTAMP DEFAULT NOW(),
  expires_at TIMESTAMP NOT NULL,
  
  -- Status
  is_active BOOLEAN DEFAULT true,
  
  -- Metadata
  metadata JSONB DEFAULT '{}'::jsonb,
  
  -- Constraints
  CONSTRAINT valid_expiration CHECK (expires_at > created_at)
);

-- ============================================================================
-- INDEXES
-- ============================================================================

-- Index for user session lookups
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);

-- Index for token hash lookups (for validation)
CREATE INDEX IF NOT EXISTS idx_sessions_token_hash ON sessions(token_hash);

-- Index for active sessions
CREATE INDEX IF NOT EXISTS idx_sessions_is_active ON sessions(is_active);

-- Index for session expiration cleanup
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at);

-- Composite index for user's active sessions
CREATE INDEX IF NOT EXISTS idx_sessions_user_active ON sessions(user_id, is_active) WHERE is_active = true;

-- Index for last activity tracking
CREATE INDEX IF NOT EXISTS idx_sessions_last_activity ON sessions(last_activity_at);

-- ============================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================================================

-- Enable RLS on sessions table
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;

-- Users can view their own sessions
CREATE POLICY "Users can view own sessions" ON sessions
  FOR SELECT USING (auth.uid() = user_id);

-- Users can delete their own sessions (logout)
CREATE POLICY "Users can delete own sessions" ON sessions
  FOR DELETE USING (auth.uid() = user_id);

-- System can insert sessions (handled by auth service)
CREATE POLICY "System can insert sessions" ON sessions
  FOR INSERT WITH CHECK (true);

-- System can update sessions (for activity tracking)
CREATE POLICY "System can update sessions" ON sessions
  FOR UPDATE USING (true);

-- ============================================================================
-- FUNCTIONS AND TRIGGERS
-- ============================================================================

-- Function to update last_activity_at timestamp
CREATE OR REPLACE FUNCTION update_session_activity()
RETURNS TRIGGER AS $$
BEGIN
  NEW.last_activity_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update last_activity_at on session updates
CREATE TRIGGER update_sessions_activity BEFORE UPDATE ON sessions
  FOR EACH ROW EXECUTE FUNCTION update_session_activity();

-- Function to cleanup expired sessions
CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
RETURNS INTEGER AS $$
DECLARE
  deleted_count INTEGER;
BEGIN
  -- Mark expired sessions as inactive
  UPDATE sessions
  SET is_active = false
  WHERE is_active = true
    AND expires_at < NOW();
  
  GET DIAGNOSTICS deleted_count = ROW_COUNT;
  
  -- Delete sessions that have been inactive for more than 30 days
  DELETE FROM sessions
  WHERE is_active = false
    AND expires_at < NOW() - INTERVAL '30 days';
  
  RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to enforce concurrent session limits
CREATE OR REPLACE FUNCTION enforce_session_limit()
RETURNS TRIGGER AS $$
DECLARE
  session_count INTEGER;
  max_sessions INTEGER := 5;
  oldest_session_id UUID;
BEGIN
  -- Count active sessions for this user
  SELECT COUNT(*) INTO session_count
  FROM sessions
  WHERE user_id = NEW.user_id
    AND is_active = true;
  
  -- If limit exceeded, deactivate oldest session
  IF session_count >= max_sessions THEN
    SELECT id INTO oldest_session_id
    FROM sessions
    WHERE user_id = NEW.user_id
      AND is_active = true
    ORDER BY last_activity_at ASC
    LIMIT 1;
    
    UPDATE sessions
    SET is_active = false
    WHERE id = oldest_session_id;
  END IF;
  
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to enforce session limits on new session creation
CREATE TRIGGER enforce_sessions_limit BEFORE INSERT ON sessions
  FOR EACH ROW EXECUTE FUNCTION enforce_session_limit();

-- ============================================================================
-- AUDIT LOGGING
-- ============================================================================

-- Audit trigger for session events
CREATE TRIGGER audit_sessions AFTER INSERT OR UPDATE OR DELETE ON sessions
  FOR EACH ROW EXECUTE FUNCTION log_audit_event();

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE sessions IS 'User session management with JWT token tracking and activity monitoring';
COMMENT ON COLUMN sessions.token_hash IS 'SHA-256 hash of JWT token for validation';
COMMENT ON COLUMN sessions.ip_address IS 'Client IP address for security tracking';
COMMENT ON COLUMN sessions.user_agent IS 'Client user agent string';
COMMENT ON COLUMN sessions.last_activity_at IS 'Last activity timestamp for idle timeout';
COMMENT ON COLUMN sessions.expires_at IS 'Absolute expiration time (24 hours from creation)';
COMMENT ON COLUMN sessions.is_active IS 'Whether session is currently active';
COMMENT ON COLUMN sessions.metadata IS 'Additional session metadata (last endpoint, etc.)';

-- ============================================================================
-- SCHEMA VERSION UPDATE
-- ============================================================================

INSERT INTO schema_version (version, description)
VALUES ('1.1.0', 'Added sessions table for session management with activity tracking and concurrent session limits')
ON CONFLICT (version) DO NOTHING;
