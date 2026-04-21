# Railway CLI Deployment Guide - Task 6.1

## 🎯 Goal
Deploy your backend to Railway using CLI (no GitHub push needed)

---

## ⏱️ Time Required
**30-45 minutes**

---

## 📋 Prerequisites

- [ ] Node.js installed (for Railway CLI)
- [ ] Railway account (create at railway.app)
- [ ] Backend code ready (✅ already done)

---

## 🚀 Step-by-Step Instructions

### Step 1: Install Railway CLI (5 minutes)

Open PowerShell and run:

```powershell
npm install -g @railway/cli
```

**Verify installation:**
```powershell
railway --version
```

Expected output: `railway version X.X.X`

---

### Step 2: Create Railway Account (5 minutes)

1. Go to [railway.app](https://railway.app)
2. Click "Start a New Project" or "Login"
3. Sign up with GitHub (recommended) or email
4. Verify your email address
5. Return to your terminal

---

### Step 3: Login to Railway (2 minutes)

```powershell
railway login
```

This will:
- Open your browser
- Ask you to authorize the CLI
- Return you to the terminal when done

**Verify login:**
```powershell
railway whoami
```

---

### Step 4: Initialize Railway Project (3 minutes)

In your `ultra_core` directory:

```powershell
cd C:\Users\Pandu\Desktop\ultra_core
railway init
```

You'll be prompted:
- **Create new project or link existing?** → Select "Create new project"
- **Project name?** → Enter: `trading-platform-backend`
- **Environment?** → Select "production"

This creates a `railway.json` file in your project.

---

### Step 5: Add PostgreSQL Database (2 minutes)

```powershell
railway add --plugin postgresql
```

Railway will:
- Provision a PostgreSQL database
- Auto-generate `DATABASE_URL` environment variable
- Link it to your project

**Verify:**
```powershell
railway variables
```

You should see `DATABASE_URL` listed.

---

### Step 6: Add Redis Cache (2 minutes)

```powershell
railway add --plugin redis
```

Railway will:
- Provision a Redis instance
- Auto-generate `REDIS_URL` environment variable
- Link it to your project

**Verify:**
```powershell
railway variables
```

You should see both `DATABASE_URL` and `REDIS_URL`.

---

### Step 7: Generate Secure Keys (5 minutes)

#### Generate JWT Secret

**PowerShell:**
```powershell
$bytes = New-Object byte[] 32
[Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
$jwtSecret = [Convert]::ToBase64String($bytes)
Write-Host "JWT_SECRET=$jwtSecret"
```

**Copy the output** (you'll need it in the next step)

#### Generate Encryption Key

**PowerShell:**
```powershell
$encKey = -join ((1..32) | ForEach-Object { '{0:x2}' -f (Get-Random -Minimum 0 -Maximum 256) })
Write-Host "ENCRYPTION_KEY=$encKey"
```

**Copy the output** (you'll need it in the next step)

---

### Step 8: Set Environment Variables (10 minutes)

Set all required environment variables:

```powershell
# Authentication (use your generated values from Step 7)
railway variables set JWT_SECRET="<paste-your-jwt-secret-here>"
railway variables set ENCRYPTION_KEY="<paste-your-encryption-key-here>"
railway variables set JWT_ALGORITHM="HS256"
railway variables set JWT_EXPIRATION_HOURS="24"

# Feature Flags
railway variables set ENABLE_PAPER_TRADING="true"
railway variables set ENABLE_REAL_TRADING="false"
railway variables set ENABLE_DRL_AGENT="true"
railway variables set ENABLE_SIMULATION="true"

# Environment
railway variables set ENVIRONMENT="production"
railway variables set LOG_LEVEL="info"

# CORS (update after frontend deployment)
railway variables set CORS_ORIGINS="http://localhost:3000"
```

**Verify all variables are set:**
```powershell
railway variables
```

---

### Step 9: Deploy Backend (5 minutes)

Deploy your backend to Railway:

```powershell
railway up
```

This will:
- Package your local files
- Upload to Railway
- Build using Dockerfile.backend
- Start the service
- Show deployment logs

**Watch the deployment:**
- Look for "Build successful"
- Look for "Deployment live"
- Note any errors in the logs

**Deployment typically takes 2-5 minutes.**

---

### Step 10: Get Your Public URL (2 minutes)

After deployment completes:

```powershell
railway domain
```

If no domain exists, create one:

```powershell
railway domain --generate
```

This generates a URL like: `trading-platform-backend-production.up.railway.app`

**Save this URL!** You'll need it for:
- Frontend configuration
- API testing
- Task 6.1 completion

---

### Step 11: Verify Deployment (5 minutes)

#### Test Health Endpoint

```powershell
$url = railway domain
curl "$url/health"
```

**Expected response:**
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

#### Test Root Endpoint

```powershell
curl "$url/"
```

**Expected response:**
```json
{
  "name": "Unified Trading Intelligence Platform",
  "version": "1.0.0",
  "docs": "/docs"
}
```

#### Access API Documentation

Open in browser:
```
https://your-app.up.railway.app/docs
```

You should see Swagger UI with all API endpoints.

---

### Step 12: Document Your Deployment (3 minutes)

Create a file to save your deployment info:

```powershell
# Create deployment info file
@"
# Railway Deployment Information

## Project Details
- Railway Project: $(railway status --json | ConvertFrom-Json | Select-Object -ExpandProperty projectId)
- Backend URL: $(railway domain)
- Deployment Date: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

## Services
- Backend: trading-platform-backend
- Database: PostgreSQL (Railway)
- Cache: Redis (Railway)

## Environment Variables
- JWT_SECRET: ✅ Set
- ENCRYPTION_KEY: ✅ Set
- DATABASE_URL: ✅ Auto-configured
- REDIS_URL: ✅ Auto-configured
- CORS_ORIGINS: ✅ Set

## Status
- Deployment: ✅ Successful
- Health Check: ✅ Passing
- API Docs: ✅ Accessible

## Next Steps
- [ ] Task 6.2: Setup Supabase
- [ ] Task 6.3: Deploy frontend to Vercel
- [ ] Task 6.4: Configure environment variables
- [ ] Task 6.5: Test connectivity
"@ | Out-File -FilePath "RAILWAY_DEPLOYMENT_INFO.md" -Encoding UTF8

Write-Host "✅ Deployment info saved to RAILWAY_DEPLOYMENT_INFO.md"
```

---

## 🎉 Success Checklist

Task 6.1 is complete when:

- [x] Railway CLI installed
- [x] Railway account created
- [x] Logged into Railway CLI
- [x] Railway project initialized
- [x] PostgreSQL database added
- [x] Redis cache added
- [x] JWT secret generated and set
- [x] Encryption key generated and set
- [x] All environment variables configured
- [x] Backend deployed successfully
- [x] Public URL generated
- [x] Health check returns 200 OK
- [x] API documentation accessible
- [x] Deployment info documented

---

## 🆘 Troubleshooting

### Railway CLI Not Found
```powershell
# Reinstall Railway CLI
npm install -g @railway/cli --force
```

### Login Fails
```powershell
# Clear Railway config and try again
Remove-Item -Path "$env:USERPROFILE\.railway" -Recurse -Force
railway login
```

### Deployment Fails
```powershell
# Check deployment logs
railway logs

# Common issues:
# 1. Missing Dockerfile.backend → Verify file exists
# 2. Missing requirements.txt → Verify file exists
# 3. Build errors → Check logs for specific error
```

### Health Check Fails
```powershell
# Check service logs
railway logs --tail 100

# Verify environment variables
railway variables

# Common issues:
# 1. DATABASE_URL not set → Run: railway add --plugin postgresql
# 2. REDIS_URL not set → Run: railway add --plugin redis
# 3. Missing JWT_SECRET → Set it again
```

### Can't Access API Docs
```powershell
# Verify service is running
railway status

# Check if domain is generated
railway domain

# If no domain, generate one
railway domain --generate
```

---

## 💰 Cost Information

### Railway Free Tier
- **$5 credit per month** (free)
- Includes:
  - Backend hosting
  - PostgreSQL database
  - Redis cache
  - Custom domains
  - 512 MB RAM per service
  - Shared CPU

### Estimated Monthly Cost
- Backend service: ~$2-3/month
- PostgreSQL: ~$1-2/month
- Redis: ~$0.50-1/month
- **Total**: ~$3.50-6/month

**Fits within free tier ✅**

---

## 🔧 Useful Railway CLI Commands

### View Logs
```powershell
railway logs
railway logs --tail 50  # Last 50 lines
railway logs --follow   # Live logs
```

### Check Status
```powershell
railway status
```

### View Variables
```powershell
railway variables
```

### Open in Browser
```powershell
railway open  # Opens Railway dashboard
```

### Redeploy
```powershell
railway up
```

### Link to Different Project
```powershell
railway link
```

### Unlink Project
```powershell
railway unlink
```

---

## 🔜 Next Steps

After completing Task 6.1:

1. **Task 6.2**: Setup Supabase database
2. **Task 6.3**: Deploy frontend to Vercel
3. **Task 6.4**: Configure environment variables across services
4. **Task 6.5**: Test connectivity between all services

---

## 📞 Support Resources

- **Railway CLI Docs**: [docs.railway.app/develop/cli](https://docs.railway.app/develop/cli)
- **Railway Discord**: [discord.gg/railway](https://discord.gg/railway)
- **Railway Status**: [status.railway.app](https://status.railway.app)
- **Project Docs**: `docs/` folder

---

## ✅ Completion Criteria

Mark Task 6.1 as complete when:

1. ✅ Railway CLI installed and working
2. ✅ Railway project created and deployed
3. ✅ PostgreSQL and Redis added
4. ✅ All environment variables set
5. ✅ Backend accessible via public URL
6. ✅ Health check endpoint returns 200 OK
7. ✅ API documentation accessible
8. ✅ Deployment info saved to `RAILWAY_DEPLOYMENT_INFO.md`

---

**Ready to start?** Follow the steps above in order! 🚀

**Estimated Total Time**: 30-45 minutes
**Difficulty**: Easy (mostly CLI commands)
**Cost**: Free (Railway free tier)
