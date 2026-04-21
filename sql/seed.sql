-- Unified Trading Intelligence Platform - Seed Data
-- This file populates the database with test data for local development

-- Insert test users
-- Password: "password123" (hashed with bcrypt)
INSERT INTO users (id, email, password_hash, max_strategies, max_trades_per_day, max_api_calls_per_hour)
VALUES 
  ('11111111-1111-1111-1111-111111111111', 'test@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqVr/VXlTW', 10, 100, 1000),
  ('22222222-2222-2222-2222-222222222222', 'trader@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqVr/VXlTW', 20, 200, 2000),
  ('33333333-3333-3333-3333-333333333333', 'admin@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqVr/VXlTW', 50, 500, 5000)
ON CONFLICT (email) DO NOTHING;

-- Insert test strategies
INSERT INTO strategies (id, user_id, name, type, config, is_active)
VALUES 
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '11111111-1111-1111-1111-111111111111', 'Simple Moving Average', 'technical', 
   '{"indicators": ["SMA_20", "SMA_50"], "timeframe": "1h", "threshold": 0.02}'::jsonb, true),
  ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', '11111111-1111-1111-1111-111111111111', 'RSI Momentum', 'technical',
   '{"indicators": ["RSI_14"], "timeframe": "15m", "overbought": 70, "oversold": 30}'::jsonb, false),
  ('cccccccc-cccc-cccc-cccc-cccccccccccc', '22222222-2222-2222-2222-222222222222', 'News Sentiment', 'news',
   '{"sources": ["twitter", "rss"], "confidence_threshold": 0.7}'::jsonb, true)
ON CONFLICT DO NOTHING;

-- Insert test trades
INSERT INTO trades (user_id, strategy_id, exchange, symbol, side, type, price, size, fee, pnl, timestamp)
VALUES 
  ('11111111-1111-1111-1111-111111111111', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'alpaca', 'AAPL', 'buy', 'market', 150.25, 10, 0.15, NULL, NOW() - INTERVAL '2 days'),
  ('11111111-1111-1111-1111-111111111111', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'alpaca', 'AAPL', 'sell', 'market', 152.50, 10, 0.15, 22.35, NOW() - INTERVAL '1 day'),
  ('22222222-2222-2222-2222-222222222222', 'cccccccc-cccc-cccc-cccc-cccccccccccc', 'polymarket', 'TRUMP_2024', 'buy', 'limit', 0.65, 100, 0.50, NULL, NOW() - INTERVAL '3 hours'),
  ('11111111-1111-1111-1111-111111111111', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'kalshi', 'FED_RATE_CUT', 'buy', 'market', 0.45, 50, 0.25, -5.25, NOW() - INTERVAL '1 hour')
ON CONFLICT DO NOTHING;

-- Insert test positions
INSERT INTO positions (user_id, exchange, symbol, size, avg_price, current_price, unrealized_pnl, realized_pnl)
VALUES 
  ('11111111-1111-1111-1111-111111111111', 'alpaca', 'TSLA', 5, 245.50, 250.00, 22.50, 0),
  ('22222222-2222-2222-2222-222222222222', 'polymarket', 'TRUMP_2024', 100, 0.65, 0.68, 3.00, 0),
  ('22222222-2222-2222-2222-222222222222', 'kalshi', 'FED_RATE_CUT', 50, 0.45, 0.42, -1.50, 0)
ON CONFLICT (user_id, exchange, symbol) DO NOTHING;

-- Insert test signals
INSERT INTO signals (user_id, source, asset, direction, confidence, rationale, indicators, timestamp)
VALUES 
  ('11111111-1111-1111-1111-111111111111', 'technical_analysis', 'BTC', 'long', 0.85, 'RSI oversold, MACD bullish crossover', 
   '{"RSI": 28, "MACD": {"value": 0.5, "signal": 0.3}}'::jsonb, NOW() - INTERVAL '30 minutes'),
  ('22222222-2222-2222-2222-222222222222', 'news_classifier', 'AAPL', 'long', 0.72, 'Positive earnings report, strong guidance',
   '{"sentiment": "positive", "confidence": 0.72}'::jsonb, NOW() - INTERVAL '1 hour'),
  ('11111111-1111-1111-1111-111111111111', 'multi_agent_sim', 'ETH', 'short', 0.65, 'Consensus: 7/10 agents bearish',
   '{"consensus": 0.7, "agents_bearish": 7, "agents_bullish": 3}'::jsonb, NOW() - INTERVAL '15 minutes')
ON CONFLICT DO NOTHING;

-- Insert test audit log entries
INSERT INTO audit_log (user_id, action, details, ip_address, timestamp)
VALUES 
  ('11111111-1111-1111-1111-111111111111', 'login', '{"method": "email"}'::jsonb, '192.168.1.100', NOW() - INTERVAL '4 hours'),
  ('11111111-1111-1111-1111-111111111111', 'strategy_created', '{"strategy_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "name": "Simple Moving Average"}'::jsonb, '192.168.1.100', NOW() - INTERVAL '3 hours'),
  ('22222222-2222-2222-2222-222222222222', 'login', '{"method": "oauth", "provider": "google"}'::jsonb, '192.168.1.101', NOW() - INTERVAL '2 hours'),
  ('11111111-1111-1111-1111-111111111111', 'trade_executed', '{"trade_id": "some-uuid", "symbol": "AAPL", "side": "buy"}'::jsonb, '192.168.1.100', NOW() - INTERVAL '1 hour')
ON CONFLICT DO NOTHING;

-- Display summary
DO $$
BEGIN
  RAISE NOTICE 'Seed data inserted successfully!';
  RAISE NOTICE 'Test users: test@example.com, trader@example.com, admin@example.com';
  RAISE NOTICE 'Password for all test users: password123';
END $$;
