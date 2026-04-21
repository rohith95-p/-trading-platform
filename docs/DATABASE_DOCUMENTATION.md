# Database Documentation

Comprehensive documentation for the Unified Trading Intelligence Platform database schema.

## Table of Contents

1. [Overview](#overview)
2. [Database Schema](#database-schema)
3. [Tables](#tables)
4. [Indexes](#indexes)
5. [Row Level Security](#row-level-security)
6. [Functions and Triggers](#functions-and-triggers)
7. [Views](#views)
8. [Data Types](#data-types)
9. [Relationships](#relationships)
10. [Query Examples](#query-examples)

---

## Overview

### Database Information

- **Database**: PostgreSQL 15+
- **Provider**: Supabase
- **Schema Version**: 1.0.0
- **Character Set**: UTF-8
- **Timezone**: UTC

### Key Features

- UUID primary keys for all tables
- JSONB for flexible configuration storage
- Row Level Security (RLS) for multi-tenant isolation
- Comprehensive indexing for performance
- Audit logging for compliance
- Automatic timestamp management

---

## Database Schema

### Entity Relationship Diagram

```
┌─────────────┐
│    users    │
└──────┬──────┘
       │
       ├──────────────────────────────────────┐
       │                                      │
       ▼                                      ▼
┌─────────────┐                        ┌─────────────┐
│  api_keys   │                        │ strategies  │
└─────────────┘                        └──────┬──────┘
                                              │
                                              ├──────────┐
                                              │          │
                                              ▼          ▼
                                        ┌─────────┐ ┌──────────┐
                                        │ trades  │ │positions │
                                        └─────────┘ └──────────┘
                                              │
                                              ▼
                                        ┌─────────┐
                                        │ signals │
                                        └─────────┘
```

---

## Tables

### 1. users

User accounts with quota limits and subscription information.

**Columns**:

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | UUID | NO | gen_random_uuid() | Primary key |
| email | TEXT | NO | - | User email (unique) |
| password_hash | TEXT | NO | - | Hashed password |
| email_verified | BOOLEAN | YES | false | Email verification status |
| email_verified_at | TIMESTAMP | YES | - | Email verification timestamp |
| full_name | TEXT | YES | - | User's full name |
| avatar_url | TEXT | YES | - | Profile picture URL |
| timezone | TEXT | YES | 'UTC' | User's timezone |
| max_strategies | INT | YES | 10 | Maximum strategies allowed |
| max_trades_per_day | INT | YES | 100 | Daily trade limit |
| max_api_calls_per_hour | INT | YES | 1000 | Hourly API call limit |
| max_positions | INT | YES | 20 | Maximum open positions |
| max_api_keys | INT | YES | 5 | Maximum API keys |
| is_active | BOOLEAN | YES | true | Account active status |
| is_premium | BOOLEAN | YES | false | Premium account flag |
| subscription_tier | TEXT | YES | 'free' | Subscription level |
| subscription_expires_at | TIMESTAMP | YES | - | Subscription expiration |
| created_at | TIMESTAMP | YES | NOW() | Account creation time |
| updated_at | TIMESTAMP | YES | NOW() | Last update time |
| last_login_at | TIMESTAMP | YES | - | Last login time |
| metadata | JSONB | YES | '{}' | Additional metadata |

**Constraints**:
- `email_format`: Email must match valid format
- `subscription_tier`: Must be one of ('free', 'basic', 'premium', 'enterprise')

**Indexes**:
- `idx_users_email` on (email)
- `idx_users_subscription_tier` on (subscription_tier)
- `idx_users_is_active` on (is_active)
- `idx_users_created_at` on (created_at)

---

### 2. api_keys

Encrypted API keys for exchange connections.

**Columns**:

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | UUID | NO | gen_random_uuid() | Primary key |
| user_id | UUID | NO | - | Foreign key to users |
| exchange | TEXT | NO | - | Exchange name |
| exchange_account_id | TEXT | YES | - | Exchange account identifier |
| key_encrypted | TEXT | NO | - | Encrypted API key |
| secret_encrypted | TEXT | NO | - | Encrypted API secret |
| passphrase_encrypted | TEXT | YES | - | Encrypted passphrase (if required) |
| is_valid | BOOLEAN | YES | true | Validation status |
| last_validated_at | TIMESTAMP | YES | - | Last validation time |
| validation_error | TEXT | YES | - | Validation error message |
| permissions | JSONB | YES | '{"read": true, "trade": false, "withdraw": false}' | API key permissions |
| last_used_at | TIMESTAMP | YES | - | Last usage time |
| usage_count | INT | YES | 0 | Usage counter |
| created_at | TIMESTAMP | YES | NOW() | Creation time |
| updated_at | TIMESTAMP | YES | NOW() | Last update time |
| expires_at | TIMESTAMP | YES | - | Expiration time |
| metadata | JSONB | YES | '{}' | Additional metadata |

**Constraints**:
- `exchange`: Must be one of ('alpaca', 'kalshi', 'polymarket', 'hyperliquid', 'dydx', 'kraken', 'binance')
- `UNIQUE(user_id, exchange, exchange_account_id)`

**Indexes**:
- `idx_api_keys_user_id` on (user_id)
- `idx_api_keys_exchange` on (exchange)
- `idx_api_keys_is_valid` on (is_valid)

---

### 3. strategies

Trading strategies with configuration and performance metrics.

**Columns**:

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | UUID | NO | gen_random_uuid() | Primary key |
| user_id | UUID | NO | - | Foreign key to users |
| name | TEXT | NO | - | Strategy name |
| description | TEXT | YES | - | Strategy description |
| type | TEXT | NO | - | Strategy type |
| config | JSONB | NO | - | Strategy configuration |
| is_active | BOOLEAN | YES | false | Active status |
| is_public | BOOLEAN | YES | false | Public visibility |
| total_trades | INT | YES | 0 | Total trades executed |
| winning_trades | INT | YES | 0 | Number of winning trades |
| losing_trades | INT | YES | 0 | Number of losing trades |
| total_pnl | DECIMAL(20,8) | YES | 0 | Total profit/loss |
| sharpe_ratio | DECIMAL(10,4) | YES | - | Sharpe ratio |
| max_drawdown | DECIMAL(10,4) | YES | - | Maximum drawdown |
| max_position_size | DECIMAL(20,8) | YES | - | Maximum position size |
| max_daily_loss | DECIMAL(20,8) | YES | - | Maximum daily loss limit |
| stop_loss_pct | DECIMAL(5,2) | YES | - | Stop loss percentage |
| take_profit_pct | DECIMAL(5,2) | YES | - | Take profit percentage |
| created_at | TIMESTAMP | YES | NOW() | Creation time |
| updated_at | TIMESTAMP | YES | NOW() | Last update time |
| last_executed_at | TIMESTAMP | YES | - | Last execution time |
| metadata | JSONB | YES | '{}' | Additional metadata |
| tags | TEXT[] | YES | ARRAY[]::TEXT[] | Strategy tags |

**Constraints**:
- `type`: Must be one of ('technical', 'news', 'drl', 'multi_agent', 'custom')
- `strategy_name_length`: Name length between 3 and 100 characters

**Indexes**:
- `idx_strategies_user_id` on (user_id)
- `idx_strategies_type` on (type)
- `idx_strategies_is_active` on (is_active)
- `idx_strategies_is_public` on (is_public)
- `idx_strategies_created_at` on (created_at)

---

### 4. trades

Trade execution records with comprehensive details.

**Columns**:

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | UUID | NO | gen_random_uuid() | Primary key |
| user_id | UUID | NO | - | Foreign key to users |
| strategy_id | UUID | YES | - | Foreign key to strategies |
| exchange | TEXT | NO | - | Exchange name |
| exchange_order_id | TEXT | YES | - | Exchange order ID |
| symbol | TEXT | NO | - | Trading symbol |
| side | TEXT | NO | - | Trade side |
| type | TEXT | NO | - | Order type |
| status | TEXT | YES | 'pending' | Order status |
| price | DECIMAL(20,8) | NO | - | Order price |
| size | DECIMAL(20,8) | NO | - | Order size |
| filled_size | DECIMAL(20,8) | YES | 0 | Filled size |
| average_fill_price | DECIMAL(20,8) | YES | - | Average fill price |
| fee | DECIMAL(20,8) | YES | 0 | Trading fee |
| fee_currency | TEXT | YES | 'USD' | Fee currency |
| slippage | DECIMAL(20,8) | YES | - | Price slippage |
| pnl | DECIMAL(20,8) | YES | - | Profit/loss |
| pnl_pct | DECIMAL(10,4) | YES | - | P&L percentage |
| stop_loss | DECIMAL(20,8) | YES | - | Stop loss price |
| take_profit | DECIMAL(20,8) | YES | - | Take profit price |
| timestamp | TIMESTAMP | YES | NOW() | Trade timestamp |
| filled_at | TIMESTAMP | YES | - | Fill timestamp |
| cancelled_at | TIMESTAMP | YES | - | Cancellation timestamp |
| metadata | JSONB | YES | '{}' | Additional metadata |
| notes | TEXT | YES | - | Trade notes |

**Constraints**:
- `side`: Must be one of ('buy', 'sell', 'long', 'short')
- `type`: Must be one of ('market', 'limit', 'stop', 'stop_limit')
- `status`: Must be one of ('pending', 'filled', 'partial', 'cancelled', 'rejected', 'expired')
- `positive_size`: size > 0
- `positive_price`: price > 0

**Indexes**:
- `idx_trades_user_id` on (user_id)
- `idx_trades_strategy_id` on (strategy_id)
- `idx_trades_exchange` on (exchange)
- `idx_trades_symbol` on (symbol)
- `idx_trades_status` on (status)
- `idx_trades_timestamp` on (timestamp)
- `idx_trades_user_symbol` on (user_id, symbol)
- `idx_trades_user_timestamp` on (user_id, timestamp DESC)

---

### 5. positions

Open and closed positions with P&L tracking.

**Columns**:

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | UUID | NO | gen_random_uuid() | Primary key |
| user_id | UUID | NO | - | Foreign key to users |
| strategy_id | UUID | YES | - | Foreign key to strategies |
| exchange | TEXT | NO | - | Exchange name |
| symbol | TEXT | NO | - | Trading symbol |
| side | TEXT | NO | - | Position side |
| size | DECIMAL(20,8) | NO | - | Position size |
| avg_entry_price | DECIMAL(20,8) | NO | - | Average entry price |
| current_price | DECIMAL(20,8) | YES | - | Current market price |
| unrealized_pnl | DECIMAL(20,8) | YES | - | Unrealized P&L |
| unrealized_pnl_pct | DECIMAL(10,4) | YES | - | Unrealized P&L % |
| realized_pnl | DECIMAL(20,8) | YES | 0 | Realized P&L |
| realized_pnl_pct | DECIMAL(10,4) | YES | - | Realized P&L % |
| stop_loss | DECIMAL(20,8) | YES | - | Stop loss price |
| take_profit | DECIMAL(20,8) | YES | - | Take profit price |
| liquidation_price | DECIMAL(20,8) | YES | - | Liquidation price |
| leverage | DECIMAL(5,2) | YES | 1.0 | Leverage multiplier |
| margin_used | DECIMAL(20,8) | YES | - | Margin used |
| is_open | BOOLEAN | YES | true | Position open status |
| opened_at | TIMESTAMP | YES | NOW() | Position open time |
| updated_at | TIMESTAMP | YES | NOW() | Last update time |
| closed_at | TIMESTAMP | YES | - | Position close time |
| metadata | JSONB | YES | '{}' | Additional metadata |

**Constraints**:
- `side`: Must be one of ('long', 'short')
- `UNIQUE(user_id, exchange, symbol, is_open)`
- `positive_size_pos`: size > 0
- `valid_leverage`: leverage >= 1.0 AND leverage <= 125.0

**Indexes**:
- `idx_positions_user_id` on (user_id)
- `idx_positions_strategy_id` on (strategy_id)
- `idx_positions_exchange` on (exchange)
- `idx_positions_symbol` on (symbol)
- `idx_positions_is_open` on (is_open)
- `idx_positions_user_open` on (user_id, is_open)

---

### 6. signals

Trading signals from various sources.

**Columns**:

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | UUID | NO | gen_random_uuid() | Primary key |
| user_id | UUID | NO | - | Foreign key to users |
| strategy_id | UUID | YES | - | Foreign key to strategies |
| source | TEXT | NO | - | Signal source |
| asset | TEXT | NO | - | Asset symbol |
| exchange | TEXT | YES | - | Exchange name |
| direction | TEXT | NO | - | Signal direction |
| confidence | DECIMAL(3,2) | NO | - | Confidence score (0-1) |
| strength | TEXT | YES | - | Signal strength |
| rationale | TEXT | YES | - | Signal reasoning |
| indicators | JSONB | YES | - | Technical indicators |
| is_executed | BOOLEAN | YES | false | Execution status |
| executed_at | TIMESTAMP | YES | - | Execution time |
| trade_id | UUID | YES | - | Foreign key to trades |
| expires_at | TIMESTAMP | YES | - | Expiration time |
| is_expired | BOOLEAN | YES | false | Expiration status |
| timestamp | TIMESTAMP | YES | NOW() | Signal timestamp |
| metadata | JSONB | YES | '{}' | Additional metadata |

**Constraints**:
- `source`: Must be one of ('technical_analysis', 'news_classifier', 'multi_agent_sim', 'drl_agent', 'custom')
- `direction`: Must be one of ('long', 'short', 'neutral', 'close')
- `strength`: Must be one of ('weak', 'moderate', 'strong')
- `valid_confidence`: confidence >= 0 AND confidence <= 1

**Indexes**:
- `idx_signals_user_id` on (user_id)
- `idx_signals_strategy_id` on (strategy_id)
- `idx_signals_source` on (source)
- `idx_signals_asset` on (asset)
- `idx_signals_is_executed` on (is_executed)
- `idx_signals_timestamp` on (timestamp DESC)
- `idx_signals_user_timestamp` on (user_id, timestamp DESC)

---

### 7. audit_log

Audit trail for compliance and security.

**Columns**:

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | UUID | NO | gen_random_uuid() | Primary key |
| user_id | UUID | YES | - | Foreign key to users |
| action | TEXT | NO | - | Action performed |
| resource_type | TEXT | YES | - | Resource type |
| resource_id | UUID | YES | - | Resource ID |
| details | JSONB | YES | - | Action details |
| ip_address | INET | YES | - | Client IP address |
| user_agent | TEXT | YES | - | Client user agent |
| request_id | UUID | YES | - | Request identifier |
| status | TEXT | YES | 'success' | Action status |
| error_message | TEXT | YES | - | Error message (if failed) |
| timestamp | TIMESTAMP | YES | NOW() | Action timestamp |
| metadata | JSONB | YES | '{}' | Additional metadata |

**Constraints**:
- `status`: Must be one of ('success', 'failure', 'error')

**Indexes**:
- `idx_audit_user_id` on (user_id)
- `idx_audit_action` on (action)
- `idx_audit_timestamp` on (timestamp DESC)
- `idx_audit_user_timestamp` on (user_id, timestamp DESC)
- `idx_audit_resource` on (resource_type, resource_id)

---

### 8. notifications

User notifications for important events.

**Columns**:

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | UUID | NO | gen_random_uuid() | Primary key |
| user_id | UUID | NO | - | Foreign key to users |
| type | TEXT | NO | - | Notification type |
| title | TEXT | NO | - | Notification title |
| message | TEXT | NO | - | Notification message |
| is_read | BOOLEAN | YES | false | Read status |
| read_at | TIMESTAMP | YES | - | Read timestamp |
| priority | TEXT | YES | 'normal' | Priority level |
| related_resource_type | TEXT | YES | - | Related resource type |
| related_resource_id | UUID | YES | - | Related resource ID |
| created_at | TIMESTAMP | YES | NOW() | Creation time |
| expires_at | TIMESTAMP | YES | - | Expiration time |
| metadata | JSONB | YES | '{}' | Additional metadata |

**Constraints**:
- `type`: Must be one of ('trade', 'signal', 'alert', 'system', 'security')
- `priority`: Must be one of ('low', 'normal', 'high', 'urgent')

**Indexes**:
- `idx_notifications_user_id` on (user_id)
- `idx_notifications_is_read` on (is_read)
- `idx_notifications_created_at` on (created_at DESC)
- `idx_notifications_user_unread` on (user_id, is_read) WHERE is_read = false

---

### 9. alerts

User-configured alerts for price and indicator conditions.

**Columns**:

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | UUID | NO | gen_random_uuid() | Primary key |
| user_id | UUID | NO | - | Foreign key to users |
| name | TEXT | NO | - | Alert name |
| type | TEXT | NO | - | Alert type |
| condition | JSONB | NO | - | Alert condition |
| is_active | BOOLEAN | YES | true | Active status |
| is_triggered | BOOLEAN | YES | false | Trigger status |
| last_triggered_at | TIMESTAMP | YES | - | Last trigger time |
| trigger_count | INT | YES | 0 | Trigger counter |
| notify_email | BOOLEAN | YES | false | Email notification |
| notify_slack | BOOLEAN | YES | false | Slack notification |
| notify_webhook | BOOLEAN | YES | false | Webhook notification |
| webhook_url | TEXT | YES | - | Webhook URL |
| created_at | TIMESTAMP | YES | NOW() | Creation time |
| updated_at | TIMESTAMP | YES | NOW() | Last update time |
| metadata | JSONB | YES | '{}' | Additional metadata |

**Constraints**:
- `type`: Must be one of ('price', 'indicator', 'pnl', 'position', 'custom')

**Indexes**:
- `idx_alerts_user_id` on (user_id)
- `idx_alerts_is_active` on (is_active)
- `idx_alerts_type` on (type)

---

## Row Level Security

All tables have Row Level Security (RLS) enabled to ensure multi-tenant data isolation.

### Policy Summary

| Table | SELECT | INSERT | UPDATE | DELETE |
|-------|--------|--------|--------|--------|
| users | Own profile | - | Own profile | - |
| api_keys | Own keys | Own keys | Own keys | Own keys |
| strategies | Own + public | Own | Own | Own |
| trades | Own | Own | Own | - |
| positions | Own | Own | Own | Own |
| signals | Own | Own | Own | - |
| audit_log | Own | - | - | - |
| notifications | Own | - | Own | Own |
| alerts | Own | Own | Own | Own |

---

## Functions and Triggers

### update_updated_at_column()

Automatically updates the `updated_at` timestamp on row updates.

**Applied to**:
- users
- api_keys
- strategies
- positions
- alerts

### log_audit_event()

Automatically logs changes to sensitive tables in the audit_log.

**Applied to**:
- api_keys (INSERT, UPDATE, DELETE)
- strategies (INSERT, UPDATE, DELETE)

---

## Views

### user_statistics

Aggregated statistics for each user.

**Columns**:
- user_id
- email
- total_strategies
- total_trades
- total_positions
- total_signals
- total_pnl
- winning_trades
- losing_trades

### active_positions_summary

Summary of all open positions.

**Columns**:
- user_id
- exchange
- symbol
- side
- size
- avg_entry_price
- current_price
- unrealized_pnl
- unrealized_pnl_pct
- leverage
- opened_at
- updated_at

---

## Query Examples

### Get User Portfolio Summary

```sql
SELECT 
  u.email,
  COUNT(DISTINCT s.id) AS strategies,
  COUNT(DISTINCT p.id) AS open_positions,
  SUM(p.unrealized_pnl) AS total_unrealized_pnl,
  SUM(t.pnl) AS total_realized_pnl
FROM users u
LEFT JOIN strategies s ON u.id = s.user_id AND s.is_active = true
LEFT JOIN positions p ON u.id = p.user_id AND p.is_open = true
LEFT JOIN trades t ON u.id = t.user_id AND t.status = 'filled'
WHERE u.id = 'user-uuid'
GROUP BY u.id, u.email;
```

### Get Recent Signals

```sql
SELECT 
  s.asset,
  s.direction,
  s.confidence,
  s.source,
  s.rationale,
  s.timestamp
FROM signals s
WHERE s.user_id = 'user-uuid'
  AND s.is_executed = false
  AND s.is_expired = false
ORDER BY s.timestamp DESC
LIMIT 10;
```

### Get Strategy Performance

```sql
SELECT 
  s.name,
  s.type,
  s.total_trades,
  s.winning_trades,
  s.losing_trades,
  ROUND(s.winning_trades::NUMERIC / NULLIF(s.total_trades, 0) * 100, 2) AS win_rate,
  s.total_pnl,
  s.sharpe_ratio,
  s.max_drawdown
FROM strategies s
WHERE s.user_id = 'user-uuid'
  AND s.is_active = true
ORDER BY s.total_pnl DESC;
```

### Get Trade History

```sql
SELECT 
  t.symbol,
  t.side,
  t.type,
  t.price,
  t.size,
  t.pnl,
  t.pnl_pct,
  t.timestamp,
  s.name AS strategy_name
FROM trades t
LEFT JOIN strategies s ON t.strategy_id = s.id
WHERE t.user_id = 'user-uuid'
  AND t.status = 'filled'
ORDER BY t.timestamp DESC
LIMIT 50;
```

---

## Best Practices

1. **Always use prepared statements** to prevent SQL injection
2. **Use indexes** for frequently queried columns
3. **Leverage JSONB** for flexible configuration storage
4. **Enable RLS** for all user-facing tables
5. **Use transactions** for multi-table operations
6. **Monitor query performance** with EXPLAIN ANALYZE
7. **Regular backups** following backup procedures
8. **Keep statistics updated** with ANALYZE

---

## Additional Resources

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Supabase Documentation](https://supabase.com/docs)
- [Database Backup Procedures](./DATABASE_BACKUP_PROCEDURES.md)
- [Migration Scripts](../sql/migrations/)

---

**Last Updated**: 2024
**Schema Version**: 1.0.0
**Maintained By**: Platform Team
