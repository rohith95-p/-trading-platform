# Deployment Guide

## Frontend Deployment to Vercel

### Prerequisites
1. Vercel account at https://vercel.com
2. GitHub account (recommended for CI/CD)

### Steps

#### Option 1: Deploy via Vercel CLI
```bash
cd frontend
npm install -g vercel
vercel login
vercel --prod
```

#### Option 2: Deploy via GitHub
1. Push code to GitHub repository
2. Go to https://vercel.com/new
3. Import repository
4. Configure:
   - Framework Preset: Next.js
   - Root Directory: ./frontend
   - Environment Variables:
     - `NEXT_PUBLIC_API_URL`: https://ultracore-api.up.railway.app

### Environment Variables (Vercel)

| Variable | Value |
|----------|-------|
| NEXT_PUBLIC_API_URL | https://ultracore-api.up.railway.app |

### Custom Domain (Optional)
1. Go to Vercel Dashboard → Settings → Domains
2. Add custom domain (e.g., ultracore.com)
3. Update DNS records

---

## Backend Deployment to Railway

### Railway Setup
1. Go to https://railway.xyz/new
2. Connect GitHub repository
3. Select `main` branch
4. Configure environment variables:

### Required Environment Variables (Railway)

```bash
# Database
DATABASE_URL=postgresql://user:password@host:5432/db

# Redis
REDIS_URL=redis://localhost:6379

# JWT
JWT_SECRET=<generate-secure-random-string>
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Encryption
ENCRYPTION_KEY=<generate-32-byte-key>

# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=xxx
SUPABASE_SERVICE_KEY=xxx

# Stripe (for billing)
STRIPE_SECRET_KEY=sk_live_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx

# OAuth (optional)
GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=xxx
GITHUB_CLIENT_ID=xxx
GITHUB_CLIENT_SECRET=xxx
```

### Generate Secure Keys
```bash
# JWT Secret
openssl rand -hex 32

# Encryption Key
openssl rand -hex 32
```

---

## OAuth Setup

### Google OAuth
1. Go to https://console.cloud.google.com
2. Create project or select existing
3. APIs & Services → Credentials → Create Credentials → OAuth Client ID
4. Set authorized redirect URI:
   ```
   https://ultracore-api.up.railway.app/auth/oauth/callback/google
   ```
5. Copy Client ID and Secret to Railway

### GitHub OAuth
1. Go to https://github.com/settings/developers
2. New OAuth App
3. Set:
   - Homepage URL: https://your-domain.com
   - Authorization callback URL:
     ```
     https://ultracore-api.up.railway.app/auth/oauth/callback/github
     ```
4. Copy Client ID and Secret to Railway

---

## Stripe Setup

### Create Stripe Products
1. Go to https://dashboard.stripe.com/products
2. Create products with prices:
   - Free Tier: $0/month
   - Pro Tier: $20/month

### Get Price IDs
```
price_xxx (Free)
price_yyy (Pro - $20/month)
```

Add to Railway environment variables.

---

## Testing Deployment

### Test Frontend
```bash
cd frontend
vercel dev  # Local development
```

### Test Backend
```bash
cd ..
uvicorn src.main:app --reload
```

### Health Check
- Frontend: https://your-frontend.vercel.app
- Backend: https://ultracore-api.up.railway.app/health

---

## Troubleshooting

### CORS Errors
1. Check CORS_ORIGINS in config.py
2. Add frontend domain to whitelist
3. Verify API_BASE_URL is correct

### Auth Issues
1. Check JWT_SECRET is set
2. Verify Supabase keys are correct
3. Check token expiration settings

### WebSocket Issues
1. Verify Redis URL is correct
2. Check WebSocket manager initialization
3. Check Railway WebSocket support

---

## Post-Deployment Checklist

- [ ] Frontend deployed to Vercel
- [ ] Backend health check passes
- [ ] CORS configured correctly
- [ ] OAuth providers configured
- [ ] Stripe webhook verified
- [ ] DNS configured (if custom domain)
- [ ] SSL certificate active
- [ ] Test user registration
- [ ] Test user login
- [ ] Test dashboard access