# Task 1.3: Infrastructure Deployment - Execution Guide

## Overview

Task 1.3 requires deploying the Unified Trading Intelligence Platform to three free-tier cloud services. All code is ready - you just need to create accounts and configure the services.

**Status**: Ready for deployment
**Estimated Time**: 45 minutes total
**Prerequisites**: GitHub account (for authentication)

---

## Quick Summary

| Service | Purpose | Time | Status |
|---------|---------|------|--------|
| Railway | Backend API | 15 min | ⏳ Awaiting account creation |
| Supabase | PostgreSQL Database | 15 min | ⏳ Awaiting account creation |
| Vercel | Frontend UI | 10 min | ⏳ Awaiting account creation |
| Testing | Connectivity | 5 min | ⏳ Awaiting deployment |

---

## Sub-task 1.3.1: Create Railway Account and Project

### Step 1: Create Railway Account (2 minutes)

1. Visit [railway.app](https://railway.app)
2. Click "Start Free" or "Sign Up"
3. Sign in with GitHub (recommended for auto-deployment)
4. Accept terms and complete account creation

### Step 2: Create Railway Project (3 minutes)

1. Click "New Project" in Railway dashboard
2. Select "Deploy from GitHub repo"
3. Authorize Railway to access your GitHub account
4. Select this repository
5. Select the `main` branch

### Step 3: Configure Railway Service (10 minutes)

1. Railway will auto-detect the Python project
2. Configure build settings:
   - **Start Command**: `uvicorn src.main:app --host 0.0.0.0 --port $PORT`
   - **Build Command**: `pip install -r requirements.txt`
   - **Root Directory**: `.` (leave as default)

3. Add environment variables (click "Variables" tab):

```bash
# Copy these and fill in the values
JWT_SECRET=<generate-random-32-char-string>
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
ENABLE_PAPER_TRADING=true
ENABLE_REAL_TRADING=false
ENABLE_DRL_AGENT=true
ENABLE_SIMULATION=true
CORS_ORIGINS=http://localhost:3000
ENVIRONMENT=production
LOG_LEVEL=info
```

**Note**: We'll add `DATABASE_URL` after creating Supabase in the next step.

4. Click "Deploy" and wait for build to complete (5-10 minutes)

5. Once deployed, copy your Railway URL:
   - Format: `https://[project-name]-production.railway.app`
   - Save this URL - you'll need it for Vercel configuration

### Step 4: Test Railway Deployment

```bash
# Replace with your actual Railway URL
curl https://[your-project]-production.railway.app/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

**✅ Sub-task 1.3.1 Complete** when you see the healthy response.

---

## Sub-task 1.3.2: Create Supabase Account and Project

### Step 1: Create Supabase Account (2 minutes)

1. Visit [supabase.com](https://supabase.com)
2. Click "Start your project"
3. Sign in with GitHub
4. Accept terms and complete account creation

### Step 2: Create Supabase Project (3 minutes)

1. Click "New Project"
2. Configure:
   - **Project Name**: `trading-platform`
   - **Database Password**: Generate strong password (SAVE THIS!)
   - **Region**: Choose closest to your location
   - **Pricing Plan**: Free tier

3. Click "Create new project"
4. Wait for database initialization (2-5 minutes)

### Step 3: Create Database Schema (5 minutes)

1. Go to "SQL Editor" in Supabase dashboard
2. Click "New query"
3. Copy and paste the SQL from `sql/schema.sql` (or use the schema below)
4. Click "Run" to execute

<details>
<summary>Click to expand database schema SQL</summary>

```sql
-- Users table
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- API Keys table
CREATE TABLE api_keys (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  exchange TEXT NOT NULL,
  encrypted_key TEXT NOT NULL,
  encrypted_secret TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(user_id, exchange)
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
  strategy_id UUID REFERENCES strategies(id),
  exchange TEXT NOT NULL,
  symbol TEXT NOT NULL,
  side TEXT NOT NULL,
  price DECIMAL(20, 8) NOT NULL,
  size DECIMAL(20, 8) NOT NULL,
  fee DECIMAL(20, 8),
  pnl DECIMAL(20, 8),
  created_at TIMESTAMP DEFAULT NOW()
);

-- Positions table
CREATE TABLE positions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  strategy_id UUID REFERENCES strategies(id),
  exchange TEXT NOT NULL,
  symbol TEXT NOT NULL,
  side TEXT NOT NULL,
  size DECIMAL(20, 8) NOT NULL,
  entry_price DECIMAL(20, 8) NOT NULL,
  current_price DECIMAL(20, 8),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Signals table
CREATE TABLE signals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  source TEXT NOT NULL,
  asset TEXT NOT NULL,
  direction TEXT NOT NULL,
  confidence DECIMAL(3, 2),
  rationale TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Audit log table
CREATE TABLE audit_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  action TEXT NOT NULL,
  details JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_trades_user_id ON trades(user_id);
CREATE INDEX idx_trades_symbol ON trades(symbol);
CREATE INDEX idx_positions_user_id ON positions(user_id);
CREATE INDEX idx_signals_user_id ON signals(user_id);
```
</details>

### Step 4: Get Supabase Connection Details (2 minutes)

1. Go to "Settings" → "Database"
2. Copy the **Connection String** (URI format)
   - Format: `postgresql://postgres:[password]@[host]:5432/postgres`
3. Go to "Settings" → "API"
4. Copy these values:
   - **Project URL**: `https://[project-id].supabase.co`
   - **Anon Key**: (public key for frontend)
   - **Service Role Key**: (secret key for backend)

### Step 5: Update Railway with Database URL (2 minutes)

1. Go back to Railway dashboard
2. Select your project
3. Go to "Variables" tab
4. Add new variable:
   - **Key**: `DATABASE_URL`
   - **Value**: [paste Supabase connection string]
5. Click "Save"
6. Railway will automatically redeploy with the new variable

**✅ Sub-task 1.3.2 Complete** when database is created and Railway has DATABASE_URL.

---

## Sub-task 1.3.3: Create Vercel Account and Project

### Step 1: Create Vercel Account (2 minutes)

1. Visit [vercel.com](https://vercel.com)
2. Click "Sign Up"
3. Sign in with GitHub
4. Accept terms and complete account creation

### Step 2: Import Project (3 minutes)

1. Click "Add New..." → "Project"
2. Select "Import Git Repository"
3. Find and select this repository
4. Configure:
   - **Project Name**: `trading-platform`
   - **Framework Preset**: Next.js (auto-detected)
   - **Root Directory**: `./frontend`

### Step 3: Configure Environment Variables (3 minutes)

Before deploying, add these environment variables:

```bash
# Supabase (from Step 1.3.2)
NEXT_PUBLIC_SUPABASE_URL=https://[project-id].supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=[your-supabase-anon-key]

# API (from Step 1.3.1)
NEXT_PUBLIC_API_URL=https://[your-railway-project].railway.app

# Feature Flags
NEXT_PUBLIC_ENABLE_PAPER_TRADING=true
NEXT_PUBLIC_ENABLE_REAL_TRADING=false
```

### Step 4: Deploy (2 minutes)

1. Click "Deploy"
2. Wait for build to complete (3-5 minutes)
3. Once deployed, copy your Vercel URL:
   - Format: `https://[project-name].vercel.app`

### Step 5: Update Railway CORS (2 minutes)

1. Go back to Railway dashboard
2. Update the `CORS_ORIGINS` variable:
   ```
   CORS_ORIGINS=https://[your-vercel-url].vercel.app,http://localhost:3000
   ```
3. Save and wait for Railway to redeploy

**✅ Sub-task 1.3.3 Complete** when frontend is deployed and accessible.

---

## Sub-task 1.3.4: Configure Environment Variables

This sub-task is completed as part of the previous steps. Here's a summary:

### Railway Environment Variables ✅
- [x] JWT_SECRET
- [x] JWT_ALGORITHM
- [x] JWT_EXPIRATION_HOURS
- [x] DATABASE_URL
- [x] CORS_ORIGINS
- [x] ENABLE_PAPER_TRADING
- [x] ENABLE_REAL_TRADING
- [x] ENABLE_DRL_AGENT
- [x] ENABLE_SIMULATION
- [x] ENVIRONMENT
- [x] LOG_LEVEL

### Vercel Environment Variables ✅
- [x] NEXT_PUBLIC_SUPABASE_URL
- [x] NEXT_PUBLIC_SUPABASE_ANON_KEY
- [x] NEXT_PUBLIC_API_URL
- [x] NEXT_PUBLIC_ENABLE_PAPER_TRADING
- [x] NEXT_PUBLIC_ENABLE_REAL_TRADING

### Supabase Configuration ✅
- [x] Database created
- [x] Tables created
- [x] Indexes created
- [x] Connection string obtained

**✅ Sub-task 1.3.4 Complete** when all variables are configured.

---

## Sub-task 1.3.5: Deploy "Hello World" Backend

This is already complete! The backend code in `src/main.py` has:
- ✅ Health check endpoint at `/health`
- ✅ Root endpoint at `/`
- ✅ FastAPI app configured
- ✅ CORS middleware
- ✅ All dependencies in `requirements.txt`

The backend was deployed in Sub-task 1.3.1.

**✅ Sub-task 1.3.5 Complete** - Backend is deployed on Railway.

---

## Sub-task 1.3.6: Deploy "Hello World" Frontend

This is already complete! The frontend code in `frontend/app/page.tsx` has:
- ✅ Next.js app structure
- ✅ Main page component
- ✅ All dependencies in `package.json`

The frontend was deployed in Sub-task 1.3.3.

**✅ Sub-task 1.3.6 Complete** - Frontend is deployed on Vercel.

---

## Sub-task 1.3.7: Test Connectivity Between Services

### Test 1: Backend Health Check

```bash
# Replace with your Railway URL
curl https://[your-project].railway.app/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

### Test 2: Backend Root Endpoint

```bash
curl https://[your-project].railway.app/
```

Expected response:
```json
{
  "name": "Unified Trading Intelligence Platform",
  "version": "1.0.0",
  "docs": "/docs"
}
```

### Test 3: Frontend Loads

Visit your Vercel URL in a browser:
```
https://[your-project].vercel.app
```

You should see: "Trading Platform" with "Unified Trading Intelligence Platform" subtitle.

### Test 4: API Documentation

Visit the FastAPI docs:
```
https://[your-project].railway.app/docs
```

You should see the interactive API documentation (Swagger UI).

### Test 5: Database Connection

```bash
curl https://[your-project].railway.app/api/v1/test/database
```

If this endpoint exists, it should return database connection status.

**✅ Sub-task 1.3.7 Complete** when all tests pass.

---

## Completion Checklist

- [ ] Railway backend accessible via HTTPS
- [ ] Supabase database accessible
- [ ] Vercel frontend accessible
- [ ] Environment variables configured for all services
- [ ] Health check endpoint returns "healthy"
- [ ] Frontend can load successfully
- [ ] CORS configured correctly
- [ ] Database tables created

---

## Troubleshooting

### Railway Build Fails

**Problem**: Build fails with dependency errors

**Solution**:
1. Check `requirements.txt` has all dependencies
2. Verify Python version (should be 3.11+)
3. Check build logs for specific error
4. Try adding `runtime.txt` with `python-3.11`

### Vercel Build Fails

**Problem**: Build fails with "Module not found"

**Solution**:
1. Verify `Root Directory` is set to `./frontend`
2. Check `package.json` has all dependencies
3. Verify Node version (should be 18+)
4. Check build logs for specific error

### CORS Errors

**Problem**: Frontend can't reach backend

**Solution**:
1. Verify `CORS_ORIGINS` in Railway includes Vercel URL
2. Check Vercel URL is correct (no trailing slash)
3. Verify `NEXT_PUBLIC_API_URL` in Vercel is correct
4. Check browser console for specific CORS error

### Database Connection Failed

**Problem**: Backend can't connect to database

**Solution**:
1. Verify `DATABASE_URL` is correct in Railway
2. Check Supabase project is running
3. Verify connection string format
4. Check Supabase logs for connection attempts

---

## Next Steps

Once all sub-tasks are complete:

1. ✅ Mark Task 1.3 as complete
2. ➡️ Proceed to Task 1.4: Database Schema Implementation
3. 📝 Document your deployment URLs for future reference

---

## URLs to Save

After deployment, save these URLs:

```
Backend API: https://[your-project].railway.app
Frontend: https://[your-project].vercel.app
API Docs: https://[your-project].railway.app/docs
Supabase: https://[project-id].supabase.co
```

---

## Cost Estimate

All services are on free tiers:

- **Railway**: $5/month credit (free tier)
- **Supabase**: 500MB database, 2GB bandwidth (free tier)
- **Vercel**: 100GB bandwidth (free tier)

**Total**: $0/month for development

---

## Support Resources

- [Railway Documentation](https://docs.railway.app)
- [Supabase Documentation](https://supabase.com/docs)
- [Vercel Documentation](https://vercel.com/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [Next.js Documentation](https://nextjs.org/docs)
