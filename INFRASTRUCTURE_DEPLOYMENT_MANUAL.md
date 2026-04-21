# Infrastructure Deployment Manual - Task 1.3

## Overview

This manual provides step-by-step instructions for deploying the Unified Trading Intelligence Platform to production using free-tier services:

- **Backend**: Railway (Python FastAPI)
- **Database**: Supabase (PostgreSQL + Auth)
- **Frontend**: Vercel (Next.js/React)

**Estimated Time**: 2-3 hours
**Cost**: $0-200/month (free tier bootstrap)

---

## Prerequisites

Before starting, ensure you have:

1. GitHub account with the trading platform repository
2. Email address for creating accounts
3. API keys for external services (Claude, Kalshi, Polymarket, Alpaca)
4. Text editor for managing environment variables
5. Terminal/command line access

---

## Part 1: Railway Backend Deployment

### Step 1.1: Create Railway Account

1. Go to [railway.app](https://railway.app)
2. Click "Start Free" button
3. Choose authentication method:
   - GitHub (recommended - easier for CI/CD)
   - Google
   - Email
4. Complete email verification if needed
5. Accept terms and create account

**Expected Result**: You're logged into Railway dashboard

### Step 1.2: Create Railway Project

1. In Railway dashboard, click "New Project"
2. Select "Deploy from GitHub"
3. Authorize Railway to access your GitHub account
4. Select your trading platform repository
5. Select the branch (main or develop)
6. Click "Deploy"

**Expected Result**: Railway creates a project and begins deployment

### Step 1.3: Configure Railway Service

1. In the project, click on the service (or create new if needed)
2. Go to "Settings" tab
3. Configure:
   - **Service Name**: `trading-platform-api`
   - **Root Directory**: `.` (root of repository)
   - **Start Command**: `uvicorn src.main:app --host 0.0.0.0 --port $PORT`
   - **Build Command**: `pip install -r requirements.txt`

4. Click "Save"

**Expected Result**: Service is configured with correct build/start commands

### Step 1.4: Set Railway Environment Variables

1. In the service, go to "Variables" tab
2. Add the following environment variables:

```
# Database (will be set after Supabase setup)
DATABASE_URL=postgresql://user:password@host:port/database

# Redis (optional for Phase 1)
REDIS_URL=redis://localhost:6379

# Authentication
JWT_SECRET=<generate-random-32-char-string>
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# External APIs
ANTHROPIC_API_KEY=<your-claude-api-key>
KALSHI_API_KEY=<your-kalshi-api-key>
POLYMARKET_API_KEY=<your-polymarket-api-key>
ALPACA_API_KEY=<your-alpaca-api-key>
ALPACA_SECRET_KEY=<your-alpaca-secret-key>

# Encryption
ENCRYPTION_KEY=<generate-32-byte-hex-key>

# Logging
BETTERSTACK_SOURCE_TOKEN=<your-betterstack-token>

# Feature Flags
ENABLE_PAPER_TRADING=true
ENABLE_REAL_TRADING=false
ENABLE_DRL_AGENT=true
ENABLE_SIMULATION=true

# CORS
CORS_ORIGINS=https://trading-platform.vercel.app,http://localhost:3000

# Environment
ENVIRONMENT=production
LOG_LEVEL=info
```

3. Click "Save" after each variable

**Expected Result**: All environment variables are set in Railway

### Step 1.5: Deploy Backend

1. In Railway dashboard, click "Deploy" button
2. Monitor the deployment in the "Deployments" tab
3. Wait for build to complete (5-10 minutes)
4. Once deployed, you'll see a public URL like:
   ```
   https://trading-platform-api-production.railway.app
   ```

5. Test the deployment:
   ```bash
   curl https://trading-platform-api-production.railway.app/health
   ```

**Expected Response**:
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

**Expected Result**: Backend is deployed and accessible via HTTPS

---

## Part 2: Supabase Database Setup

### Step 2.1: Create Supabase Account

1. Go to [supabase.com](https://supabase.com)
2. Click "Start your project" or "Sign Up"
3. Choose authentication method:
   - GitHub (recommended)
   - Email
4. Complete email verification if needed
5. Accept terms and create account

**Expected Result**: You're logged into Supabase dashboard

### Step 2.2: Create Supabase Project

1. In Supabase dashboard, click "New Project"
2. Configure the project:
   - **Project Name**: `trading-platform`
   - **Database Password**: Generate a strong password (save this!)
   - **Region**: Choose closest to your location
   - **Pricing Plan**: Free tier

3. Click "Create new project"
4. Wait for database to initialize (2-5 minutes)

**Expected Result**: Supabase project is created and database is running

### Step 2.3: Get Database Connection String

1. In the project, go to "Settings" → "Database"
2. Copy the connection string (PostgreSQL URI)
3. Format: `postgresql://[user]:[password]@[host]:[port]/[database]`
4. Save this for Railway environment variables

**Expected Result**: You have the DATABASE_URL for Railway

### Step 2.4: Create Database Tables

1. In Supabase, go to "SQL Editor"
2. Click "New Query"
3. Copy and paste the SQL from `sql/schema.sql` (see below)
4. Click "Run"
5. Wait for tables to be created

**SQL Schema** (save as `sql/schema.sql`):

```sql
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

-- Create indexes
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
```

**Expected Result**: All 7 tables created with indexes and RLS policies

### Step 2.5: Configure Authentication

1. In Supabase, go to "Authentication" → "Providers"
2. Enable "Email" provider:
   - Toggle "Email Confirmations" to ON
   - Set "Confirm email" to "Enabled"
3. Enable "Google" provider (optional):
   - Add your Google OAuth credentials
4. Enable "GitHub" provider (optional):
   - Add your GitHub OAuth credentials

**Expected Result**: Authentication providers are configured

### Step 2.6: Get Supabase API Keys

1. In Supabase, go to "Settings" → "API"
2. Copy and save:
   - **Project URL**: `https://[project-id].supabase.co`
   - **Anon Key**: Public key for frontend
   - **Service Role Key**: Secret key for backend

3. Add these to Railway and Vercel environment variables

**Expected Result**: You have Supabase API keys for frontend and backend

---

## Part 3: Vercel Frontend Deployment

### Step 3.1: Create Vercel Account

1. Go to [vercel.com](https://vercel.com)
2. Click "Sign Up"
3. Choose authentication method:
   - GitHub (recommended)
   - GitLab
   - Bitbucket
   - Email
4. Complete email verification if needed
5. Accept terms and create account

**Expected Result**: You're logged into Vercel dashboard

### Step 3.2: Create Vercel Project

1. In Vercel dashboard, click "New Project"
2. Select "Import Git Repository"
3. Choose your GitHub repository
4. Configure the project:
   - **Project Name**: `trading-platform`
   - **Framework**: Next.js (auto-detected)
   - **Root Directory**: `./frontend` (if frontend is in subdirectory)

5. Click "Import"

**Expected Result**: Vercel creates a project and begins deployment

### Step 3.3: Configure Vercel Environment Variables

1. In the project settings, go to "Environment Variables"
2. Add the following variables:

```
# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://[project-id].supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<your-supabase-anon-key>

# API
NEXT_PUBLIC_API_URL=https://trading-platform-api-production.railway.app
NEXT_PUBLIC_WS_URL=wss://trading-platform-api-production.railway.app/ws

# Feature Flags
NEXT_PUBLIC_ENABLE_PAPER_TRADING=true
NEXT_PUBLIC_ENABLE_REAL_TRADING=false
```

3. Click "Save" after each variable

**Expected Result**: All environment variables are set in Vercel

### Step 3.4: Deploy Frontend

1. In Vercel dashboard, click "Deploy" button
2. Monitor the deployment in the "Deployments" tab
3. Wait for build to complete (3-5 minutes)
4. Once deployed, you'll see a public URL like:
   ```
   https://trading-platform.vercel.app
   ```

5. Visit the URL to verify the frontend loads

**Expected Result**: Frontend is deployed and accessible via HTTPS

---

## Part 4: Test Connectivity

### Test 4.1: Backend Health Check

```bash
curl https://trading-platform-api-production.railway.app/health
```

**Expected Response**:
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

### Test 4.2: Frontend Loads

Visit: `https://trading-platform.vercel.app`

**Expected Result**: Page displays "Trading Platform" heading

### Test 4.3: Frontend Can Reach Backend

Create a test endpoint in frontend (`frontend/app/api/test/route.ts`):

```typescript
export async function GET() {
  try {
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/health`
    );
    const data = await response.json();
    return Response.json({ backend: data });
  } catch (error) {
    return Response.json({ error: error.message }, { status: 500 });
  }
}
```

Test with:
```bash
curl https://trading-platform.vercel.app/api/test
```

**Expected Response**:
```json
{
  "backend": {
    "status": "healthy",
    "version": "1.0.0"
  }
}
```

### Test 4.4: Database Connection

Create a test endpoint in backend (`src/api/test.py`):

```python
from fastapi import APIRouter
from datetime import datetime

router = APIRouter(prefix="/api/v1/test", tags=["test"])

@router.get("/database")
async def test_database():
    """Test database connection"""
    try:
        # Test connection
        return {
            "status": "connected",
            "database": "PostgreSQL",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
```

Test with:
```bash
curl https://trading-platform-api-production.railway.app/api/v1/test/database
```

**Expected Response**:
```json
{
  "status": "connected",
  "database": "PostgreSQL",
  "timestamp": "2024-01-15T10:30:00.000000"
}
```

---

## Part 5: Monitoring and Maintenance

### Railway Monitoring

1. Go to Railway dashboard
2. Select your project
3. Monitor:
   - CPU usage
   - Memory usage
   - Disk usage
   - Network I/O
   - Logs

### Supabase Monitoring

1. Go to Supabase dashboard
2. Select your project
3. Monitor:
   - Database connections
   - Query performance
   - Storage usage
   - Auth events

### Vercel Monitoring

1. Go to Vercel dashboard
2. Select your project
3. Monitor:
   - Build status
   - Deployment history
   - Performance metrics
   - Error logs

---

## Troubleshooting

### Backend Won't Deploy

**Problem**: Build fails in Railway
**Solution**:
1. Check build logs in Railway dashboard
2. Verify `requirements.txt` has all dependencies
3. Check `start command` is correct
4. Verify environment variables are set
5. Try redeploying from GitHub

### Frontend Won't Deploy

**Problem**: Build fails in Vercel
**Solution**:
1. Check build logs in Vercel dashboard
2. Verify `package.json` has all dependencies
3. Check `build command` is correct
4. Verify environment variables are set
5. Try redeploying from GitHub

### Database Connection Failed

**Problem**: Backend can't connect to Supabase
**Solution**:
1. Verify `DATABASE_URL` is correct in Railway
2. Check Supabase project is running
3. Verify IP whitelist (if applicable)
4. Test connection locally first

### CORS Errors

**Problem**: Frontend can't reach backend
**Solution**:
1. Verify `CORS_ORIGINS` includes frontend URL in Railway
2. Check frontend is using correct API URL
3. Verify API is returning CORS headers
4. Check browser console for specific error

---

## Completion Checklist

- [ ] Railway account created
- [ ] Railway project deployed
- [ ] Railway environment variables set
- [ ] Backend health check working
- [ ] Supabase account created
- [ ] Supabase project created
- [ ] Database tables created
- [ ] Supabase API keys obtained
- [ ] Vercel account created
- [ ] Vercel project deployed
- [ ] Vercel environment variables set
- [ ] Frontend loads successfully
- [ ] Frontend can reach backend
- [ ] Database connection working
- [ ] All services accessible via HTTPS

---

## Next Steps

Once infrastructure is deployed:

1. Proceed to Task 1.4 (Database Schema Implementation)
2. Proceed to Task 1.5 (Authentication System)
3. Proceed to Task 1.6 (API Key Management)

---

## References

- [Railway Documentation](https://docs.railway.app)
- [Supabase Documentation](https://supabase.com/docs)
- [Vercel Documentation](https://vercel.com/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [Next.js Documentation](https://nextjs.org/docs)

