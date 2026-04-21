# 🚨 URGENT: Supabase Keys Rotation Guide

## ⚠️ Your Keys Were Exposed

Your Supabase API keys were posted publicly and need to be rotated immediately.

---

## 🔄 Step 1: Rotate Keys (5 minutes)

### Go to Supabase Dashboard

1. Visit [app.supabase.com](https://app.supabase.com)
2. Login to your account
3. Select your project

### Reset API Keys

1. Click **Settings** (gear icon in sidebar)
2. Click **API** section
3. Scroll to **Project API keys**
4. Click **"Reset API key"** or **"Regenerate"** for:
   - **anon (public) key**
   - **service_role (secret) key**
5. Copy the new keys immediately

---

## 📝 Step 2: Update Local Environment

### Update `.env.local` file

Replace the old keys with new ones:

```bash
# Supabase Configuration
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_ANON_KEY=<paste-new-anon-key-here>
SUPABASE_SERVICE_KEY=<paste-new-service-key-here>
```

**Important**: 
- Get your project URL from Supabase Dashboard → Settings → API → Project URL
- The anon key is safe for frontend use
- The service_role key is SECRET - never expose it

---

## 🚀 Step 3: Update Railway Environment Variables

If you've already deployed to Railway, update the variables:

```powershell
railway variables set SUPABASE_URL="https://your-project-ref.supabase.co"
railway variables set SUPABASE_ANON_KEY="<new-anon-key>"
railway variables set SUPABASE_SERVICE_KEY="<new-service-key>"
```

---

## 🔒 Step 4: Security Best Practices

### Never Do This:
- ❌ Post keys in chat/messages
- ❌ Commit keys to Git
- ❌ Share keys in screenshots
- ❌ Email keys in plain text
- ❌ Store keys in code files

### Always Do This:
- ✅ Use `.env` files (gitignored)
- ✅ Use environment variables
- ✅ Store in password manager
- ✅ Rotate keys if exposed
- ✅ Use different keys for dev/prod

---

## 📋 Exposed Keys (DO NOT USE)

These keys were exposed and should be rotated:

```
Anon Key (exposed): sb_publishable_sPxOxoc7iTEU5zlgul1s4g_-5tTEyfE
Service Key (exposed): sb_secret_nmA8cHlNYvY2a0Bfnb9I_Q_PlGikNK4
```

**Status**: ⚠️ COMPROMISED - Rotate immediately

---

## ✅ Verification

After rotation, verify new keys work:

```powershell
# Test with curl (replace with your actual URL and new anon key)
curl "https://your-project-ref.supabase.co/rest/v1/" `
  -H "apikey: <new-anon-key>" `
  -H "Authorization: Bearer <new-anon-key>"
```

Expected: 200 OK response

---

## 🔜 Next Steps

After rotating keys:

1. ✅ Update `.env.local` with new keys
2. ✅ Update Railway variables (if deployed)
3. ✅ Test connection to Supabase
4. ✅ Continue with Task 6.2 (Supabase setup)
5. ✅ Never expose keys again

---

## 📞 Support

If you need help:
- [Supabase Docs](https://supabase.com/docs)
- [Supabase Discord](https://discord.supabase.com)
- [Security Best Practices](https://supabase.com/docs/guides/api/api-keys)

---

**Priority**: 🚨 URGENT - Rotate keys immediately
**Time Required**: 5 minutes
**Difficulty**: Easy
