# Task 1.3: Infrastructure Deployment - Quick Checklist

## ⚠️ Important Note

This task requires **manual account creation** on three cloud platforms. All code is ready - you just need to create accounts and configure services.

**Total Time**: ~45 minutes
**Cost**: $0 (all free tiers)

---

## Quick Checklist

### 1️⃣ Railway (Backend) - 15 minutes

- [ ] Go to [railway.app](https://railway.app) and sign up with GitHub
- [ ] Create new project from this GitHub repository
- [ ] Configure build:
  - Start Command: `uvicorn src.main:app --host 0.0.0.0 --port $PORT`
  - Build Command: `pip install -r requirements.txt`
- [ ] Add environment variables:
  ```bash
  JWT_SECRET=<random-32-char-string>
  JWT_ALGORITHM=HS256
  JWT_EXPIRATION_HOURS=24
  ENABLE_PAPER_TRADING=true
  ENABLE_REAL_TRADING=false
  CORS_ORIGINS=http://localhost:3000
  ENVIRONMENT=production
  LOG_LEVEL=info
  ```
- [ ] Deploy and wait for build to complete
- [ ] Test: `curl https://[your-project].railway.app/health`
- [ ] Save Railway URL: `_______________________________`

### 2️⃣ Supabase (Database) - 15 minutes

- [ ] Go to [supabase.com](https://supabase.com) and sign up with GitHub
- [ ] Create new project named "trading-platform"
- [ ] Save database password: `_______________________________`
- [ ] Wait for database initialization (2-5 minutes)
- [ ] Go to SQL Editor and run the schema from `sql/schema.sql`
- [ ] Go to Settings → Database and copy connection string
- [ ] Go to Settings → API and copy:
  - Project URL: `_______________________________`
  - Anon Key: `_______________________________`
  - Service Role Key: `_______________________________`
- [ ] Go back to Railway and add `DATABASE_URL` variable with connection string
- [ ] Wait for Railway to redeploy

### 3️⃣ Vercel (Frontend) - 10 minutes

- [ ] Go to [vercel.com](https://vercel.com) and sign up with GitHub
- [ ] Import this GitHub repository
- [ ] Configure:
  - Project Name: `trading-platform`
  - Framework: Next.js (auto-detected)
  - Root Directory: `./frontend`
- [ ] Add environment variables:
  ```bash
  NEXT_PUBLIC_SUPABASE_URL=https://[project-id].supabase.co
  NEXT_PUBLIC_SUPABASE_ANON_KEY=[your-anon-key]
  NEXT_PUBLIC_API_URL=https://[your-railway-project].railway.app
  NEXT_PUBLIC_ENABLE_PAPER_TRADING=true
  NEXT_PUBLIC_ENABLE_REAL_TRADING=false
  ```
- [ ] Deploy and wait for build to complete
- [ ] Save Vercel URL: `_______________________________`
- [ ] Go back to Railway and update `CORS_ORIGINS`:
  ```
  CORS_ORIGINS=https://[your-vercel-url].vercel.app,http://localhost:3000
  ```

### 4️⃣ Test Connectivity - 5 minutes

- [ ] Backend health: `curl https://[railway-url]/health`
  - Expected: `{"status": "healthy", "version": "1.0.0"}`
- [ ] Frontend loads: Visit `https://[vercel-url]` in browser
  - Expected: "Trading Platform" page
- [ ] API docs: Visit `https://[railway-url]/docs`
  - Expected: Swagger UI

---

## ✅ Task Complete When:

- [ ] Railway backend accessible via HTTPS
- [ ] Supabase database accessible
- [ ] Vercel frontend accessible
- [ ] Environment variables configured
- [ ] Health check returns "healthy"
- [ ] Frontend loads successfully

---

## 📝 Save Your URLs

After deployment, save these for future reference:

```
Backend API: https://[your-project].railway.app
Frontend: https://[your-project].vercel.app
API Docs: https://[your-project].railway.app/docs
Supabase: https://[project-id].supabase.co
```

---

## 🆘 Need Help?

See detailed guide: `TASK_1_3_DEPLOYMENT_GUIDE.md`

Common issues:
- **Railway build fails**: Check `requirements.txt` and build logs
- **Vercel build fails**: Verify Root Directory is `./frontend`
- **CORS errors**: Update `CORS_ORIGINS` in Railway with Vercel URL
- **Database connection fails**: Verify `DATABASE_URL` format in Railway

---

## 📚 Resources

- [Railway Docs](https://docs.railway.app)
- [Supabase Docs](https://supabase.com/docs)
- [Vercel Docs](https://vercel.com/docs)
