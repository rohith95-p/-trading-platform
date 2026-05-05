# Placeholders, TODOs & Hardcoded Values

> Auto-generated audit. Every item here needs a real value or implementation before production.

---

## 🔴 CRITICAL — Security / Auth

### 1. `src/config.py` — Default JWT secret
```python
JWT_SECRET: str = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "your-encryption-key-change-in-production")
```
**Fix**: Set `JWT_SECRET` and `ENCRYPTION_KEY` as Railway env vars.
Real values already generated in `RAILWAY_DEPLOYMENT_INFO.md`.

### 2. `src/auth/jwt_handler.py` line 20
```python
self.secret_key = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
```
**Fix**: Same as above — env var must be set.

### 3. `src/auth/auth_service.py` line 362
```python
secret = "JBSWY3DPEHPK3PXP"  # Placeholder
```
**Fix**: 2FA secret must be fetched from database per user, not hardcoded.

---

## 🟠 HIGH — Unimplemented Features

### 4. `src/api/auth.py` — OAuth not implemented
```python
# TODO: Implement Google OAuth flow  (line 475)
# TODO: Implement GitHub OAuth flow  (line 489)
# TODO: Implement Google OAuth callback  (line 506)
# TODO: Implement GitHub OAuth callback  (line 523)
```
**Fix**: Implement Supabase OAuth or python-social-auth.

### 5. `src/api/auth.py` — Profile & password endpoints
```python
# TODO: Fetch user profile from database  (line 316)
# TODO: Verify current password and update to new password  (line 288)
```
**Fix**: Wire to `auth_service` and database.

### 6. `src/auth/auth_service.py` — 2FA database ops
```python
# TODO: Store secret and backup codes in database  (line 342)
# TODO: Get user's 2FA secret from database  (line 361)
# TODO: Remove 2FA secret from database  (line 377)
# TODO: Update user's last_login_at in database  (line 160)
```
**Fix**: Add `totp_secret` column to users table, implement CRUD.

### 7. `src/api_keys/api_key_service.py` — Exchange validation
```python
# TODO: Make actual test API call to exchange  (line 381)
```
**Fix**: Each connector's `connect()` method should be called to validate.

### 8. `src/api/intelligence.py` line 85 — Placeholder indicator endpoint
```python
# Placeholder - in production would fetch real data
prices = [100.0 + i for i in range(100)]
```
**Fix**: This old `/indicators` endpoint is superseded by `/indicators/compute`. Either remove or wire to real data.

### 9. `src/api/intelligence.py` line 738 — Placeholder simulation
```python
"reasoning": "Placeholder simulation"
```
**Fix**: This `/simulate` endpoint in `intelligence.py` conflicts with the real one in `simulation.py`. Remove this stub.

### 10. `src/backtesting/pandas_backtester.py` line 79 — Placeholder signal
```python
# --- Signal generation (simple placeholder: buy every 10 bars) ---
df.loc[df.index[::10], "signal"] = 1
```
**Fix**: Accept strategy signals from config/strategy executor instead of hardcoded every-10-bars.

---

## 🟡 MEDIUM — Missing Config Values

### 11. `src/config.py` — Missing Supabase keys
```python
# Not present at all
SUPABASE_URL = ...
SUPABASE_ANON_KEY = ...
SUPABASE_SERVICE_KEY = ...
```
**Fix**: Add to `src/config.py` Settings class.

### 12. `src/config.py` — Missing OpenAI key
```python
# Not present — needed for simulation engine
OPENAI_API_KEY = ...
```
**Fix**: Add optional field, simulation falls back to mock if absent.

### 13. `.env.development` — Exchange API keys empty
```
KALSHI_API_KEY=
POLYMARKET_API_KEY=
ALPACA_API_KEY=
HYPERLIQUID_API_KEY=
DYDX_API_KEY=
KRAKEN_API_KEY=
BINANCE_API_KEY=
```
**Fix**: Fill in paper trading keys from each exchange dashboard.

---

## 🟢 LOW — Minor TODOs

### 14. `src/auth/middleware.py` lines 126, 143
```python
# TODO: Check if user's email is verified
# TODO: Check if user has premium subscription
```
**Fix**: Add `email_verified` and `subscription_tier` to User model.

### 15. `src/api_keys/api_key_service.py` line 607
```python
# TODO: Implement detailed usage tracking by day
```
**Fix**: Add `api_key_usage` table with daily aggregation.

---

## ✅ Already Handled

- `SUPABASE_URL` / `SUPABASE_ANON_KEY` / `SUPABASE_SERVICE_KEY` → in `.env.local` ✅
- `JWT_SECRET` / `ENCRYPTION_KEY` → generated, in `RAILWAY_DEPLOYMENT_INFO.md` ✅
- Railway backend deployed ✅
- All exchange connectors use paper trading mode by default ✅

---

## Action Priority

| # | Item | Priority | Effort |
|---|------|----------|--------|
| 1-3 | JWT/Encryption env vars | 🔴 Critical | 5 min |
| 4 | OAuth (Google/GitHub) | 🟠 High | 2 days |
| 5-6 | Auth profile/2FA DB ops | 🟠 High | 1 day |
| 9 | Remove duplicate /simulate | 🟠 High | 10 min |
| 11-12 | Add Supabase/OpenAI to config | 🟡 Medium | 30 min |
| 10 | Real backtester signals | 🟡 Medium | 1 day |
| 7 | Exchange key validation | 🟡 Medium | 2 hours |
| 13 | Fill exchange API keys | 🟡 Medium | 1 hour |
| 14-15 | Minor TODOs | 🟢 Low | 1 day |
