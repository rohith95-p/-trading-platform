# Task 6.1: Railway Account and Backend Deployment

## Quick Start Checklist

This is a **manual setup task** that requires you to create accounts and configure services. Follow this checklist step-by-step.

---

## ✅ Checklist

### Part 1: Create Railway Account (5 minutes)

- [ ] Go to [railway.app](https://railway.app)
- [ ] Click "Start a New Project" or "Login"
- [ ] Sign up with GitHub (recommended)
- [ ] Verify your email address
- [ ] Confirm you can access the Railway dashboard

---

### Part 2: Create Railway Project (10 minutes)

- [ ] Click "New Project" in Railway dashboard
- [ ] Select "Deploy from GitHub repo"
- [ ] Authorize Railway to access your GitHub repositories
- [ ] Select your `ultra_core` repository (or your trading platform repo)
- [ ] Wait for Railway to detect the project

---

### Part 3: Configure Backend Service (15 minutes)

#### Service Settings
- [ ] Set service name: `trading-platform-api`
- [ ] Verify build method: Dockerfile
- [ ] Verify Dockerfile path: `Dockerfile.backend`
- [ ] Set start command: `uvicorn src.main:app --host 0.0.0.0 --port $PORT`

#### Add PostgreSQL Database
- [ ] Click "New" → "Database" → "PostgreSQL"
- [ ] Wait for provisioning (2-3 minutes)
- [ ] Verify `DATABASE_URL` is added to environment variables

#### Add Redis Cache
- [ ] Click "New" → "Database" → "Redis"
- [ ] Wait for provisioning (1-2 minutes)
- [ ] Verify `REDIS_URL` is added to environment variables

---

### Part 4: Generate Secure Keys (5 minutes)

#### Generate JWT Secret
```bash
# On Linux/Mac:
openssl rand -base64 32

# On Windows (PowerShell):
[Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Minimum 0 -Maximum 256 }))
```
- [ ] Copy the generated JWT secret
- [ ] Save it securely (you'll need it in the next step)

#### Generate Encryption Key
```bash
# On Linux/Mac:
openssl rand -hex 32

# On Windows (PowerShell):
-join ((1..32) | ForEach-Object { '{0:x2}' -f (Get-Random -Minimum 0 -Maximum 256) })
```
- [ ] Copy the generated encryption key
- [ ] Save it securely (you'll need it in the next step)

---

### Part 5: Configure Environment Variables (10 minutes)

Go to your service → Settings → Variables and add:

#### Required Variables
- [ ] `JWT_SECRET` = (paste your generated JWT secret)
- [ ] `JWT_ALGORITHM` = `HS256`
- [ ] `JWT_EXPIRATION_HOURS` = `24`
- [ ] `ENCRYPTION_KEY` = (paste your generated encryption key)
- [ ] `ENABLE_PAPER_TRADING` = `true`
- [ ] `ENABLE_REAL_TRADING` = `false`
- [ ] `ENABLE_DRL_AGENT` = `true`
- [ ] `ENABLE_SIMULATION` = `true`
- [ ] `ENVIRONMENT` = `production`
- [ ] `LOG_LEVEL` = `info`
- [ ] `CORS_ORIGINS` = `http://localhost:3000`

#### Auto-Generated (verify these exist)
- [ ] `DATABASE_URL` (should be auto-added by Railway)
- [ ] `REDIS_URL` (should be auto-added by Railway)
- [ ] `PORT` (should be auto-added by Railway)

---

### Part 6: Deploy Backend (5 minutes)

- [ ] Railway automatically deploys when environment variables are set
- [ ] Monitor deployment in Railway dashboard
- [ ] Check deployment logs for errors
- [ ] Wait for "Deployment successful" message
- [ ] Note the deployment time (usually 2-5 minutes)

---

### Part 7: Get Public URL (2 minutes)

- [ ] Go to service Settings → Domains
- [ ] Copy the Railway-provided URL (e.g., `trading-platform-api-production.railway.app`)
- [ ] Save this URL (you'll need it for frontend configuration)

---

### Part 8: Verify Deployment (5 minutes)

#### Test Health Endpoint
```bash
curl https://your-app.railway.app/health
```
- [ ] Run the curl command (replace with your actual URL)
- [ ] Verify response contains `"status": "healthy"`
- [ ] Verify response contains `"version": "1.0.0"`

#### Test Root Endpoint
```bash
curl https://your-app.railway.app/
```
- [ ] Run the curl command
- [ ] Verify response contains `"name": "Unified Trading Intelligence Platform"`

#### Access API Documentation
- [ ] Visit `https://your-app.railway.app/docs` in browser
- [ ] Verify Swagger UI loads correctly
- [ ] Browse available endpoints

---

### Part 9: Document Your Deployment (5 minutes)

Create a file to save your deployment information:

- [ ] Create `RAILWAY_DEPLOYMENT_INFO.md` in project root
- [ ] Save Railway project URL
- [ ] Save backend public URL
- [ ] Save database connection info (keep secure!)
- [ ] Save Redis connection info (keep secure!)
- [ ] Save generated JWT secret (keep secure!)
- [ ] Save generated encryption key (keep secure!)

**Template:**
```markdown
# Railway Deployment Information

## Project Details
- Railway Project: https://railway.app/project/[your-project-id]
- Backend URL: https://[your-app].railway.app
- Deployment Date: [date]

## Services
- Backend: trading-platform-api
- Database: PostgreSQL 15
- Cache: Redis 7

## Environment Variables (Configured)
- JWT_SECRET: ✅ Set
- ENCRYPTION_KEY: ✅ Set
- DATABASE_URL: ✅ Auto-configured
- REDIS_URL: ✅ Auto-configured
- CORS_ORIGINS: ✅ Set

## Status
- Deployment: ✅ Successful
- Health Check: ✅ Passing
- API Docs: ✅ Accessible
```

---

## ⚠️ Important Notes

### Security
- **NEVER commit** `RAILWAY_DEPLOYMENT_INFO.md` to GitHub if it contains secrets
- Add it to `.gitignore` immediately
- Store secrets in a password manager

### Cost
- Railway free tier: $5 credit/month
- Estimated usage: $3-6/month
- Monitor usage in Railway dashboard

### Next Steps
After completing this task:
1. ✅ Task 6.1 complete
2. ⏳ Task 6.2: Setup Supabase database
3. ⏳ Task 6.3: Deploy frontend to Vercel
4. ⏳ Task 6.4: Configure environment variables
5. ⏳ Task 6.5: Test connectivity

---

## Troubleshooting

### Deployment Fails
- Check build logs in Railway dashboard
- Verify `Dockerfile.backend` exists in repository
- Ensure all files are committed and pushed to GitHub

### Health Check Fails
- Check runtime logs in Railway dashboard
- Verify environment variables are set correctly
- Ensure DATABASE_URL and REDIS_URL are accessible

### Can't Access API Docs
- Verify deployment is successful
- Check if service is running in Railway dashboard
- Try accessing `/health` endpoint first

### Database Connection Errors
- Verify PostgreSQL service is running
- Check DATABASE_URL format is correct
- Ensure database is provisioned (check Railway dashboard)

---

## Support

If you encounter issues:
1. Check Railway deployment logs
2. Review `docs/RAILWAY_DEPLOYMENT_GUIDE.md` for detailed instructions
3. Visit [Railway Documentation](https://docs.railway.app)
4. Ask in [Railway Discord](https://discord.gg/railway)

---

## Completion Criteria

Task 6.1 is complete when:
- ✅ Railway account created
- ✅ Railway project created
- ✅ Backend service configured
- ✅ PostgreSQL database added
- ✅ Redis cache added
- ✅ Environment variables set
- ✅ Backend deployed successfully
- ✅ Health check endpoint returns 200 OK
- ✅ API documentation accessible
- ✅ Deployment info documented

---

**Estimated Time**: 1 hour
**Difficulty**: Easy (mostly point-and-click)
**Prerequisites**: GitHub account, backend code in repository

**Status**: Ready to execute
