# Railway Backend Deployment Guide

## Overview

This guide walks you through deploying the Unified Trading Platform backend to Railway. The backend is a FastAPI application with PostgreSQL database and Redis cache.

---

## Prerequisites

- GitHub account (for code repository)
- Railway account (free tier available)
- Backend code ready in repository

---

## Step 1: Create Railway Account

1. Go to [railway.app](https://railway.app)
2. Click "Start a New Project" or "Login"
3. Sign up with GitHub (recommended for automatic deployments)
4. Verify your email address

---

## Step 2: Create New Project

1. Click "New Project" in Railway dashboard
2. Select "Deploy from GitHub repo"
3. Authorize Railway to access your GitHub repositories
4. Select your trading platform repository
5. Railway will detect the project automatically

---

## Step 3: Configure Service Settings

### Service Name
- Set service name to: `trading-platform-api`

### Build Configuration
Railway should auto-detect the Dockerfile, but verify:
- **Build Method**: Dockerfile
- **Dockerfile Path**: `Dockerfile.backend`
- **Build Command**: (leave empty, Docker handles this)

### Start Configuration
- **Start Command**: `uvicorn src.main:app --host 0.0.0.0 --port $PORT`
- Railway automatically provides the `$PORT` environment variable

---

## Step 4: Add PostgreSQL Database

1. In your Railway project, click "New"
2. Select "Database" → "PostgreSQL"
3. Railway will provision a PostgreSQL instance
4. The `DATABASE_URL` environment variable is automatically added to your service

---

## Step 5: Add Redis Cache

1. In your Railway project, click "New"
2. Select "Database" → "Redis"
3. Railway will provision a Redis instance
4. The `REDIS_URL` environment variable is automatically added to your service

---

## Step 6: Configure Environment Variables

Go to your service settings → Variables tab and add:

### Required Variables

```bash
# Authentication (generate secure random strings)
JWT_SECRET=<generate-32-char-random-string>
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Encryption (generate 32-byte hex key)
ENCRYPTION_KEY=<generate-32-byte-hex-key>

# Feature Flags
ENABLE_PAPER_TRADING=true
ENABLE_REAL_TRADING=false
ENABLE_DRL_AGENT=true
ENABLE_SIMULATION=true

# Environment
ENVIRONMENT=production
LOG_LEVEL=info

# CORS (update with your frontend URL)
CORS_ORIGINS=https://trading-platform.vercel.app,http://localhost:3000
```

### Optional Variables (add when ready)

```bash
# External APIs (add when you have API keys)
ANTHROPIC_API_KEY=<your-claude-api-key>
KALSHI_API_KEY=<your-kalshi-api-key>
POLYMARKET_API_KEY=<your-polymarket-api-key>
ALPACA_API_KEY=<your-alpaca-api-key>
ALPACA_SECRET_KEY=<your-alpaca-secret-key>

# Logging (add when you have Better Stack account)
BETTERSTACK_SOURCE_TOKEN=<your-betterstack-token>
```

### Auto-Generated Variables (Railway provides these)
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `PORT` - Port number for the service

---

## Step 7: Generate Secure Keys

### JWT Secret (32+ characters)
```bash
# On Linux/Mac:
openssl rand -base64 32

# On Windows (PowerShell):
[Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Minimum 0 -Maximum 256 }))
```

### Encryption Key (32-byte hex)
```bash
# On Linux/Mac:
openssl rand -hex 32

# On Windows (PowerShell):
-join ((1..32) | ForEach-Object { '{0:x2}' -f (Get-Random -Minimum 0 -Maximum 256) })
```

---

## Step 8: Deploy

1. Railway automatically deploys when you push to your GitHub repository
2. Monitor deployment in the Railway dashboard
3. Check deployment logs for any errors
4. Wait for deployment to complete (usually 2-5 minutes)

---

## Step 9: Get Your Public URL

1. Go to your service settings in Railway
2. Click on "Settings" tab
3. Scroll to "Domains" section
4. Railway provides a default domain like: `trading-platform-api-production.railway.app`
5. (Optional) Add a custom domain if you have one

---

## Step 10: Verify Deployment

### Test Health Endpoint
```bash
curl https://your-app.railway.app/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

### Test Root Endpoint
```bash
curl https://your-app.railway.app/
```

Expected response:
```json
{
  "name": "Unified Trading Intelligence Platform",
  "version": "1.0.0",
  "docs": "/docs"
}
```

### Access API Documentation
Visit: `https://your-app.railway.app/docs`

---

## Step 11: Configure Health Checks (Optional)

Railway automatically monitors your service, but you can configure custom health checks:

1. Go to service settings → "Health Checks"
2. Set health check path: `/health`
3. Set interval: 30 seconds
4. Set timeout: 10 seconds
5. Set restart threshold: 3 failures

---

## Step 12: Setup Database Schema

After deployment, you need to initialize the database:

### Option A: Using Alembic Migrations (Recommended)
```bash
# SSH into Railway service (if available) or run locally with production DATABASE_URL
railway run alembic upgrade head
```

### Option B: Manual SQL Execution
1. Connect to Railway PostgreSQL using provided credentials
2. Execute the schema from `sql/schema.sql`

---

## Troubleshooting

### Deployment Fails
- Check build logs in Railway dashboard
- Verify Dockerfile.backend exists and is correct
- Ensure requirements.txt has all dependencies

### Service Crashes on Start
- Check runtime logs in Railway dashboard
- Verify all required environment variables are set
- Check DATABASE_URL and REDIS_URL are accessible

### Database Connection Errors
- Verify DATABASE_URL is set correctly
- Check PostgreSQL service is running in Railway
- Ensure database schema is initialized

### Redis Connection Errors
- Verify REDIS_URL is set correctly
- Check Redis service is running in Railway

### CORS Errors
- Update CORS_ORIGINS environment variable
- Include your frontend URL (Vercel deployment URL)

---

## Cost Estimation

### Railway Free Tier
- $5 credit per month
- Includes:
  - 512 MB RAM per service
  - Shared CPU
  - PostgreSQL database
  - Redis cache
  - Custom domains

### Estimated Monthly Cost (Free Tier)
- Backend service: ~$2-3/month
- PostgreSQL: ~$1-2/month
- Redis: ~$0.50-1/month
- **Total**: ~$3.50-6/month (within free tier)

### Scaling (Paid Plans)
- Hobby: $5/month per service
- Pro: $20/month per service
- Includes more resources and priority support

---

## Automatic Deployments

Railway automatically deploys when you:
1. Push to your main/master branch
2. Merge a pull request
3. Manually trigger deployment in dashboard

### Disable Auto-Deploy (Optional)
1. Go to service settings
2. Click "Deployments" tab
3. Toggle "Auto Deploy" off

---

## Monitoring & Logs

### View Logs
1. Go to your service in Railway dashboard
2. Click "Logs" tab
3. View real-time logs
4. Filter by log level (info, warning, error)

### Metrics
1. Click "Metrics" tab
2. View CPU, memory, and network usage
3. Monitor request rates and response times

---

## Rollback Deployment

If a deployment fails:
1. Go to "Deployments" tab
2. Find the last working deployment
3. Click "Redeploy" on that version

---

## Environment-Specific Configurations

### Development
```bash
ENVIRONMENT=development
LOG_LEVEL=debug
ENABLE_PAPER_TRADING=true
ENABLE_REAL_TRADING=false
```

### Staging
```bash
ENVIRONMENT=staging
LOG_LEVEL=info
ENABLE_PAPER_TRADING=true
ENABLE_REAL_TRADING=false
```

### Production
```bash
ENVIRONMENT=production
LOG_LEVEL=warning
ENABLE_PAPER_TRADING=true
ENABLE_REAL_TRADING=false  # Keep false until fully tested
```

---

## Security Best Practices

1. **Never commit secrets** to GitHub
2. **Use Railway environment variables** for all sensitive data
3. **Rotate JWT_SECRET** periodically
4. **Enable HTTPS only** (Railway provides this by default)
5. **Restrict CORS_ORIGINS** to your frontend domains only
6. **Keep ENABLE_REAL_TRADING=false** until thoroughly tested
7. **Use strong encryption keys** (32+ bytes)
8. **Monitor logs** for suspicious activity

---

## Next Steps

After successful Railway deployment:

1. ✅ Backend deployed to Railway
2. ⏳ Deploy frontend to Vercel (see `VERCEL_DEPLOYMENT_GUIDE.md`)
3. ⏳ Setup Supabase for authentication (see `SUPABASE_SETUP_GUIDE.md`)
4. ⏳ Configure Better Stack monitoring
5. ⏳ Test end-to-end connectivity
6. ⏳ Initialize database schema
7. ⏳ Add API keys for exchanges

---

## Support Resources

- [Railway Documentation](https://docs.railway.app)
- [Railway Discord](https://discord.gg/railway)
- [FastAPI Documentation](https://fastapi.tiangolo.com)
- Project Documentation: `docs/INFRASTRUCTURE_DEPLOYMENT_GUIDE.md`

---

## Quick Reference

### Railway CLI (Optional)
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Link to project
railway link

# View logs
railway logs

# Run commands in Railway environment
railway run <command>

# Deploy manually
railway up
```

### Useful Commands
```bash
# Check service status
railway status

# View environment variables
railway variables

# Open service in browser
railway open

# SSH into service (if available)
railway shell
```

---

**Last Updated**: 2024
**Version**: 1.0
**Status**: Ready for deployment
