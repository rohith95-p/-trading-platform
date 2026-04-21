# Task 6.1: Railway Deployment - Quick Reference Card

## 🎯 Goal
Deploy your FastAPI backend to Railway cloud hosting.

---

## ⏱️ Time Required
**~1 hour** (manual setup, no coding)

---

## 📖 Main Guide
**START HERE**: `docs/TASK_6.1_RAILWAY_SETUP.md`

---

## 🔗 Quick Links

| Resource | URL |
|----------|-----|
| Railway | https://railway.app |
| Railway Docs | https://docs.railway.app |
| Railway Discord | https://discord.gg/railway |

---

## 🔑 Commands You'll Need

### Generate JWT Secret
```bash
# Linux/Mac
openssl rand -base64 32

# Windows PowerShell
[Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Minimum 0 -Maximum 256 }))
```

### Generate Encryption Key
```bash
# Linux/Mac
openssl rand -hex 32

# Windows PowerShell
-join ((1..32) | ForEach-Object { '{0:x2}' -f (Get-Random -Minimum 0 -Maximum 256) })
```

### Test Deployment
```bash
# Replace with your actual Railway URL
curl https://your-app.railway.app/health
```

---

## 📋 Environment Variables Checklist

### Required (you set these)
- [ ] `JWT_SECRET` (generate above)
- [ ] `JWT_ALGORITHM` = `HS256`
- [ ] `JWT_EXPIRATION_HOURS` = `24`
- [ ] `ENCRYPTION_KEY` (generate above)
- [ ] `ENABLE_PAPER_TRADING` = `true`
- [ ] `ENABLE_REAL_TRADING` = `false`
- [ ] `ENABLE_DRL_AGENT` = `true`
- [ ] `ENABLE_SIMULATION` = `true`
- [ ] `ENVIRONMENT` = `production`
- [ ] `LOG_LEVEL` = `info`
- [ ] `CORS_ORIGINS` = `http://localhost:3000`

### Auto-configured (Railway provides)
- [ ] `DATABASE_URL` (verify exists)
- [ ] `REDIS_URL` (verify exists)
- [ ] `PORT` (verify exists)

---

## ✅ Success Checklist

- [ ] Railway account created
- [ ] Project created and connected to GitHub
- [ ] PostgreSQL database added
- [ ] Redis cache added
- [ ] Environment variables configured
- [ ] Backend deployed successfully
- [ ] Health check returns 200 OK
- [ ] API docs accessible
- [ ] Railway URL saved

---

## 🧪 Verification

### Health Check
```bash
curl https://your-app.railway.app/health
```
Expected: `{"status": "healthy", "version": "1.0.0"}`

### API Docs
Visit: `https://your-app.railway.app/docs`

---

## 💰 Cost
**Free tier**: $5 credit/month
**Estimated usage**: $3-6/month
**Conclusion**: Fits within free tier ✅

---

## 🆘 Troubleshooting

| Issue | Solution |
|-------|----------|
| Deployment fails | Check build logs in Railway dashboard |
| Health check fails | Verify environment variables are set |
| Can't access API | Check service is running in Railway |
| Database errors | Verify PostgreSQL service is running |

**Full troubleshooting**: See `docs/TASK_6.1_RAILWAY_SETUP.md`

---

## 📁 Files Created for This Task

| File | Purpose |
|------|---------|
| `docs/TASK_6.1_RAILWAY_SETUP.md` | Step-by-step checklist |
| `docs/RAILWAY_DEPLOYMENT_GUIDE.md` | Detailed reference guide |
| `RAILWAY_SETUP_README.md` | Overview and introduction |
| `TASK_6.1_COMPLETE_GUIDE.md` | Complete guide with all info |
| `scripts/verify_railway_ready.py` | Pre-deployment verification |
| `.env.railway.example` | Environment variable template |

---

## 📝 What to Save

After deployment, create `RAILWAY_DEPLOYMENT_INFO.md` with:
- Railway project URL
- Backend public URL
- Deployment date
- Service status

**⚠️ Important**: This file is in `.gitignore` - don't commit secrets!

---

## 🔜 Next Steps

After Task 6.1:
1. Task 6.2: Setup Supabase
2. Task 6.3: Deploy to Vercel
3. Task 6.4: Configure environment variables
4. Task 6.5: Test connectivity

---

## 📞 Support

- **Railway**: [docs.railway.app](https://docs.railway.app)
- **Project Docs**: `docs/` folder
- **Discord**: [discord.gg/railway](https://discord.gg/railway)

---

**Ready?** Open `docs/TASK_6.1_RAILWAY_SETUP.md` and start! 🚀
