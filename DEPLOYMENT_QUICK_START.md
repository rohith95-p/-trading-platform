# Infrastructure Deployment - Quick Start Guide

## 5-Minute Overview

Task 1.3 requires deploying the trading platform to three free-tier services:

1. **Railway** - Backend (Python FastAPI)
2. **Supabase** - Database (PostgreSQL)
3. **Vercel** - Frontend (Next.js)

All code is ready. You just need to create accounts and configure services.

---

## Quick Checklist

### Phase 1: Railway Backend (15 minutes)

```bash
# 1. Go to railway.app and create account
# 2. Create new project from GitHub
# 3. Add environment variables (see .env.railway.example)
# 4. Deploy
# 5. Test: curl https://trading-platform-api-production.railway.app/health
```

### Phase 2: Supabase Database (15 minutes)

```bash
# 1. Go to supabase.com and create account
# 2. Create new project
# 3. Copy connection string
# 4. Run SQL from sql/schema.sql in SQL Editor
# 5. Get API keys from Settings → API
```

### Phase 3: Vercel Frontend (10 minutes)

```bash
# 1. Go to vercel.com and create account
# 2. Import GitHub repository
# 3. Add environment variables (see .env.vercel.example)
# 4. Deploy
# 5. Visit https://trading-platform.vercel.app
```

### Phase 4: Test Connectivity (5 minutes)

```bash
# Test backend
curl https://trading-platform-api-production.railway.app/health

# Test frontend
curl https://trading-platform.vercel.app

# Test frontend → backend
curl https://trading-platform.vercel.app/api/test
```

---

## Key URLs

Once deployed, you'll have:

- **Backend API**: `https://trading-platform-api-production.railway.app`
- **Frontend**: `https://trading-platform.vercel.app`
- **Database**: Supabase PostgreSQL (connection string in Railway)

---

## Environment Variables

### Railway (Backend)

Copy from `.env.railway.example` and fill in:
- `DATABASE_URL` - From Supabase
- `JWT_SECRET` - Generate random string
- `ANTHROPIC_API_KEY` - From Anthropic
- `ALPACA_API_KEY` - From Alpaca
- etc.

### Vercel (Frontend)

Copy from `.env.vercel.example` and fill in:
- `NEXT_PUBLIC_SUPABASE_URL` - From Supabase
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` - From Supabase
- `NEXT_PUBLIC_API_URL` - Railway backend URL

---

## Troubleshooting

### Backend won't deploy
- Check build logs in Railway dashboard
- Verify `requirements.txt` has all dependencies
- Verify environment variables are set

### Frontend won't deploy
- Check build logs in Vercel dashboard
- Verify `package.json` has all dependencies
- Verify environment variables are set

### Can't connect frontend to backend
- Verify `CORS_ORIGINS` in Railway includes Vercel URL
- Verify `NEXT_PUBLIC_API_URL` in Vercel is correct
- Check browser console for specific errors

### Database connection failed
- Verify `DATABASE_URL` is correct in Railway
- Check Supabase project is running
- Test connection locally first

---

## Files Provided

- `INFRASTRUCTURE_DEPLOYMENT_MANUAL.md` - Detailed step-by-step guide
- `DEPLOYMENT_CHECKLIST_TASK_1_3.md` - Complete checklist
- `sql/schema.sql` - Database schema
- `.env.railway.example` - Railway environment variables template
- `.env.vercel.example` - Vercel environment variables template
- `Dockerfile.backend` - Backend Docker configuration
- `requirements.txt` - Python dependencies
- `frontend/package.json` - Node.js dependencies

---

## Next Steps

1. Follow the detailed guide in `INFRASTRUCTURE_DEPLOYMENT_MANUAL.md`
2. Use the checklist in `DEPLOYMENT_CHECKLIST_TASK_1_3.md` to track progress
3. Once deployed, proceed to Task 1.4 (Database Schema Implementation)

---

## Support

For detailed instructions, see:
- `INFRASTRUCTURE_DEPLOYMENT_MANUAL.md` - Complete guide with all steps
- `DEPLOYMENT_CHECKLIST_TASK_1_3.md` - Detailed checklist for each sub-task

For documentation:
- [Railway Docs](https://docs.railway.app)
- [Supabase Docs](https://supabase.com/docs)
- [Vercel Docs](https://vercel.com/docs)

