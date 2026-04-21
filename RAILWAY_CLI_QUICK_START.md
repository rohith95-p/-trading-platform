# Railway CLI Quick Start - Task 6.1

## 🚀 Fast Track (Copy & Paste Commands)

### 1. Install Railway CLI
```powershell
npm install -g @railway/cli
```

### 2. Login
```powershell
railway login
```

### 3. Initialize Project
```powershell
cd C:\Users\Pandu\Desktop\ultra_core
railway init
# Select: Create new project → Name: trading-platform-backend → Environment: production
```

### 4. Add Databases
```powershell
railway add --plugin postgresql
railway add --plugin redis
```

### 5. Generate Keys

**JWT Secret:**
```powershell
$bytes = New-Object byte[] 32; [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes); $jwtSecret = [Convert]::ToBase64String($bytes); Write-Host "JWT_SECRET=$jwtSecret"
```

**Encryption Key:**
```powershell
$encKey = -join ((1..32) | ForEach-Object { '{0:x2}' -f (Get-Random -Minimum 0 -Maximum 256) }); Write-Host "ENCRYPTION_KEY=$encKey"
```

### 6. Set Environment Variables

**Replace `<YOUR_JWT_SECRET>` and `<YOUR_ENCRYPTION_KEY>` with values from step 5:**

```powershell
railway variables set JWT_SECRET="<YOUR_JWT_SECRET>"
railway variables set ENCRYPTION_KEY="<YOUR_ENCRYPTION_KEY>"
railway variables set JWT_ALGORITHM="HS256"
railway variables set JWT_EXPIRATION_HOURS="24"
railway variables set ENABLE_PAPER_TRADING="true"
railway variables set ENABLE_REAL_TRADING="false"
railway variables set ENABLE_DRL_AGENT="true"
railway variables set ENABLE_SIMULATION="true"
railway variables set ENVIRONMENT="production"
railway variables set LOG_LEVEL="info"
railway variables set CORS_ORIGINS="http://localhost:3000"
```

### 7. Deploy
```powershell
railway up
```

### 8. Get URL
```powershell
railway domain --generate
```

### 9. Test
```powershell
$url = railway domain
curl "$url/health"
```

**Expected:** `{"status": "healthy", "version": "1.0.0"}`

---

## ✅ Done!

Your backend is now deployed to Railway.

**Next:** Open `RAILWAY_CLI_DEPLOYMENT_GUIDE.md` for detailed instructions and troubleshooting.

---

## 🔍 Useful Commands

```powershell
railway logs              # View logs
railway status            # Check status
railway variables         # List variables
railway open              # Open dashboard
railway domain            # Show URL
```

---

**Time**: 30-45 minutes | **Cost**: Free tier | **Difficulty**: Easy
