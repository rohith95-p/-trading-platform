-- Unified Trading Intelligence Platform - Database Schema
-- This schema should be executed in Supabase PostgreSQL

-- Users table
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  max_strategies INT DEFAULT 10,
  max_trades_per_day INT DEFAULT 100,
  max_api_calls_per_hour INT DEFAULT 1000
);

-- API keys table (encrypted)
CREATE TABLE api_keys (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  exchange TEXT NOT NULL,
  key_encrypted TEXT NOT NULL,
  secret_encrypted TEXT NOT NULL,
  is_valid BOOLEAN DEFAULT true,
  last_validated_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Strategies table
CREATE TABLE strategies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  type TEXT NOT NULL,
  config JSONB NOT NULL,
  is_active BOOLEAN DEFAULT false,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Trades table
CREATE TABLE trades (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  strategy_id UUID REFERENCES strategies(id) ON DELETE SET NULL,
  exchange TEXT NOT NULL,
  symbol TEXT NOT NULL,
  side TEXT NOT NULL,
  type TEXT NOT NULL,
  price DECIMAL(20, 8) NOT NULL,
  size DECIMAL(20, 8) NOT NULL,
  fee DECIMAL(20, 8) DEFAULT 0,
  pnl DECIMAL(20, 8),
  timestamp TIMESTAMP DEFAULT NOW()
);

-- Positions table
CREATE TABLE positions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  exchange TEXT NOT NULL,
  symbol TEXT NOT NULL,
  size DECIMAL(20, 8) NOT NULL,
  avg_price DECIMAL(20, 8) NOT NULL,
  current_price DECIMAL(20, 8),
  unrealized_pnl DECIMAL(20, 8),
  realized_pnl DECIMAL(20, 8) DEFAULT 0,
  updated_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(user_id, exchange, symbol)
);

-- Signals table
CREATE TABLE signals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  source TEXT NOT NULL,
  asset TEXT NOT NULL,
  direction TEXT NOT NULL,
  confidence DECIMAL(3, 2) NOT NULL,
  rationale TEXT,
  indicators JSONB,
  timestamp TIMESTAMP DEFAULT NOW()
);

-- Audit log table
CREATE TABLE audit_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  action TEXT NOT NULL,
  details JSONB,
  ip_address INET,
  timestamp TIMESTAMP DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_trades_user_id ON trades(user_id);
CREATE INDEX idx_trades_symbol ON trades(symbol);
CREATE INDEX idx_trades_timestamp ON trades(timestamp);
CREATE INDEX idx_positions_user_id ON positions(user_id);
CREATE INDEX idx_signals_user_id ON signals(user_id);
CREATE INDEX idx_signals_timestamp ON signals(timestamp);
CREATE INDEX idx_audit_user_id ON audit_log(user_id);
CREATE INDEX idx_audit_timestamp ON audit_log(timestamp);

-- Enable Row Level Security
ALTER TABLE strategies ENABLE ROW LEVEL SECURITY;
ALTER TABLE trades ENABLE ROW LEVEL SECURITY;
ALTER TABLE positions ENABLE ROW LEVEL SECURITY;
ALTER TABLE signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;

-- Create RLS policies
CREATE POLICY "Users can view own strategies" ON strategies
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can view own trades" ON trades
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can view own positions" ON positions
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can view own signals" ON signals
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can view own api_keys" ON api_keys
  FOR SELECT USING (auth.uid() = user_id);
