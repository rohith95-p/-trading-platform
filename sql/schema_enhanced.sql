-- Unified Trading Intelligence Platform - Enhanced Database Schema
-- Version: 1.0.0
-- This schema includes all enhancements for Task 1.6

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- USERS TABLE
-- ============================================================================
-- Enhanced users table with comprehensive quota limits and metadata
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  email_verified BOOLEAN DEFAULT false,
  email_verified_at TIMESTAMP,
  
  -- Profile information
  full_name TEXT,
  avatar_url TEXT,
  timezone TEXT DEFAULT 'UTC',
  
  -- Quota limits
  max_strategies INT DEFAULT 10,
  max_trades_per_day INT DEFAULT 100,
  max_api_calls_per_hour INT DEFAULT 1000,
  max_positions INT DEFAULT 20,
  max_api_keys INT DEFAULT 5,
  
  -- Account status
  is_active BOOLEAN DEFAULT true,
  is_premium BOOLEAN DEFAULT false,
  subscription_tier TEXT DEFAULT 'free' CHECK (subscription_tier IN ('free', 'basic', 'premium', 'enterprise')),
  subscription_expires_at TIMESTAMP,
  
  -- Timestamps
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  last_login_at TIMESTAMP,
  
  -- Metadata
  metadata JSONB DEFAULT '{}'::jsonb,
  
  -- Constraints
  CONSTRAINT email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
);

-- ============================================================================
-- API KEYS TABLE
-- ============================================================================
-- Enhanced API keys table with encryption fields and validation
CREATE TABLE IF NOT EXISTS api_keys (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  
  -- Exchange information
  exchange TEXT NOT NULL CHECK (exchange IN ('alpaca', 'kalshi', 'polymarket', 'hyperliquid', 'dydx', 'kraken', 'binance')),
  exchange_account_id TEXT,
  
  -- Encrypted credentials
  key_encrypted TEXT NOT NULL,
  secret_encrypted TEXT NOT NULL,
  passphrase_encrypted TEXT, -- For exchanges that require passphrase
  
  -- Validation
  is_valid BOOLEAN DEFAULT true,
  last_validated_at TIMESTAMP,
  validation_error TEXT,
  
  -- Permissions
  permissions JSONB DEFAULT '{"read": true, "trade": false, "withdraw": false}'::jsonb,
  
  -- Usage tracking
  last_used_at TIMESTAMP,
  usage_count INT DEFAULT 0,
  
  -- Timestamps
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  expires_at TIMESTAMP,
  
  -- Metadata
  metadata JSONB DEFAULT '{}'::jsonb,
  
  -- Constraints
  UNIQUE(user_id, exchange, exchange_account_id)
);

-- ============================================================================
-- STRATEGIES TABLE
-- ============================================================================
-- Enhanced strategies table with comprehensive configuration
CREATE TABLE IF NOT EXISTS strategies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  
  -- Strategy information
  name TEXT NOT NULL,
  description TEXT,
  type TEXT NOT NULL CHECK (type IN ('technical', 'news', 'drl', 'multi_agent', 'custom')),
  
  -- Configuration
  config JSONB NOT NULL,
  
  -- Status
  is_active BOOLEAN DEFAULT false,
  is_public BOOLEAN DEFAULT false,
  
  -- Performance metrics
  total_trades INT DEFAULT 0,
  winning_trades INT DEFAULT 0,
  losing_trades INT DEFAULT 0,
  total_pnl DECIMAL(20, 8) DEFAULT 0,
  sharpe_ratio DECIMAL(10, 4),
  max_drawdown DECIMAL(10, 4),
  
  -- Risk parameters
  max_position_size DECIMAL(20, 8),
  max_daily_loss DECIMAL(20, 8),
  stop_loss_pct DECIMAL(5, 2),
  take_profit_pct DECIMAL(5, 2),
  
  -- Timestamps
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  last_executed_at TIMESTAMP,
  
  -- Metadata
  metadata JSONB DEFAULT '{}'::jsonb,
  tags TEXT[] DEFAULT ARRAY[]::TEXT[],
  
  -- Constraints
  CONSTRAINT strategy_name_length CHECK (char_length(name) >= 3 AND char_length(name) <= 100)
);

-- ============================================================================
-- TRADES TABLE
-- ============================================================================
-- Enhanced trades table with comprehensive fields
CREATE TABLE IF NOT EXISTS trades (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  strategy_id UUID REFERENCES strategies(id) ON DELETE SET NULL,
  
  -- Exchange information
  exchange TEXT NOT NULL,
  exchange_order_id TEXT,
  symbol TEXT NOT NULL,
  
  -- Trade details
  side TEXT NOT NULL CHECK (side IN ('buy', 'sell', 'long', 'short')),
  type TEXT NOT NULL CHECK (type IN ('market', 'limit', 'stop', 'stop_limit')),
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'filled', 'partial', 'cancelled', 'rejected', 'expired')),
  
  -- Pricing
  price DECIMAL(20, 8) NOT NULL,
  size DECIMAL(20, 8) NOT NULL,
  filled_size DECIMAL(20, 8) DEFAULT 0,
  average_fill_price DECIMAL(20, 8),
  
  -- Costs
  fee DECIMAL(20, 8) DEFAULT 0,
  fee_currency TEXT DEFAULT 'USD',
  slippage DECIMAL(20, 8),
  
  -- P&L
  pnl DECIMAL(20, 8),
  pnl_pct DECIMAL(10, 4),
  
  -- Risk management
  stop_loss DECIMAL(20, 8),
  take_profit DECIMAL(20, 8),
  
  -- Timestamps
  timestamp TIMESTAMP DEFAULT NOW(),
  filled_at TIMESTAMP,
  cancelled_at TIMESTAMP,
  
  -- Metadata
  metadata JSONB DEFAULT '{}'::jsonb,
  notes TEXT,
  
  -- Constraints
  CONSTRAINT positive_size CHECK (size > 0),
  CONSTRAINT positive_price CHECK (price > 0)
);

-- ============================================================================
-- POSITIONS TABLE
-- ============================================================================
-- Enhanced positions table with unique constraints and tracking
CREATE TABLE IF NOT EXISTS positions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  strategy_id UUID REFERENCES strategies(id) ON DELETE SET NULL,
  
  -- Position information
  exchange TEXT NOT NULL,
  symbol TEXT NOT NULL,
  side TEXT NOT NULL CHECK (side IN ('long', 'short')),
  
  -- Size and pricing
  size DECIMAL(20, 8) NOT NULL,
  avg_entry_price DECIMAL(20, 8) NOT NULL,
  current_price DECIMAL(20, 8),
  
  -- P&L
  unrealized_pnl DECIMAL(20, 8),
  unrealized_pnl_pct DECIMAL(10, 4),
  realized_pnl DECIMAL(20, 8) DEFAULT 0,
  realized_pnl_pct DECIMAL(10, 4),
  
  -- Risk management
  stop_loss DECIMAL(20, 8),
  take_profit DECIMAL(20, 8),
  liquidation_price DECIMAL(20, 8),
  
  -- Leverage
  leverage DECIMAL(5, 2) DEFAULT 1.0,
  margin_used DECIMAL(20, 8),
  
  -- Status
  is_open BOOLEAN DEFAULT true,
  
  -- Timestamps
  opened_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  closed_at TIMESTAMP,
  
  -- Metadata
  metadata JSONB DEFAULT '{}'::jsonb,
  
  -- Constraints
  UNIQUE(user_id, exchange, symbol, is_open),
  CONSTRAINT positive_size_pos CHECK (size > 0),
  CONSTRAINT valid_leverage CHECK (leverage >= 1.0 AND leverage <= 125.0)
);

-- ============================================================================
-- SIGNALS TABLE
-- ============================================================================
-- Enhanced signals table with source tracking
CREATE TABLE IF NOT EXISTS signals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  strategy_id UUID REFERENCES strategies(id) ON DELETE SET NULL,
  
  -- Signal information
  source TEXT NOT NULL CHECK (source IN ('technical_analysis', 'news_classifier', 'multi_agent_sim', 'drl_agent', 'custom')),
  asset TEXT NOT NULL,
  exchange TEXT,
  
  -- Signal details
  direction TEXT NOT NULL CHECK (direction IN ('long', 'short', 'neutral', 'close')),
  confidence DECIMAL(3, 2) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
  strength TEXT CHECK (strength IN ('weak', 'moderate', 'strong')),
  
  -- Reasoning
  rationale TEXT,
  indicators JSONB,
  
  -- Execution
  is_executed BOOLEAN DEFAULT false,
  executed_at TIMESTAMP,
  trade_id UUID REFERENCES trades(id) ON DELETE SET NULL,
  
  -- Expiration
  expires_at TIMESTAMP,
  is_expired BOOLEAN DEFAULT false,
  
  -- Timestamps
  timestamp TIMESTAMP DEFAULT NOW(),
  
  -- Metadata
  metadata JSONB DEFAULT '{}'::jsonb,
  
  -- Constraints
  CONSTRAINT valid_confidence CHECK (confidence >= 0 AND confidence <= 1)
);

-- ============================================================================
-- AUDIT LOG TABLE
-- ============================================================================
-- Enhanced audit log table for compliance
CREATE TABLE IF NOT EXISTS audit_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  
  -- Action information
  action TEXT NOT NULL,
  resource_type TEXT,
  resource_id UUID,
  
  -- Details
  details JSONB,
  
  -- Request information
  ip_address INET,
  user_agent TEXT,
  request_id UUID,
  
  -- Status
  status TEXT DEFAULT 'success' CHECK (status IN ('success', 'failure', 'error')),
  error_message TEXT,
  
  -- Timestamps
  timestamp TIMESTAMP DEFAULT NOW(),
  
  -- Metadata
  metadata JSONB DEFAULT '{}'::jsonb
);

-- ============================================================================
-- ADDITIONAL TABLES
-- ============================================================================

-- Notifications table
CREATE TABLE IF NOT EXISTS notifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  
  -- Notification details
  type TEXT NOT NULL CHECK (type IN ('trade', 'signal', 'alert', 'system', 'security')),
  title TEXT NOT NULL,
  message TEXT NOT NULL,
  
  -- Status
  is_read BOOLEAN DEFAULT false,
  read_at TIMESTAMP,
  
  -- Priority
  priority TEXT DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
  
  -- Related resources
  related_resource_type TEXT,
  related_resource_id UUID,
  
  -- Timestamps
  created_at TIMESTAMP DEFAULT NOW(),
  expires_at TIMESTAMP,
  
  -- Metadata
  metadata JSONB DEFAULT '{}'::jsonb
);

-- Alerts table
CREATE TABLE IF NOT EXISTS alerts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  
  -- Alert configuration
  name TEXT NOT NULL,
  type TEXT NOT NULL CHECK (type IN ('price', 'indicator', 'pnl', 'position', 'custom')),
  condition JSONB NOT NULL,
  
  -- Status
  is_active BOOLEAN DEFAULT true,
  is_triggered BOOLEAN DEFAULT false,
  last_triggered_at TIMESTAMP,
  trigger_count INT DEFAULT 0,
  
  -- Notification settings
  notify_email BOOLEAN DEFAULT false,
  notify_slack BOOLEAN DEFAULT false,
  notify_webhook BOOLEAN DEFAULT false,
  webhook_url TEXT,
  
  -- Timestamps
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  
  -- Metadata
  metadata JSONB DEFAULT '{}'::jsonb
);

-- ============================================================================
-- INDEXES
-- ============================================================================

-- Users indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_subscription_tier ON users(subscription_tier);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);

-- API keys indexes
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_exchange ON api_keys(exchange);
CREATE INDEX IF NOT EXISTS idx_api_keys_is_valid ON api_keys(is_valid);

-- Strategies indexes
CREATE INDEX IF NOT EXISTS idx_strategies_user_id ON strategies(user_id);
CREATE INDEX IF NOT EXISTS idx_strategies_type ON strategies(type);
CREATE INDEX IF NOT EXISTS idx_strategies_is_active ON strategies(is_active);
CREATE INDEX IF NOT EXISTS idx_strategies_is_public ON strategies(is_public);
CREATE INDEX IF NOT EXISTS idx_strategies_created_at ON strategies(created_at);

-- Trades indexes
CREATE INDEX IF NOT EXISTS idx_trades_user_id ON trades(user_id);
CREATE INDEX IF NOT EXISTS idx_trades_strategy_id ON trades(strategy_id);
CREATE INDEX IF NOT EXISTS idx_trades_exchange ON trades(exchange);
CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);
CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status);
CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp);
CREATE INDEX IF NOT EXISTS idx_trades_user_symbol ON trades(user_id, symbol);
CREATE INDEX IF NOT EXISTS idx_trades_user_timestamp ON trades(user_id, timestamp DESC);

-- Positions indexes
CREATE INDEX IF NOT EXISTS idx_positions_user_id ON positions(user_id);
CREATE INDEX IF NOT EXISTS idx_positions_strategy_id ON positions(strategy_id);
CREATE INDEX IF NOT EXISTS idx_positions_exchange ON positions(exchange);
CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol);
CREATE INDEX IF NOT EXISTS idx_positions_is_open ON positions(is_open);
CREATE INDEX IF NOT EXISTS idx_positions_user_open ON positions(user_id, is_open);

-- Signals indexes
CREATE INDEX IF NOT EXISTS idx_signals_user_id ON signals(user_id);
CREATE INDEX IF NOT EXISTS idx_signals_strategy_id ON signals(strategy_id);
CREATE INDEX IF NOT EXISTS idx_signals_source ON signals(source);
CREATE INDEX IF NOT EXISTS idx_signals_asset ON signals(asset);
CREATE INDEX IF NOT EXISTS idx_signals_is_executed ON signals(is_executed);
CREATE INDEX IF NOT EXISTS idx_signals_timestamp ON signals(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_signals_user_timestamp ON signals(user_id, timestamp DESC);

-- Audit log indexes
CREATE INDEX IF NOT EXISTS idx_audit_user_id ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_user_timestamp ON audit_log(user_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_resource ON audit_log(resource_type, resource_id);

-- Notifications indexes
CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_is_read ON notifications(is_read);
CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON notifications(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notifications_user_unread ON notifications(user_id, is_read) WHERE is_read = false;

-- Alerts indexes
CREATE INDEX IF NOT EXISTS idx_alerts_user_id ON alerts(user_id);
CREATE INDEX IF NOT EXISTS idx_alerts_is_active ON alerts(is_active);
CREATE INDEX IF NOT EXISTS idx_alerts_type ON alerts(type);

-- ============================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================================================

-- Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE strategies ENABLE ROW LEVEL SECURITY;
ALTER TABLE trades ENABLE ROW LEVEL SECURITY;
ALTER TABLE positions ENABLE ROW LEVEL SECURITY;
ALTER TABLE signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE alerts ENABLE ROW LEVEL SECURITY;

-- Users policies
CREATE POLICY "Users can view own profile" ON users
  FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" ON users
  FOR UPDATE USING (auth.uid() = id);

-- API keys policies
CREATE POLICY "Users can view own api_keys" ON api_keys
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own api_keys" ON api_keys
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own api_keys" ON api_keys
  FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own api_keys" ON api_keys
  FOR DELETE USING (auth.uid() = user_id);

-- Strategies policies
CREATE POLICY "Users can view own strategies" ON strategies
  FOR SELECT USING (auth.uid() = user_id OR is_public = true);

CREATE POLICY "Users can insert own strategies" ON strategies
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own strategies" ON strategies
  FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own strategies" ON strategies
  FOR DELETE USING (auth.uid() = user_id);

-- Trades policies
CREATE POLICY "Users can view own trades" ON trades
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own trades" ON trades
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own trades" ON trades
  FOR UPDATE USING (auth.uid() = user_id);

-- Positions policies
CREATE POLICY "Users can view own positions" ON positions
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own positions" ON positions
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own positions" ON positions
  FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own positions" ON positions
  FOR DELETE USING (auth.uid() = user_id);

-- Signals policies
CREATE POLICY "Users can view own signals" ON signals
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own signals" ON signals
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own signals" ON signals
  FOR UPDATE USING (auth.uid() = user_id);

-- Audit log policies (read-only for users)
CREATE POLICY "Users can view own audit logs" ON audit_log
  FOR SELECT USING (auth.uid() = user_id);

-- Notifications policies
CREATE POLICY "Users can view own notifications" ON notifications
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can update own notifications" ON notifications
  FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own notifications" ON notifications
  FOR DELETE USING (auth.uid() = user_id);

-- Alerts policies
CREATE POLICY "Users can view own alerts" ON alerts
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own alerts" ON alerts
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own alerts" ON alerts
  FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own alerts" ON alerts
  FOR DELETE USING (auth.uid() = user_id);

-- ============================================================================
-- FUNCTIONS AND TRIGGERS
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_api_keys_updated_at BEFORE UPDATE ON api_keys
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_strategies_updated_at BEFORE UPDATE ON strategies
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_positions_updated_at BEFORE UPDATE ON positions
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_alerts_updated_at BEFORE UPDATE ON alerts
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to log audit events
CREATE OR REPLACE FUNCTION log_audit_event()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO audit_log (user_id, action, resource_type, resource_id, details)
  VALUES (
    auth.uid(),
    TG_OP,
    TG_TABLE_NAME,
    COALESCE(NEW.id, OLD.id),
    jsonb_build_object(
      'old', to_jsonb(OLD),
      'new', to_jsonb(NEW)
    )
  );
  RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Audit triggers for sensitive tables
CREATE TRIGGER audit_api_keys AFTER INSERT OR UPDATE OR DELETE ON api_keys
  FOR EACH ROW EXECUTE FUNCTION log_audit_event();

CREATE TRIGGER audit_strategies AFTER INSERT OR UPDATE OR DELETE ON strategies
  FOR EACH ROW EXECUTE FUNCTION log_audit_event();

-- ============================================================================
-- VIEWS
-- ============================================================================

-- View for user statistics
CREATE OR REPLACE VIEW user_statistics AS
SELECT 
  u.id AS user_id,
  u.email,
  COUNT(DISTINCT s.id) AS total_strategies,
  COUNT(DISTINCT t.id) AS total_trades,
  COUNT(DISTINCT p.id) AS total_positions,
  COUNT(DISTINCT sig.id) AS total_signals,
  COALESCE(SUM(t.pnl), 0) AS total_pnl,
  COUNT(DISTINCT CASE WHEN t.pnl > 0 THEN t.id END) AS winning_trades,
  COUNT(DISTINCT CASE WHEN t.pnl < 0 THEN t.id END) AS losing_trades
FROM users u
LEFT JOIN strategies s ON u.id = s.user_id
LEFT JOIN trades t ON u.id = t.user_id
LEFT JOIN positions p ON u.id = p.user_id
LEFT JOIN signals sig ON u.id = sig.user_id
GROUP BY u.id, u.email;

-- View for active positions summary
CREATE OR REPLACE VIEW active_positions_summary AS
SELECT 
  user_id,
  exchange,
  symbol,
  side,
  size,
  avg_entry_price,
  current_price,
  unrealized_pnl,
  unrealized_pnl_pct,
  leverage,
  opened_at,
  updated_at
FROM positions
WHERE is_open = true
ORDER BY updated_at DESC;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE users IS 'User accounts with quota limits and subscription information';
COMMENT ON TABLE api_keys IS 'Encrypted API keys for exchange connections';
COMMENT ON TABLE strategies IS 'Trading strategies with configuration and performance metrics';
COMMENT ON TABLE trades IS 'Trade execution records with comprehensive details';
COMMENT ON TABLE positions IS 'Open and closed positions with P&L tracking';
COMMENT ON TABLE signals IS 'Trading signals from various sources';
COMMENT ON TABLE audit_log IS 'Audit trail for compliance and security';
COMMENT ON TABLE notifications IS 'User notifications for important events';
COMMENT ON TABLE alerts IS 'User-configured alerts for price and indicator conditions';

-- ============================================================================
-- GRANTS
-- ============================================================================

-- Grant appropriate permissions (adjust based on your setup)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO authenticated;
-- GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO authenticated;

-- ============================================================================
-- SCHEMA VERSION
-- ============================================================================

CREATE TABLE IF NOT EXISTS schema_version (
  version TEXT PRIMARY KEY,
  applied_at TIMESTAMP DEFAULT NOW(),
  description TEXT
);

INSERT INTO schema_version (version, description)
VALUES ('1.0.0', 'Initial enhanced schema with comprehensive tables, indexes, and RLS policies')
ON CONFLICT (version) DO NOTHING;
