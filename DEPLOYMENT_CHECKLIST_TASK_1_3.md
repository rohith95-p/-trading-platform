# Task 1.3: Infrastructure Deployment - Detailed Checklist

## Overview

This checklist tracks the completion of all sub-tasks for Task 1.3 (Infrastructure Deployment). Each sub-task has specific completion criteria that must be verified.

**Total Sub-tasks**: 7
**Estimated Time**: 2-3 hours
**Status**: Ready for manual execution

---

## Sub-task 1.3.1: Create Railway Account and Project

### Objectives
- Create Railway account
- Create Railway project
- Configure service settings
- Set environment variables
- Deploy backend

### Checklist

#### Account Creation
- [ ] Go to railway.app
- [ ] Click "Start Free"
- [ ] Choose authentication method (GitHub recommended)
- [ ] Complete email verification
- [ ] Accept terms and create account
- [ ] Verify you're logged into Railway dashboard

#### Project Creation
- [ ] Click "New Project" in Railway dashboard
- [ ] Select "Deploy from GitHub"
- [ ] Authorize Railway to access GitHub
- [ ] Select trading platform repository
- [ ] Select branch (main or develop)
- [ ] Click "Deploy"
- [ ] Verify project is created

#### Service Configuration
- [ ] In the project, click on the service
- [ ] Go to "Settings" tab
- [ ] Set Service Name: `trading-platform-api`
- [ ] Set Root Directory: `.`
- [ ] Set Start Command: `uvicorn src.main:app --host 0.0.0.0 --port $PORT`
- [ ] Set Build Command: `pip install -r requirements.txt`
- [ ] Click "Save"

#### Environment Variables
- [ ] Go to "Variables" tab
- [ ] Add DATABASE_URL (will be set after Supabase)
- [ ] Add REDIS_URL
- [ ] Add JWT_SECRET (generate random 32-char string)
- [ ] Add JWT_ALGORITHM: `HS256`
- [ ] Add JWT_EXPIRATION_HOURS: `24`
- [ ] Add ANTHROPIC_API_KEY
- [ ] Add KALSHI_API_KEY
- [ ] Add POLYMARKET_API_KEY
- [ ] Add ALPACA_API_KEY
- [ ] Add ALPACA_SECRET_KEY
- [ ] Add ENCRYPTION_KEY (generate 32-byte hex key)
- [ ] Add BETTERSTACK_SOURCE_TOKEN
- [ ] Add ENABLE_PAPER_TRADING: `true`
- [ ] Add ENABLE_REAL_TRADING: `false`
- [ ] Add ENABLE_DRL_AGENT: `true`
- [ ] Add ENABLE_SIMULATION: `true`
- [ ] Add CORS_ORIGINS: `https://trading-platform.vercel.app,http://localhost:3000`
- [ ] Add ENVIRONMENT: `production`
- [ ] Add LOG_LEVEL: `info`

#### Deployment
- [ ] Click "Deploy" button
- [ ] Monitor deployment in "Deployments" tab
- [ ] Wait for build to complete (5-10 minutes)
- [ ] Verify deployment succeeded
- [ ] Note the public URL: `https://trading-platform-api-production.railway.app`

#### Verification
- [ ] Test health endpoint: `curl https://trading-platform-api-production.railway.app/health`
- [ ] Verify response includes `"status": "healthy"`
- [ ] Verify response includes `"version": "1.0.0"`

**Completion Criteria**:
- ✅ Railway account created
- ✅ Railway project deployed
- ✅ All environment variables set
- ✅ Backend accessible via HTTPS
- ✅ Health check endpoint working

**Status**: ⏳ Pending (Manual account creation required)

---

## Sub-task 1.3.2: Create Supabase Account and Project

### Objectives
- Create Supabase account
- Create Supabase project
- Create database tables
- Configure authentication
- Get API keys

### Checklist

#### Account Creation
- [ ] Go to supabase.com
- [ ] Click "Start your project" or "Sign Up"
- [ ] Choose authentication method (GitHub recommended)
- [ ] Complete email verification
- [ ] Accept terms and create account
- [ ] Verify you're logged into Supabase dashboard

#### Project Creation
- [ ] Click "New Project" in Supabase dashboard
- [ ] Set Project Name: `trading-platform`
- [ ] Generate and save Database Password
- [ ] Choose Region (closest to your location)
- [ ] Select Pricing Plan: Free tier
- [ ] Click "Create new project"
- [ ] Wait for database to initialize (2-5 minutes)
- [ ] Verify project is running

#### Get Connection String
- [ ] Go to "Settings" → "Database"
- [ ] Copy PostgreSQL connection string
- [ ] Format: `postgresql://[user]:[password]@[host]:[port]/[database]`
- [ ] Save as DATABASE_URL for Railway

#### Create Database Tables
- [ ] Go to "SQL Editor"
- [ ] Click "New Query"
- [ ] Copy SQL from `sql/schema.sql`
- [ ] Paste into SQL editor
- [ ] Click "Run"
- [ ] Verify all tables created:
  - [ ] users table
  - [ ] api_keys table
  - [ ] strategies table
  - [ ] trades table
  - [ ] positions table
  - [ ] signals table
  - [ ] audit_log table
- [ ] Verify indexes created:
  - [ ] idx_trades_user_id
  - [ ] idx_trades_symbol
  - [ ] idx_trades_timestamp
  - [ ] idx_positions_user_id
  - [ ] idx_signals_user_id
  - [ ] idx_signals_timestamp
  - [ ] idx_audit_user_id
  - [ ] idx_audit_timestamp
- [ ] Verify RLS enabled on all tables
- [ ] Verify RLS policies created

#### Configure Authentication
- [ ] Go to "Authentication" → "Providers"
- [ ] Enable "Email" provider
- [ ] Toggle "Email Confirmations" to ON
- [ ] Set "Confirm email" to "Enabled"
- [ ] Enable "Google" provider (optional)
- [ ] Add Google OAuth credentials (optional)
- [ ] Enable "GitHub" provider (optional)
- [ ] Add GitHub OAuth credentials (optional)

#### Get API Keys
- [ ] Go to "Settings" → "API"
- [ ] Copy Project URL: `https://[project-id].supabase.co`
- [ ] Copy Anon Key (public key for frontend)
- [ ] Copy Service Role Key (secret key for backend)
- [ ] Save all keys for Railway and Vercel

**Completion Criteria**:
- ✅ Supabase account created
- ✅ Supabase project created
- ✅ All 7 tables created with correct schema
- ✅ All indexes created
- ✅ RLS policies active
- ✅ Authentication providers configured
- ✅ API keys obtained

**Status**: ⏳ Pending (Manual account creation required)

---

## Sub-task 1.3.3: Create Vercel Account and Project

### Objectives
- Create Vercel account
- Create Vercel project
- Configure environment variables
- Deploy frontend

### Checklist

#### Account Creation
- [ ] Go to vercel.com
- [ ] Click "Sign Up"
- [ ] Choose authentication method (GitHub recommended)
- [ ] Complete email verification
- [ ] Accept terms and create account
- [ ] Verify you're logged into Vercel dashboard

#### Project Creation
- [ ] Click "New Project" in Vercel dashboard
- [ ] Select "Import Git Repository"
- [ ] Choose trading platform repository
- [ ] Set Project Name: `trading-platform`
- [ ] Verify Framework: Next.js (auto-detected)
- [ ] Set Root Directory: `./frontend` (if applicable)
- [ ] Click "Import"
- [ ] Verify project is created

#### Environment Variables
- [ ] Go to project settings
- [ ] Go to "Environment Variables"
- [ ] Add NEXT_PUBLIC_SUPABASE_URL: `https://[project-id].supabase.co`
- [ ] Add NEXT_PUBLIC_SUPABASE_ANON_KEY: (from Supabase)
- [ ] Add NEXT_PUBLIC_API_URL: `https://trading-platform-api-production.railway.app`
- [ ] Add NEXT_PUBLIC_WS_URL: `wss://trading-platform-api-production.railway.app/ws`
- [ ] Add NEXT_PUBLIC_ENABLE_PAPER_TRADING: `true`
- [ ] Add NEXT_PUBLIC_ENABLE_REAL_TRADING: `false`
- [ ] Click "Save" after each variable

#### Deployment
- [ ] Click "Deploy" button
- [ ] Monitor deployment in "Deployments" tab
- [ ] Wait for build to complete (3-5 minutes)
- [ ] Verify deployment succeeded
- [ ] Note the public URL: `https://trading-platform.vercel.app`

#### Verification
- [ ] Visit `https://trading-platform.vercel.app`
- [ ] Verify page loads successfully
- [ ] Verify page displays "Trading Platform" heading

**Completion Criteria**:
- ✅ Vercel account created
- ✅ Vercel project deployed
- ✅ All environment variables set
- ✅ Frontend accessible via HTTPS
- ✅ Frontend loads successfully

**Status**: ⏳ Pending (Manual account creation required)

---

## Sub-task 1.3.4: Configure Environment Variables for All Services

### Objectives
- Verify all Railway environment variables
- Verify all Supabase configuration
- Verify all Vercel environment variables

### Checklist

#### Railway Backend Variables
- [ ] DATABASE_URL = PostgreSQL connection string from Supabase
- [ ] REDIS_URL = Redis connection string (or localhost:6379 for Phase 1)
- [ ] JWT_SECRET = Random 32+ character string
- [ ] JWT_ALGORITHM = `HS256`
- [ ] JWT_EXPIRATION_HOURS = `24`
- [ ] ANTHROPIC_API_KEY = From Anthropic console
- [ ] KALSHI_API_KEY = From Kalshi dashboard
- [ ] POLYMARKET_API_KEY = From Polymarket dashboard
- [ ] ALPACA_API_KEY = From Alpaca dashboard
- [ ] ALPACA_SECRET_KEY = From Alpaca dashboard
- [ ] ENCRYPTION_KEY = 32-byte hex key
- [ ] BETTERSTACK_SOURCE_TOKEN = From Better Stack
- [ ] ENABLE_PAPER_TRADING = `true`
- [ ] ENABLE_REAL_TRADING = `false`
- [ ] ENABLE_DRL_AGENT = `true`
- [ ] ENABLE_SIMULATION = `true`
- [ ] CORS_ORIGINS = `https://trading-platform.vercel.app,http://localhost:3000`
- [ ] ENVIRONMENT = `production`
- [ ] LOG_LEVEL = `info`

#### Supabase Configuration
- [ ] Database: PostgreSQL 15
- [ ] Connection Pooling: Enabled (max 10 connections)
- [ ] Backups: Daily automatic backups enabled
- [ ] Auth: Email + OAuth configured
- [ ] RLS: Enabled on all tables
- [ ] Policies: All RLS policies created

#### Vercel Frontend Variables
- [ ] NEXT_PUBLIC_SUPABASE_URL = Supabase project URL
- [ ] NEXT_PUBLIC_SUPABASE_ANON_KEY = Supabase anon key
- [ ] NEXT_PUBLIC_API_URL = Railway backend URL
- [ ] NEXT_PUBLIC_WS_URL = Railway WebSocket URL
- [ ] NEXT_PUBLIC_ENABLE_PAPER_TRADING = `true`
- [ ] NEXT_PUBLIC_ENABLE_REAL_TRADING = `false`

**Completion Criteria**:
- ✅ All Railway variables set and verified
- ✅ All Supabase configuration verified
- ✅ All Vercel variables set and verified

**Status**: ⏳ Pending (Requires Railway, Supabase, Vercel setup)

---

## Sub-task 1.3.5: Deploy "Hello World" Backend to Railway

### Objectives
- Verify backend code exists
- Verify requirements.txt exists
- Deploy to Railway
- Test health endpoint

### Checklist

#### Code Verification
- [ ] Verify `src/main.py` exists
- [ ] Verify `src/main.py` has `/health` endpoint
- [ ] Verify `src/main.py` has `/` endpoint
- [ ] Verify `requirements.txt` exists
- [ ] Verify `requirements.txt` has all dependencies
- [ ] Verify `Dockerfile.backend` exists

#### Local Testing (Optional)
- [ ] Create virtual environment: `python -m venv venv`
- [ ] Activate virtual environment: `source venv/bin/activate`
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Run locally: `python -m uvicorn src.main:app --reload`
- [ ] Test health endpoint: `curl http://localhost:8000/health`
- [ ] Verify response includes `"status": "healthy"`

#### Railway Deployment
- [ ] Push code to GitHub
- [ ] Railway auto-deploys on push
- [ ] Monitor deployment in Railway dashboard
- [ ] Wait for build to complete
- [ ] Verify deployment succeeded

#### Verification
- [ ] Test health endpoint: `curl https://trading-platform-api-production.railway.app/health`
- [ ] Verify response:
  ```json
  {
    "status": "healthy",
    "version": "1.0.0"
  }
  ```
- [ ] Test root endpoint: `curl https://trading-platform-api-production.railway.app/`
- [ ] Verify response includes API information

**Completion Criteria**:
- ✅ Backend code exists and is correct
- ✅ Backend deployed to Railway
- ✅ Backend accessible via HTTPS
- ✅ Health check endpoint working
- ✅ Root endpoint working

**Status**: ✅ Complete (Code ready, awaiting Railway deployment)

---

## Sub-task 1.3.6: Deploy "Hello World" Frontend to Vercel

### Objectives
- Verify frontend code exists
- Verify package.json exists
- Deploy to Vercel
- Test frontend loads

### Checklist

#### Code Verification
- [ ] Verify `frontend/app/page.tsx` exists
- [ ] Verify `frontend/app/page.tsx` has "Trading Platform" heading
- [ ] Verify `frontend/package.json` exists
- [ ] Verify `frontend/package.json` has all dependencies
- [ ] Verify `frontend/next.config.js` exists

#### Local Testing (Optional)
- [ ] Navigate to frontend directory: `cd frontend`
- [ ] Install dependencies: `npm install`
- [ ] Run locally: `npm run dev`
- [ ] Visit `http://localhost:3000`
- [ ] Verify page loads and displays "Trading Platform"

#### Vercel Deployment
- [ ] Push code to GitHub
- [ ] Vercel auto-deploys on push
- [ ] Monitor deployment in Vercel dashboard
- [ ] Wait for build to complete
- [ ] Verify deployment succeeded

#### Verification
- [ ] Visit `https://trading-platform.vercel.app`
- [ ] Verify page loads successfully
- [ ] Verify page displays "Trading Platform" heading
- [ ] Verify page displays "Unified Trading Intelligence Platform"

**Completion Criteria**:
- ✅ Frontend code exists and is correct
- ✅ Frontend deployed to Vercel
- ✅ Frontend accessible via HTTPS
- ✅ Frontend loads successfully
- ✅ Frontend displays correct content

**Status**: ⏳ Pending (Requires Vercel deployment)

---

## Sub-task 1.3.7: Test Connectivity Between Services

### Objectives
- Test backend health check
- Test frontend loads
- Test frontend can reach backend
- Test database connection
- Verify all environment variables

### Checklist

#### Test 1: Backend Health Check
- [ ] Run: `curl https://trading-platform-api-production.railway.app/health`
- [ ] Verify response status: 200 OK
- [ ] Verify response includes `"status": "healthy"`
- [ ] Verify response includes `"version": "1.0.0"`

#### Test 2: Frontend Loads
- [ ] Visit: `https://trading-platform.vercel.app`
- [ ] Verify page loads successfully
- [ ] Verify page displays "Trading Platform" heading
- [ ] Verify page displays "Unified Trading Intelligence Platform"
- [ ] Verify no console errors

#### Test 3: Frontend Can Reach Backend
- [ ] Create test endpoint in frontend (if not exists)
- [ ] Run: `curl https://trading-platform.vercel.app/api/test`
- [ ] Verify response status: 200 OK
- [ ] Verify response includes backend health status
- [ ] Verify response includes `"status": "healthy"`

#### Test 4: Database Connection
- [ ] Create test endpoint in backend (if not exists)
- [ ] Run: `curl https://trading-platform-api-production.railway.app/api/v1/test/database`
- [ ] Verify response status: 200 OK
- [ ] Verify response includes `"status": "connected"`
- [ ] Verify response includes `"database": "PostgreSQL"`

#### Test 5: Environment Variables
- [ ] Verify Railway has all required variables
- [ ] Verify Supabase has correct configuration
- [ ] Verify Vercel has all required variables
- [ ] Verify no sensitive data in logs

#### Test 6: HTTPS/SSL
- [ ] Verify backend URL uses HTTPS: `https://trading-platform-api-production.railway.app`
- [ ] Verify frontend URL uses HTTPS: `https://trading-platform.vercel.app`
- [ ] Verify SSL certificates are valid
- [ ] Verify no mixed content warnings

**Completion Criteria**:
- ✅ Backend health check working
- ✅ Frontend loads successfully
- ✅ Frontend can reach backend
- ✅ Database connection working
- ✅ All environment variables configured
- ✅ All services accessible via HTTPS

**Status**: ⏳ Pending (Requires all services deployed)

---

## Summary Table

| Sub-task | Description | Status | Notes |
|----------|-------------|--------|-------|
| 1.3.1 | Create Railway Account and Project | ⏳ Pending | Manual account creation required |
| 1.3.2 | Create Supabase Account and Project | ⏳ Pending | Manual account creation required |
| 1.3.3 | Create Vercel Account and Project | ⏳ Pending | Manual account creation required |
| 1.3.4 | Configure Environment Variables | ⏳ Pending | Requires accounts created |
| 1.3.5 | Deploy Backend to Railway | ✅ Ready | Code prepared, awaiting Railway |
| 1.3.6 | Deploy Frontend to Vercel | ⏳ Pending | Requires Vercel deployment |
| 1.3.7 | Test Connectivity | ⏳ Pending | Requires all services deployed |

---

## Completion Criteria for Task 1.3

All of the following must be true:

- ✅ Railway backend accessible via HTTPS
- ✅ Supabase database accessible
- ✅ Vercel frontend accessible
- ✅ Environment variables configured for all services
- ✅ All services communicating (frontend → backend → database)
- ✅ Health check endpoints working
- ✅ Database tables created with correct schema
- ✅ RLS policies active
- ✅ Authentication providers configured

---

## Next Steps

Once all sub-tasks are complete:

1. Proceed to Task 1.4 (Database Schema Implementation)
2. Proceed to Task 1.5 (Authentication System)
3. Proceed to Task 1.6 (API Key Management)

---

## Resources

- [INFRASTRUCTURE_DEPLOYMENT_MANUAL.md](./INFRASTRUCTURE_DEPLOYMENT_MANUAL.md) - Detailed step-by-step guide
- [sql/schema.sql](./sql/schema.sql) - Database schema SQL
- [.env.railway.example](./.env.railway.example) - Railway environment variables template
- [.env.vercel.example](./.env.vercel.example) - Vercel environment variables template
- [Railway Documentation](https://docs.railway.app)
- [Supabase Documentation](https://supabase.com/docs)
- [Vercel Documentation](https://vercel.com/docs)

