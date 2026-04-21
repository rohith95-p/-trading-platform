# Infrastructure Deployment Guide

This guide provides step-by-step instructions for deploying the Unified Trading Intelligence Platform to Railway (backend), Supabase (database), and Vercel (frontend).

## Overview

The Phase 1 MVP uses a free-tier deployment stack:

- **Backend**: Railway (Python FastAPI)
- **Database**: Supabase (PostgreSQL + Auth)
- **Frontend**: Vercel (Next.js/React)
- **Logging**: Better Stack (optional)

**Total Cost**: $0-200/month (bootstrap phase)

---

## Task 1.3.1: Create Railway Account and Project

### Step 1: Create Railway Account

1. Go to [railway.app](https://railway.app)
2. Click "Start Free" or "Sign Up"
3. Choose authentication method (GitHub, Google, or email)
4. Complete email verification if needed
5. Accept terms and create account

### Step 2: Create Railway Project

1. Click "New Project" in the Railway dashboard
2. Select "Deploy from GitHub" or "Create Empty Project"
3. If using GitHub:
   - Authorize Railway to access your GitHub account
   - Select the repository containing the backend code
   - Select the branch (main or develop)
4. If creating empty project:
   - Click "Create Empty Project"
   - Name it "trading-platform-api"

### Step 3: Configure Railway Service

1. In the project, click "New Service"
2. Select "GitHub Repo" and choose your repository
3. Configure the service:
   - **Name**: `trading-platform-api`
   - **Root Directory**: `.` (or path to backend code)
   - **Start Command**: `uvicorn src.main:app --host 0.0.0.0 --port $PORT`
   - **Build Command**: `pip install -r requirements.txt`

### Step 4: Set Environment Variables

1. In the service settings, go to "Variables"
2. Add the following environment variables:

```bash
# Database
DATABASE_URL=postgresql://...  # Will be set after Supabase setup
REDIS_URL=redis://...          # Will be set after Redis setup

# Authentication
JWT_SECRET=<generate-random-secret>
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# External APIs
ANTHROPIC_API_KEY=<your-claude-key>
KALSHI_API_KEY=<your-kalshi-key>
POLYMARKET_API_KEY=<your-polymarket-key>
ALPACA_API_KEY=<your-alpaca-key>
ALPACA_SECRET_KEY=<your-alpaca-secret>

# Encryption
ENCRYPTION_KEY=<generate-32-byte-hex-key>

# Logging
BETTERSTACK_SOURCE_TOKEN=<your-betterstack-token>

# Feature Flags
ENABLE_PAPER_TRADING=true
ENABLE_REAL_TRADING=false
ENABLE_DRL_AGENT=true
ENABLE_SIMULATION=true
```

### Step 5: Deploy

1. Click "Deploy" button
2. Wait for build to complete (5-10 minutes)
3. Once deployed, you'll get a public URL like: `https://trading-platform-api-production.railway.app`
4. Test the deployment with: `curl https://trading-platform-api-production.railway.app/health`

### Step 6: Configure Health Check

1. In service settings, go to "Health Check"
2. Set health check URL: `/health`
3. Set interval: 30 seconds
4. Set timeout: 10 seconds

---

## Task 1.3.2: Create Supabase Account and Project

### Step 1: Create Supabase Account

1. Go to [supabase.com](https://supabase.com)
2. Click "Start your project" or "Sign Up"
3. Choose authentication method (GitHub or email)
4. Complete email verification if needed
5. Accept terms and create account

### Step 2: Create Supabase Project

1. Click "New Project" in the Supabase dashboard
2. Configure the project:
   - **Project Name**: `trading-platform`
   - **Database Password**: Generate a strong password (save this!)
   - **Region**: Choose closest to your location
   - **Pricing Plan**: Free tier

3. Click "Create new project"
4. Wait for database to initialize (2-5 minutes)

### Step 3: Get Connection String

1. In the project, go to "Settings" → "Database"
2. Copy the connection string (PostgreSQL URI)
3. Format: `postgresql://[user]:[password]@[host]:[port]/[database]`
4. Save this for Railway environment variables

### Step 4: Create Database Tables

1. Go to "SQL Editor" in Supabase
2. Create a new query
3. Paste the following SQL to create all tables:

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

4. Click "Run" to execute the SQL

### Step 5: Configure Authentication

1. Go to "Authentication" → "Providers"
2. Enable "Email" provider:
   - Enable "Email Confirmations"
   - Set "Confirm email" to "Enabled"
3. Enable "Google" provider:
   - Add your Google OAuth credentials
4. Enable "GitHub" provider:
   - Add your GitHub OAuth credentials

### Step 6: Get API Keys

1. Go to "Settings" → "API"
2. Copy the following:
   - **Project URL**: `https://[project-id].supabase.co`
   - **Anon Key**: Public key for frontend
   - **Service Role Key**: Secret key for backend

3. Save these for Railway and Vercel environment variables

---

## Task 1.3.3: Create Vercel Account and Project

### Step 1: Create Vercel Account

1. Go to [vercel.com](https://vercel.com)
2. Click "Sign Up"
3. Choose authentication method (GitHub, GitLab, Bitbucket, or email)
4. Complete email verification if needed
5. Accept terms and create account

### Step 2: Create Vercel Project

1. Click "New Project" in the Vercel dashboard
2. Select "Import Git Repository"
3. Choose your GitHub repository containing the frontend code
4. Configure the project:
   - **Project Name**: `trading-platform`
   - **Framework**: Next.js (auto-detected)
   - **Root Directory**: `./frontend` (if frontend is in subdirectory)

5. Click "Import"

### Step 3: Configure Environment Variables

1. In the project settings, go to "Environment Variables"
2. Add the following variables:

```bash
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

3. Click "Save"

### Step 4: Deploy

1. Click "Deploy" button
2. Wait for build to complete (3-5 minutes)
3. Once deployed, you'll get a public URL like: `https://trading-platform.vercel.app`
4. Test the deployment by visiting the URL

### Step 5: Configure Custom Domain (Optional)

1. In project settings, go to "Domains"
2. Add your custom domain
3. Follow DNS configuration instructions
4. Wait for DNS propagation (up to 48 hours)

---

## Task 1.3.4: Configure Environment Variables for All Services

### Railway Backend Environment Variables

```bash
# Database
DATABASE_URL=postgresql://[user]:[password]@[host]:[port]/[database]
REDIS_URL=redis://[host]:[port]

# Authentication
JWT_SECRET=<generate-random-secret-min-32-chars>
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

### Supabase Configuration

- **Database**: PostgreSQL 15
- **Connection Pooling**: Enabled (max 10 connections)
- **Backups**: Daily automatic backups
- **Auth**: Email + OAuth (Google, GitHub)

### Vercel Frontend Environment Variables

```bash
# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://[project-id].supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<your-supabase-anon-key>

# API
NEXT_PUBLIC_API_URL=https://trading-platform-api-production.railway.app
NEXT_PUBLIC_WS_URL=wss://trading-platform-api-production.railway.app/ws

# Feature Flags
NEXT_PUBLIC_ENABLE_PAPER_TRADING=true
NEXT_PUBLIC_ENABLE_REAL_TRADING=false

# Analytics (optional)
NEXT_PUBLIC_GA_ID=<your-google-analytics-id>
```

---

## Task 1.3.5: Deploy "Hello World" Backend to Railway

### Step 1: Create Hello World Endpoint

Create `src/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI(title="Trading Platform API", version="1.0.0")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://trading-platform.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "trading-platform-api",
        "version": "1.0.0"
    }

@app.get("/")
async def root():
    """Hello World endpoint"""
    return {
        "message": "Hello World from Trading Platform API",
        "environment": os.getenv("ENVIRONMENT", "development")
    }

@app.get("/api/v1/health")
async def api_health():
    """API health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Step 2: Create requirements.txt

```
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-dotenv==1.0.0
pydantic==2.5.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
redis==5.0.1
cryptography==41.0.7
```

### Step 3: Deploy to Railway

1. Push code to GitHub
2. Railway will auto-deploy on push
3. Monitor deployment in Railway dashboard
4. Once deployed, test with:

```bash
curl https://trading-platform-api-production.railway.app/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "trading-platform-api",
  "version": "1.0.0"
}
```

---

## Task 1.3.6: Deploy "Hello World" Frontend to Vercel

### Step 1: Create Hello World Page

Create `frontend/pages/index.tsx`:

```typescript
import React from 'react';

export default function Home() {
  return (
    <div style={{ padding: '2rem', textAlign: 'center' }}>
      <h1>Hello World from Trading Platform</h1>
      <p>Frontend deployed on Vercel</p>
      <p>Backend API: {process.env.NEXT_PUBLIC_API_URL}</p>
    </div>
  );
}
```

### Step 2: Create package.json

```json
{
  "name": "trading-platform-frontend",
  "version": "1.0.0",
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  },
  "dependencies": {
    "next": "^14.0.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "@supabase/supabase-js": "^2.38.0"
  }
}
```

### Step 3: Deploy to Vercel

1. Push code to GitHub
2. Vercel will auto-deploy on push
3. Monitor deployment in Vercel dashboard
4. Once deployed, visit: `https://trading-platform.vercel.app`

Expected page:
```
Hello World from Trading Platform
Frontend deployed on Vercel
Backend API: https://trading-platform-api-production.railway.app
```

---

## Task 1.3.7: Test Connectivity Between Services

### Test 1: Backend Health Check

```bash
curl https://trading-platform-api-production.railway.app/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "trading-platform-api",
  "version": "1.0.0"
}
```

### Test 2: Frontend Loads

```bash
curl https://trading-platform.vercel.app
```

Expected response: HTML page with "Hello World from Trading Platform"

### Test 3: Frontend Can Reach Backend

Create a test endpoint in frontend:

```typescript
// pages/api/test.ts
import { NextApiRequest, NextApiResponse } from 'next';

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  try {
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/health`
    );
    const data = await response.json();
    res.status(200).json({ backend: data });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
}
```

Test with:
```bash
curl https://trading-platform.vercel.app/api/test
```

Expected response:
```json
{
  "backend": {
    "status": "healthy",
    "service": "trading-platform-api",
    "version": "1.0.0"
  }
}
```

### Test 4: Database Connection

Create a test endpoint in backend:

```python
@app.get("/api/v1/test/database")
async def test_database():
    """Test database connection"""
    try:
        # Test connection
        result = await db.execute("SELECT 1")
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

### Test 5: Environment Variables

Verify all services have correct environment variables:

**Railway**:
```bash
# In Railway dashboard, check Variables tab
```

**Supabase**:
```bash
# In Supabase dashboard, check Settings → API
```

**Vercel**:
```bash
# In Vercel dashboard, check Settings → Environment Variables
```

---

## Monitoring and Alerts

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

1. Check build logs in Railway dashboard
2. Verify `requirements.txt` has all dependencies
3. Check `start command` is correct
4. Verify environment variables are set

### Frontend Won't Deploy

1. Check build logs in Vercel dashboard
2. Verify `package.json` has all dependencies
3. Check `build command` is correct
4. Verify environment variables are set

### Database Connection Failed

1. Verify `DATABASE_URL` is correct
2. Check Supabase project is running
3. Verify IP whitelist (if applicable)
4. Test connection locally first

### CORS Errors

1. Verify `CORS_ORIGINS` includes frontend URL
2. Check frontend is using correct API URL
3. Verify API is returning CORS headers

---

## Next Steps

1. Deploy "Hello World" backend to Railway
2. Deploy "Hello World" frontend to Vercel
3. Test connectivity between services
4. Proceed to Task 1.4 (Database Schema Implementation)

---

## References

- [Railway Documentation](https://docs.railway.app)
- [Supabase Documentation](https://supabase.com/docs)
- [Vercel Documentation](https://vercel.com/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [Next.js Documentation](https://nextjs.org/docs)
