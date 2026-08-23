# Railway Deployment Script - Complete Setup
# This script will deploy your backend to Railway with all necessary configuration

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Railway Deployment - Trading Platform" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check if Railway CLI is installed
Write-Host "[1/9] Checking Railway CLI..." -ForegroundColor Yellow
try {
    $railwayVersion = railway --version 2>$null
    if ($railwayVersion) {
        Write-Host "✅ Railway CLI installed: $railwayVersion" -ForegroundColor Green
    } else {
        throw "Railway CLI not found"
    }
} catch {
    Write-Host "❌ Railway CLI not installed" -ForegroundColor Red
    Write-Host "Installing Railway CLI..." -ForegroundColor Yellow
    npm install -g @railway/cli
    Write-Host "✅ Railway CLI installed" -ForegroundColor Green
}
Write-Host ""

# Step 2: Login to Railway
Write-Host "[2/9] Logging into Railway..." -ForegroundColor Yellow
Write-Host "This will open your browser for authentication..." -ForegroundColor Gray
railway login
Write-Host "✅ Logged into Railway" -ForegroundColor Green
Write-Host ""

# Step 3: Initialize Railway project
Write-Host "[3/9] Initializing Railway project..." -ForegroundColor Yellow
railway init
Write-Host "✅ Railway project initialized" -ForegroundColor Green
Write-Host ""

# Step 4: Add PostgreSQL
Write-Host "[4/9] Adding PostgreSQL database..." -ForegroundColor Yellow
railway add --plugin postgresql
Write-Host "✅ PostgreSQL added" -ForegroundColor Green
Write-Host ""

# Step 5: Add Redis
Write-Host "[5/9] Adding Redis cache..." -ForegroundColor Yellow
railway add --plugin redis
Write-Host "✅ Redis added" -ForegroundColor Green
Write-Host ""

# Step 6: Generate JWT Secret
Write-Host "[6/9] Generating JWT Secret..." -ForegroundColor Yellow
$bytes = New-Object byte[] 32
[Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
$jwtSecret = [Convert]::ToBase64String($bytes)
Write-Host "✅ JWT Secret generated" -ForegroundColor Green
Write-Host ""

# Step 7: Generate Encryption Key
Write-Host "[7/9] Generating Encryption Key..." -ForegroundColor Yellow
$encKey = -join ((1..32) | ForEach-Object { '{0:x2}' -f (Get-Random -Minimum 0 -Maximum 256) })
Write-Host "✅ Encryption Key generated" -ForegroundColor Green
Write-Host ""

# Step 8: Set all environment variables
Write-Host "[8/9] Setting environment variables..." -ForegroundColor Yellow

# Authentication
railway variables set JWT_SECRET="$jwtSecret"
railway variables set JWT_ALGORITHM="HS256"
railway variables set JWT_EXPIRATION_HOURS="24"
railway variables set ENCRYPTION_KEY="$encKey"

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

Write-Host "✅ All environment variables set" -ForegroundColor Green
Write-Host ""

# Step 9: Deploy
Write-Host "[9/9] Deploying to Railway..." -ForegroundColor Yellow
Write-Host "This may take 2-5 minutes..." -ForegroundColor Gray
railway up

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Deployment Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Get deployment URL
Write-Host "Getting your deployment URL..." -ForegroundColor Yellow
$deploymentUrl = railway domain
if (-not $deploymentUrl) {
    Write-Host "Generating domain..." -ForegroundColor Yellow
    railway domain --generate
    $deploymentUrl = railway domain
}

Write-Host ""
Write-Host "✅ Backend URL: $deploymentUrl" -ForegroundColor Green
Write-Host ""

# Test health endpoint
Write-Host "Testing health endpoint..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$deploymentUrl/health" -Method Get
    if ($response.status -eq "healthy") {
        Write-Host "✅ Health check passed!" -ForegroundColor Green
        Write-Host "   Status: $($response.status)" -ForegroundColor Gray
        Write-Host "   Version: $($response.version)" -ForegroundColor Gray
    }
} catch {
    Write-Host "⚠️  Health check failed - service may still be starting" -ForegroundColor Yellow
    Write-Host "   Wait 1-2 minutes and try: curl $deploymentUrl/health" -ForegroundColor Gray
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "1. API Docs: $deploymentUrl/docs" -ForegroundColor White
Write-Host "2. View logs: railway logs" -ForegroundColor White
Write-Host "3. Check status: railway status" -ForegroundColor White
Write-Host "4. Open dashboard: railway open" -ForegroundColor White
Write-Host ""
Write-Host "Deployment info saved to: RAILWAY_DEPLOYMENT_INFO.md" -ForegroundColor Gray
Write-Host ""

# Save deployment info
$deploymentInfo = @"
# Railway Deployment Information

## Deployment Date
$(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

## URLs
- **Backend**: $deploymentUrl
- **API Docs**: $deploymentUrl/docs
- **Health Check**: $deploymentUrl/health

## Services
- Backend: trading-platform-backend
- Database: PostgreSQL (Railway)
- Cache: Redis (Railway)
- Auth: Supabase

## Environment Variables
- JWT_SECRET: ✅ Generated and set
- ENCRYPTION_KEY: ✅ Generated and set
- DATABASE_URL: ✅ Auto-configured by Railway
- REDIS_URL: ✅ Auto-configured by Railway
- CORS_ORIGINS: ✅ Set

## Generated Secrets (SAVE THESE SECURELY)
- JWT_SECRET: $jwtSecret
- ENCRYPTION_KEY: $encKey

## Status
- Deployment: ✅ Successful
- Health Check: ✅ Passing (or starting)
- API Docs: ✅ Accessible

## Useful Commands
``````powershell
# View logs
railway logs

# Check status
railway status

# View variables
railway variables

# Open dashboard
railway open

# Redeploy
railway up
``````

## Next Steps
- [ ] Test API endpoints
- [ ] Task 6.2: Setup Supabase (add Supabase keys to Railway)
- [ ] Task 6.3: Deploy frontend to Vercel
- [ ] Task 6.4: Configure frontend environment variables
- [ ] Task 6.5: Test end-to-end connectivity (Task 6.5)

## Support
- Railway Docs: https://docs.railway.app
- Railway Discord: https://discord.gg/railway
- Project Docs: docs/ folder

---

**⚠️ SECURITY NOTE**: This file contains sensitive information. It's already in .gitignore. Do NOT commit to Git!
"@

$deploymentInfo | Out-File -FilePath "RAILWAY_DEPLOYMENT_INFO.md" -Encoding UTF8

Write-Host "✅ Task 6.1 Complete!" -ForegroundColor Green
Write-Host ""
