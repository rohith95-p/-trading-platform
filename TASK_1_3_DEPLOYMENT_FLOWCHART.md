# Task 1.3: Infrastructure Deployment - Visual Flowchart

## Deployment Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    START: Task 1.3                          │
│              Infrastructure Deployment                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 1: Generate Secrets (2 minutes)                       │
│  ─────────────────────────────────────────────────────      │
│  Run: python scripts/generate_secrets.py                    │
│  Save: JWT_SECRET and ENCRYPTION_KEY                        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 2: Deploy Backend to Railway (15 minutes)            │
│  ─────────────────────────────────────────────────────      │
│  1. Create Railway account (railway.app)                    │
│  2. Create project from GitHub                              │
│  3. Configure build settings                                │
│  4. Add environment variables                               │
│  5. Deploy and wait for build                               │
│  6. Test: curl [railway-url]/health                         │
│  7. Save Railway URL                                        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 3: Setup Database on Supabase (15 minutes)           │
│  ─────────────────────────────────────────────────────      │
│  1. Create Supabase account (supabase.com)                  │
│  2. Create project "trading-platform"                       │
│  3. Wait for database initialization                        │
│  4. Run SQL schema from sql/schema.sql                      │
│  5. Get connection string and API keys                      │
│  6. Update Railway with DATABASE_URL                        │
│  7. Wait for Railway to redeploy                            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 4: Deploy Frontend to Vercel (10 minutes)            │
│  ─────────────────────────────────────────────────────      │
│  1. Create Vercel account (vercel.com)                      │
│  2. Import GitHub repository                                │
│  3. Set root directory to ./frontend                        │
│  4. Add environment variables                               │
│  5. Deploy and wait for build                               │
│  6. Save Vercel URL                                         │
│  7. Update Railway CORS_ORIGINS with Vercel URL            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 5: Test Connectivity (5 minutes)                      │
│  ─────────────────────────────────────────────────────      │
│  1. Test backend health: curl [railway-url]/health          │
│  2. Test frontend: Visit [vercel-url] in browser            │
│  3. Test API docs: Visit [railway-url]/docs                 │
│  4. Verify all services are accessible                      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  ✅ TASK 1.3 COMPLETE                       │
│                                                              │
│  Infrastructure deployed:                                   │
│  • Backend: Railway                                         │
│  • Database: Supabase                                       │
│  • Frontend: Vercel                                         │
│                                                              │
│  Next: Task 1.4 - Database Schema Implementation            │
└─────────────────────────────────────────────────────────────┘
```

---

## Service Dependencies

```
┌──────────────┐
│   Frontend   │
│   (Vercel)   │
└──────┬───────┘
       │ HTTPS
       │ API Calls
       ▼
┌──────────────┐         ┌──────────────┐
│   Backend    │────────▶│   Database   │
│  (Railway)   │ SQL     │  (Supabase)  │
└──────────────┘         └──────────────┘
```

---

## Environment Variables Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    Generate Secrets                          │
│  python scripts/generate_secrets.py                         │
└────────────────────────┬────────────────────────────────────┘
                         │
         ┌───────────────┴───────────────┐
         ▼                               ▼
┌─────────────────┐            ┌─────────────────┐
│     Railway     │            │     Vercel      │
│   Environment   │            │   Environment   │
│    Variables    │            │    Variables    │
├─────────────────┤            ├─────────────────┤
│ JWT_SECRET      │            │ SUPABASE_URL    │
│ ENCRYPTION_KEY  │            │ SUPABASE_KEY    │
│ DATABASE_URL ◀──┼────────┐   │ API_URL         │
│ CORS_ORIGINS ◀──┼───┐    │   └─────────────────┘
└─────────────────┘   │    │
                      │    │
                      │    └───────────────┐
                      │                    │
                      │            ┌───────▼────────┐
                      │            │    Supabase    │
                      │            │   Connection   │
                      │            │     String     │
                      │            └────────────────┘
                      │
                      └────────────────────┐
                                           │
                                   ┌───────▼────────┐
                                   │  Vercel URL    │
                                   │  (for CORS)    │
                                   └────────────────┘
```

---

## Timeline

```
Time    Activity                                Status
─────────────────────────────────────────────────────────
0:00    Generate secrets                        ⏳ To Do
0:02    Create Railway account                  ⏳ To Do
0:05    Configure Railway project               ⏳ To Do
0:10    Deploy backend to Railway               ⏳ To Do
0:15    Test backend health check               ⏳ To Do
0:17    Create Supabase account                 ⏳ To Do
0:20    Create Supabase project                 ⏳ To Do
0:25    Run SQL schema                          ⏳ To Do
0:27    Get Supabase connection details         ⏳ To Do
0:30    Update Railway with DATABASE_URL        ⏳ To Do
0:32    Create Vercel account                   ⏳ To Do
0:35    Import project to Vercel                ⏳ To Do
0:38    Configure Vercel environment            ⏳ To Do
0:40    Deploy frontend to Vercel               ⏳ To Do
0:42    Update Railway CORS                     ⏳ To Do
0:43    Test backend connectivity               ⏳ To Do
0:44    Test frontend connectivity              ⏳ To Do
0:45    Test API documentation                  ⏳ To Do
0:47    ✅ Task 1.3 Complete                    ⏳ To Do
```

---

## Decision Tree

```
                    Start Task 1.3
                          │
                          ▼
              Have Railway account?
                    ╱         ╲
                  Yes          No
                   │            │
                   │            ▼
                   │    Create Railway account
                   │            │
                   └────────────┘
                          │
                          ▼
              Have Supabase account?
                    ╱         ╲
                  Yes          No
                   │            │
                   │            ▼
                   │    Create Supabase account
                   │            │
                   └────────────┘
                          │
                          ▼
              Have Vercel account?
                    ╱         ╲
                  Yes          No
                   │            │
                   │            ▼
                   │    Create Vercel account
                   │            │
                   └────────────┘
                          │
                          ▼
                  Deploy all services
                          │
                          ▼
                  Test connectivity
                          │
                          ▼
                All tests pass?
                    ╱         ╲
                  Yes          No
                   │            │
                   │            ▼
                   │    Troubleshoot
                   │    (see guide)
                   │            │
                   └────────────┘
                          │
                          ▼
                  ✅ Task Complete
```

---

## Troubleshooting Flow

```
                    Deployment Issue?
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
    Railway Build    Vercel Build    CORS Error
        Failed          Failed
          │               │               │
          ▼               ▼               ▼
    Check build     Check root      Update CORS
    logs and        directory       in Railway
    requirements    is ./frontend   with Vercel URL
          │               │               │
          └───────────────┼───────────────┘
                          │
                          ▼
                    Try again
                          │
                          ▼
                    Still failing?
                          │
                          ▼
              Check detailed guide
              TASK_1_3_DEPLOYMENT_GUIDE.md
```

---

## Success Indicators

```
✅ Railway Backend
   │
   ├─ Health check returns {"status": "healthy"}
   ├─ API docs accessible at /docs
   └─ Environment variables configured

✅ Supabase Database
   │
   ├─ Project created and running
   ├─ Tables created successfully
   ├─ Connection string obtained
   └─ API keys obtained

✅ Vercel Frontend
   │
   ├─ Frontend loads in browser
   ├─ "Trading Platform" page displays
   └─ Environment variables configured

✅ Connectivity
   │
   ├─ Frontend can reach backend
   ├─ Backend can reach database
   └─ CORS configured correctly
```

---

## Quick Reference

| What | Where | Time |
|------|-------|------|
| Generate secrets | `python scripts/generate_secrets.py` | 2 min |
| Railway setup | [railway.app](https://railway.app) | 15 min |
| Supabase setup | [supabase.com](https://supabase.com) | 15 min |
| Vercel setup | [vercel.com](https://vercel.com) | 10 min |
| Test connectivity | `curl` commands | 5 min |
| **Total** | | **47 min** |

---

## Files to Reference

1. **Quick Start**: `TASK_1_3_QUICK_CHECKLIST.md`
2. **Detailed Guide**: `TASK_1_3_DEPLOYMENT_GUIDE.md`
3. **Summary**: `TASK_1_3_EXECUTION_SUMMARY.md`
4. **This Flowchart**: `TASK_1_3_DEPLOYMENT_FLOWCHART.md`

---

## After Completion

```
Task 1.3 Complete
       │
       ▼
Save deployment URLs
       │
       ▼
Update documentation
       │
       ▼
Proceed to Task 1.4
(Database Schema Implementation)
```
