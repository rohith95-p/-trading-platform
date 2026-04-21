# Infrastructure Deployment Checklist

This checklist tracks the completion of Task 1.3 (Infrastructure Deployment).

## Task 1.3.1: Create Railway Account and Project (Task 6.1)

**MANUAL SETUP REQUIRED** - Follow the detailed guide: `docs/TASK_6.1_RAILWAY_SETUP.md`

### Quick Checklist:
- [ ] Create Railway account at railway.app
- [ ] Create Railway project named "trading-platform-api"
- [ ] Add PostgreSQL database
- [ ] Add Redis cache
- [ ] Generate JWT secret and encryption key
- [ ] Configure Railway service with:
  - [ ] Name: `trading-platform-api`
  - [ ] Start Command: `uvicorn src.main:app --host 0.0.0.0 --port $PORT`
  - [ ] Dockerfile: `Dockerfile.backend`
- [ ] Set Railway environment variables:
  - [ ] DATABASE_URL (auto-configured)
  - [ ] REDIS_URL (auto-configured)
  - [ ] JWT_SECRET (generate with: `openssl rand -base64 32`)
  - [ ] JWT_ALGORITHM = `HS256`
  - [ ] JWT_EXPIRATION_HOURS = `24`
  - [ ] ENCRYPTION_KEY (generate with: `openssl rand -hex 32`)
  - [ ] ENABLE_PAPER_TRADING = `true`
  - [ ] ENABLE_REAL_TRADING = `false`
  - [ ] ENABLE_DRL_AGENT = `true`
  - [ ] ENABLE_SIMULATION = `true`
  - [ ] ENVIRONMENT = `production`
  - [ ] LOG_LEVEL = `info`
  - [ ] CORS_ORIGINS = `http://localhost:3000`
- [ ] Deploy backend to Railway (automatic on push)
- [ ] Verify deployment with: `curl https://your-app.railway.app/health`
- [ ] Get Railway public URL and save it
- [ ] Access API docs: `https://your-app.railway.app/docs`

**Detailed Instructions**: See `docs/TASK_6.1_RAILWAY_SETUP.md` and `docs/RAILWAY_DEPLOYMENT_GUIDE.md`

**Status**: ⏳ Pending (Manual account creation required)
**Estimated Time**: 1 hour

---

## Task 1.3.2: Create Supabase Account and Project

- [ ] Create Supabase account at supabase.com
- [ ] Create Supabase project named "trading-platform"
- [ ] Configure project:
  - [ ] Database password: (save securely)
  - [ ] Region: (choose closest to location)
  - [ ] Pricing plan: Free tier
- [ ] Get connection string (PostgreSQL URI)
- [ ] Create database tables:
  - [ ] users table
  - [ ] api_keys table
  - [ ] strategies table
  - [ ] trades table
  - [ ] positions table
  - [ ] signals table
  - [ ] audit_log table
- [ ] Create database indexes:
  - [ ] idx_trades_user_id
  - [ ] idx_trades_symbol
  - [ ] idx_trades_timestamp
  - [ ] idx_positions_user_id
  - [ ] idx_signals_user_id
  - [ ] idx_signals_timestamp
  - [ ] idx_audit_user_id
  - [ ] idx_audit_timestamp
- [ ] Enable Row Level Security (RLS):
  - [ ] strategies table
  - [ ] trades table
  - [ ] positions table
  - [ ] signals table
  - [ ] api_keys table
- [ ] Create RLS policies:
  - [ ] Users can view own strategies
  - [ ] Users can view own trades
  - [ ] Users can view own positions
  - [ ] Users can view own signals
  - [ ] Users can view own api_keys
- [ ] Configure authentication:
  - [ ] Enable Email provider
  - [ ] Enable Google OAuth
  - [ ] Enable GitHub OAuth
- [ ] Get API keys:
  - [ ] Project URL
  - [ ] Anon Key
  - [ ] Service Role Key
- [ ] Verify database connection

**Status**: ⏳ Pending (Manual account creation required)

---

## Task 1.3.3: Create Vercel Account and Project

- [ ] Create Vercel account at vercel.com
- [ ] Create Vercel project named "trading-platform"
- [ ] Configure project:
  - [ ] Framework: Next.js (auto-detected)
  - [ ] Root Directory: `./frontend` (if applicable)
- [ ] Set Vercel environment variables:
  - [ ] NEXT_PUBLIC_SUPABASE_URL
  - [ ] NEXT_PUBLIC_SUPABASE_ANON_KEY
  - [ ] NEXT_PUBLIC_API_URL
  - [ ] NEXT_PUBLIC_WS_URL
  - [ ] NEXT_PUBLIC_ENABLE_PAPER_TRADING
  - [ ] NEXT_PUBLIC_ENABLE_REAL_TRADING
- [ ] Deploy frontend to Vercel
- [ ] Verify deployment by visiting: `https://trading-platform.vercel.app`
- [ ] Get Vercel public URL: `https://trading-platform.vercel.app`

**Status**: ⏳ Pending (Manual account creation required)

---

## Task 1.3.4: Configure Environment Variables for All Services

### Railway Backend

- [ ] DATABASE_URL = `postgresql://[user]:[password]@[host]:[port]/[database]`
- [ ] REDIS_URL = `redis://[host]:[port]`
- [ ] JWT_SECRET = (32+ character random string)
- [ ] JWT_ALGORITHM = `HS256`
- [ ] JWT_EXPIRATION_HOURS = `24`
- [ ] ANTHROPIC_API_KEY = (from Anthropic console)
- [ ] KALSHI_API_KEY = (from Kalshi dashboard)
- [ ] POLYMARKET_API_KEY = (from Polymarket dashboard)
- [ ] ALPACA_API_KEY = (from Alpaca dashboard)
- [ ] ALPACA_SECRET_KEY = (from Alpaca dashboard)
- [ ] ENCRYPTION_KEY = (32-byte hex key)
- [ ] BETTERSTACK_SOURCE_TOKEN = (from Better Stack)
- [ ] ENABLE_PAPER_TRADING = `true`
- [ ] ENABLE_REAL_TRADING = `false`
- [ ] ENABLE_DRL_AGENT = `true`
- [ ] ENABLE_SIMULATION = `true`
- [ ] CORS_ORIGINS = `https://trading-platform.vercel.app,http://localhost:3000`
- [ ] ENVIRONMENT = `production`
- [ ] LOG_LEVEL = `info`

### Supabase

- [ ] Database: PostgreSQL 15
- [ ] Connection Pooling: Enabled (max 10 connections)
- [ ] Backups: Daily automatic backups
- [ ] Auth: Email + OAuth (Google, GitHub)

### Vercel Frontend

- [ ] NEXT_PUBLIC_SUPABASE_URL = `https://[project-id].supabase.co`
- [ ] NEXT_PUBLIC_SUPABASE_ANON_KEY = (from Supabase)
- [ ] NEXT_PUBLIC_API_URL = `https://trading-platform-api-production.railway.app`
- [ ] NEXT_PUBLIC_WS_URL = `wss://trading-platform-api-production.railway.app/ws`
- [ ] NEXT_PUBLIC_ENABLE_PAPER_TRADING = `true`
- [ ] NEXT_PUBLIC_ENABLE_REAL_TRADING = `false`

**Status**: ⏳ Pending (Requires Railway, Supabase, Vercel setup)

---

## Task 1.3.5: Deploy "Hello World" Backend to Railway

- [ ] Create `src/main.py` with FastAPI app
- [ ] Create `requirements.txt` with dependencies
- [ ] Test locally: `python -m uvicorn src.main:app --reload`
- [ ] Push code to GitHub
- [ ] Railway auto-deploys on push
- [ ] Monitor deployment in Railway dashboard
- [ ] Test health endpoint: `curl https://trading-platform-api-production.railway.app/health`
- [ ] Verify response:
  ```json
  {
    "status": "healthy",
    "service": "trading-platform-api",
    "version": "1.0.0"
  }
  ```

**Status**: ✅ Complete (Code created, awaiting Railway deployment)

---

## Task 1.3.6: Deploy "Hello World" Frontend to Vercel

- [ ] Create `frontend/pages/index.tsx` with Hello World page
- [ ] Create `frontend/package.json` with dependencies
- [ ] Test locally: `npm run dev`
- [ ] Push code to GitHub
- [ ] Vercel auto-deploys on push
- [ ] Monitor deployment in Vercel dashboard
- [ ] Visit: `https://trading-platform.vercel.app`
- [ ] Verify page displays "Hello World from Trading Platform"

**Status**: ⏳ Pending (Requires frontend code and Vercel setup)

---

## Task 1.3.7: Test Connectivity Between Services

### Test 1: Backend Health Check

- [ ] Run: `curl https://trading-platform-api-production.railway.app/health`
- [ ] Verify response includes `"status": "healthy"`

### Test 2: Frontend Loads

- [ ] Visit: `https://trading-platform.vercel.app`
- [ ] Verify page displays correctly

### Test 3: Frontend Can Reach Backend

- [ ] Create test endpoint in frontend
- [ ] Run: `curl https://trading-platform.vercel.app/api/test`
- [ ] Verify response includes backend health status

### Test 4: Database Connection

- [ ] Create test endpoint in backend
- [ ] Run: `curl https://trading-platform-api-production.railway.app/api/v1/test/database`
- [ ] Verify response includes `"status": "connected"`

### Test 5: Environment Variables

- [ ] Verify Railway has all required variables
- [ ] Verify Supabase has correct configuration
- [ ] Verify Vercel has all required variables

**Status**: ⏳ Pending (Requires all services deployed)

---

## Summary

| Task | Status | Notes |
|------|--------|-------|
| 1.3.1 Create Railway Account | ⏳ Pending | Manual account creation required |
| 1.3.2 Create Supabase Account | ⏳ Pending | Manual account creation required |
| 1.3.3 Create Vercel Account | ⏳ Pending | Manual account creation required |
| 1.3.4 Configure Environment Variables | ⏳ Pending | Requires accounts created |
| 1.3.5 Deploy Backend | ✅ Complete | Code ready, awaiting Railway |
| 1.3.6 Deploy Frontend | ⏳ Pending | Requires frontend code |
| 1.3.7 Test Connectivity | ⏳ Pending | Requires all services deployed |

---

## Next Steps

1. Create Railway account and project
2. Create Supabase account and project
3. Create Vercel account and project
4. Configure environment variables for all services
5. Deploy backend to Railway
6. Deploy frontend to Vercel
7. Test connectivity between services
8. Proceed to Task 1.4 (Database Schema Implementation)

---

## References

- [Railway Documentation](https://docs.railway.app)
- [Supabase Documentation](https://supabase.com/docs)
- [Vercel Documentation](https://vercel.com/docs)
- [Infrastructure Deployment Guide](./INFRASTRUCTURE_DEPLOYMENT_GUIDE.md)
