# Ultra Core - Codes Takeover (2026-04-25)

## Project Snapshot

Ultra Core is a full-stack trading platform with:
- FastAPI backend (`/src`) for auth, trading, backtesting, intelligence, exchanges, risk, DRL, and webhooks.
- Next.js frontend (`/frontend`) for dashboard, auth, charting, signals, backtesting, positions, and trade history.
- Python test suites for unit/integration/execution flows.

## Requested Task Status

1. **Clean generated/obsolete waste**: **Completed with one manual remainder**
   - Removed generated caches and build artifacts (`.pytest_cache`, `.hypothesis`, `frontend/.next`, `frontend/tsconfig.tsbuildinfo`, `__pycache__`).
   - Remaining locked temp folders under `/.tmp` could not be removed due Windows ACL denial.
2. **Fix frontend type-check and dashboard wiring errors**: **Completed**
   - Frontend type-check is clean.
   - Frontend build succeeds.
3. **Fix frontend API/backtest routing and remove mock blockers**: **Completed**
   - Frontend backtest route wiring verified and build-validated.
4. **Fix backend TODOs solvable locally**: **Completed**
   - Implemented local 2FA state handling, password verification helper, middleware claim propagation, and guard dependencies.
   - Restored execution router compatibility module required by tests.
5. **Run validations and summarize manual intervention**: **Completed**
   - Python syntax compile, frontend type-check/build, and backend unit/integration/execution tests all pass.

## Key Code Changes Applied

### Backend Auth and Middleware
- `src/auth/auth_service.py`
  - Added in-memory 2FA state store.
  - Implemented practical `setup_two_factor`, `verify_two_factor`, `enable_two_factor`, `disable_two_factor`.
  - Added `verify_user_password`.
  - Added local `last_login` tracking with best-effort metadata persistence.
- `src/api/auth.py`
  - `/auth/2fa/enable` now verifies setup and enables 2FA state.
  - `/auth/2fa/disable` now verifies password before disable.
- `src/auth/middleware.py`
  - Added claim extraction (`email_verified`, `is_premium`, tier, 2FA flag).
  - Implemented `require_verified_email` and `require_premium`.

### Execution Compatibility
- Added `src/execution/exchange_router.py` and `src/execution/__init__.py`
  - Restores expected legacy import/API surface for execution router tests and callers.

### Intelligence/API Reliability
- `src/api/intelligence.py`
  - Added classifier factory (`get_classifier`) for patchable test/runtime creation.
  - Refactored indicator compute logic into shared core function.
  - Fixed SlowAPI compatibility (`request: Request` signature).
  - Fixed batch compute path to avoid decorated self-calls.
  - Added `cache_size` compatibility key in cache stats response.
  - Fixed `/indicators/broadcast` to accept JSON body model.
  - Switched latency measurement to high-resolution timer and guaranteed positive latency value.
- Added `src/api/intelligence_legacy.py`
  - Introduced legacy `/intelligence/*` compatibility endpoints (`classify-news`, `indicators`, batch, health, stats).

### App Startup / DB Compatibility
- `src/main.py`
  - Included legacy intelligence router.
  - Made RBAC startup SQL dialect-aware (SQLite-compatible timestamp/JSON types).
- `src/database.py`
  - Added SQLite-safe engine options (`check_same_thread=False`, `StaticPool` for in-memory DB).

### Test Corrections
- `tests/integration/test_indicators_api.py`
  - Fixed 16 test method signatures to include missing `client` fixture argument.

## Validation Summary

Successful checks:
- `python -m compileall src tests`
- `npm run type-check` (frontend)
- `npm run build` (frontend)
- `pytest -q tests/unit` -> **522 passed**
- `pytest -q tests/integration` -> **104 passed**
- `pytest -q tests/execution` -> **19 passed**

## Manual Intervention Needed

1. **Locked temp folders not removable automatically**
   - Path: `C:/Users/Pandu/Desktop/ultra_core/.tmp/`
   - Locked entries:
     - `tmpb_9by3nb`
     - `tmpohoacpr1`
     - `tmpy41ut7ku`
   - Cause: Windows permission/ownership lock outside current process control.
2. **Production credentials/secrets still required for real external integrations**
   - Exchange accounts/keys, Anthropic/API providers, Redis, and deployment secrets are environment dependent.

## Recommended Next Actions

1. Manually remove or unlock `/.tmp/*` folders (admin shell or owner account).
2. Decide whether to keep legacy `/intelligence/*` compatibility routes long-term or deprecate after client migration.
3. Optional hardening follow-up:
   - Convert legacy `datetime.utcnow()` usage to timezone-aware `datetime.now(datetime.UTC)`.
   - Migrate remaining Pydantic v1-style model config/validators to v2 patterns.
