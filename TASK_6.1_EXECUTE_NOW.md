# Task 6.1 - Execute Now

## 🎯 Your Mission

Deploy your backend to Railway using the automated script.

---

## 🚀 Single Command

Open PowerShell in `C:\Users\Pandu\Desktop\ultra_core` and run:

```powershell
.\DEPLOY_TO_RAILWAY.ps1
```

---

## ⏱️ Timeline

- **Step 1-2**: Railway CLI install & login (1 min)
- **Step 3-5**: Project setup & databases (2 min)
- **Step 6-8**: Generate keys & set variables (1 min)
- **Step 9**: Deploy (2-5 min)
- **Total**: 6-9 minutes

---

## 👀 What You'll See

```
========================================
Railway Deployment - Trading Platform
========================================

[1/9] Checking Railway CLI...
✅ Railway CLI installed

[2/9] Logging into Railway...
✅ Logged into Railway

[3/9] Initializing Railway project...
✅ Railway project initialized

[4/9] Adding PostgreSQL database...
✅ PostgreSQL added

[5/9] Adding Redis cache...
✅ Redis added

[6/9] Generating JWT Secret...
✅ JWT Secret generated

[7/9] Generating Encryption Key...
✅ Encryption Key generated

[8/9] Setting environment variables...
✅ All environment variables set

[9/9] Deploying to Railway...
✅ Deployment Complete!

========================================
Deployment Complete!
========================================

✅ Backend URL: https://your-app.up.railway.app
✅ Health check passed!
```

---

## ✅ Success Indicators

After deployment, you should have:

1. ✅ Railway project created
2. ✅ PostgreSQL database running
3. ✅ Redis cache running
4. ✅ Backend deployed and accessible
5. ✅ Health endpoint returning: `{"status": "healthy", "version": "1.0.0"}`
6. ✅ API docs at: `https://your-app.up.railway.app/docs`
7. ✅ Deployment info saved to: `RAILWAY_DEPLOYMENT_INFO.md`

---

## 🆘 If Something Goes Wrong

### Railway CLI not found
```powershell
npm install -g @railway/cli
```

### Login fails
```powershell
railway login
```

### Deployment fails
```powershell
railway logs
railway status
```

### Need help
- Check logs: `railway logs`
- Check status: `railway status`
- Open dashboard: `railway open`

---

## 📋 After Deployment

### 1. Verify Health Check
```powershell
$url = railway domain
curl "$url/health"
```

Expected: `{"status": "healthy", "version": "1.0.0"}`

### 2. Check API Docs
Open in browser: `https://your-app.up.railway.app/docs`

### 3. Save Your URL
Copy the Railway URL - you'll need it for frontend configuration.

---

## 🔜 After Task 6.1 Completes

Tell me:
1. ✅ "Deployment successful"
2. 🔗 Your Railway URL
3. ✅ Health check status

Then I'll:
1. Mark Task 6.1 as complete
2. Move to Task 6.2 (Supabase setup)
3. Continue with remaining tasks

---

## 💡 Quick Commands Reference

```powershell
# View logs
railway logs

# Check status
railway status

# View variables
railway variables

# Open dashboard
railway open

# Show URL
railway domain

# Redeploy
railway up
```

---

**Ready?** Run: `.\DEPLOY_TO_RAILWAY.ps1`

**Time**: 6-9 minutes  
**Difficulty**: Easy (automated)  
**Status**: Waiting for you to execute ⏳
