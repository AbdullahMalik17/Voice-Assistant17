# 🚀 Production Deployment Guide

Complete guide to deploy Voice Assistant with Supabase authentication to production.

**Stack:**
- Frontend: Vercel (Next.js)
- Backend: Render (FastAPI)
- Database: Supabase (PostgreSQL)
- Authentication: Supabase Auth + NextAuth.js

---

## 📋 Pre-Deployment Checklist

Before deploying, ensure you have:
- [ ] Supabase account (free tier works)
- [ ] Vercel account (free tier works)
- [ ] Render account (free tier works)
- [ ] GitHub repository with your code
- [ ] All API keys ready (Gemini, ElevenLabs, Picovoice)

---

## Part 1: Supabase Production Setup

### Step 1: Create Production Supabase Project

1. Go to [https://supabase.com/dashboard](https://supabase.com/dashboard)
2. Click **"New Project"**
3. Enter details:
   - **Name:** voice-assistant-prod
   - **Database Password:** Generate strong password (SAVE THIS!)
   - **Region:** Choose closest to your users (e.g., US East, EU West)
   - **Pricing Plan:** Free tier (500MB database, 50,000 monthly active users)
4. Click **"Create new project"**
5. Wait 2-3 minutes for provisioning

### Step 2: Run Database Migrations

1. Go to **SQL Editor** in Supabase dashboard
2. Click **"New query"**
3. Copy and paste contents of `supabase/migrations/001_user_profiles.sql`
4. Click **"Run"** (or Ctrl+Enter)
5. Verify success message
6. Repeat for:
   - `002_conversation_sessions.sql`
   - `003_conversation_turns.sql`

### Step 3: Verify Tables and RLS

1. Go to **Table Editor**
2. Verify these tables exist:
   - ✅ user_profiles
   - ✅ conversation_sessions
   - ✅ conversation_turns

3. Click on each table → **Policies** tab
4. Verify RLS is enabled and policies exist

### Step 4: Configure Email Authentication

1. Go to **Authentication** → **Providers**
2. Enable **Email** provider
3. **Confirm Email:** Recommended (Enable)
4. **Email Templates:**
   - Customize confirmation email (optional)
   - Set **Site URL:** `https://your-app.vercel.app`

### Step 5: Get API Credentials

1. Go to **Project Settings** (gear icon)
2. Click **API** section
3. Copy these values (you'll need them):

```bash
# Project URL
SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co

# Project API Keys
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# JWT Secret (click "Reveal" next to JWT Secret)
SUPABASE_JWT_SECRET=your-super-secret-jwt-secret-string
```

### Step 6: Set Up Database Backups (Optional)

1. Go to **Database** → **Backups**
2. Enable **Point-in-Time Recovery (PITR)** (paid feature)
3. Or use manual backups:
   - Click **"Create backup"**
   - Schedule weekly backups

---

## Part 2: Backend Deployment (Render)

### Step 1: Prepare Backend Code

1. Ensure `requirements.txt` is up to date:

```bash
# Generate requirements.txt
pip freeze > requirements.txt
```

2. Create `render.yaml` (already exists):

```yaml
services:
  - type: web
    name: voice-assistant-api
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn src.api.websocket_server:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: PYTHON_VERSION
        value: 3.10.0
      - key: GEMINI_API_KEY
        sync: false
      - key: ELEVENLABS_API_KEY
        sync: false
      - key: PICOVOICE_ACCESS_KEY
        sync: false
      - key: SUPABASE_URL
        sync: false
      - key: SUPABASE_JWT_SECRET
        sync: false
      - key: SUPABASE_SERVICE_ROLE_KEY
        sync: false
      - key: ENABLE_CONVERSATION_PERSISTENCE
        value: "true"
```

3. Commit and push to GitHub:

```bash
git add .
git commit -m "Prepare for production deployment"
git push origin main
```

### Step 2: Deploy to Render

1. Go to [https://dashboard.render.com](https://dashboard.render.com)
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Select your repo: `Voice_Assistant`
5. Configure:
   - **Name:** voice-assistant-api
   - **Environment:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn src.api.websocket_server:app --host 0.0.0.0 --port $PORT`
   - **Plan:** Free (or Starter for better performance)

6. Click **"Advanced"** → Add environment variables:

```bash
# AI Services
GEMINI_API_KEY=your-gemini-key
ELEVENLABS_API_KEY=your-elevenlabs-key
PICOVOICE_ACCESS_KEY=your-picovoice-key
OPENAI_API_KEY=your-openai-key

# Supabase
SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
SUPABASE_JWT_SECRET=your-jwt-secret
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Persistence
ENABLE_CONVERSATION_PERSISTENCE=true
CONVERSATION_RETENTION_DAYS=30

# CORS (Important!)
CORS_ORIGINS=https://your-app.vercel.app,http://localhost:3000
```

7. Click **"Create Web Service"**
8. Wait 3-5 minutes for deployment
9. Copy your backend URL: `https://voice-assistant-api.onrender.com`

### Step 3: Add Persistent Disk (Important!)

1. In Render dashboard, go to your service
2. Click **"Disks"** tab
3. Click **"Add Disk"**
4. Configure:
   - **Name:** data
   - **Mount Path:** `/opt/render/project/src/data`
   - **Size:** 1GB (free tier)
5. Click **"Save"**
6. Redeploy service

### Step 4: Verify Backend Deployment

Test health endpoint:
```bash
curl https://voice-assistant-api.onrender.com/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "services": {...}
}
```

---

## Part 3: Frontend Deployment (Vercel)

### Step 1: Prepare Frontend Code

1. Update `web/package.json` scripts:

```json
{
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  }
}
```

2. Install dependencies:

```bash
cd web
npm install next-auth @supabase/supabase-js
```

3. Create `web/.env.local` (for local testing):

```bash
# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key

# NextAuth
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=$(openssl rand -base64 32)

# Backend API
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/voice
```

4. Test build locally:

```bash
npm run build
```

5. If successful, commit and push:

```bash
git add .
git commit -m "Add Supabase auth and prepare for Vercel"
git push origin main
```

### Step 2: Deploy to Vercel

1. Go to [https://vercel.com/dashboard](https://vercel.com/dashboard)
2. Click **"Add New..."** → **"Project"**
3. Import your GitHub repository
4. Configure:
   - **Framework Preset:** Next.js
   - **Root Directory:** `web`
   - **Build Command:** `npm run build` (auto-detected)
   - **Output Directory:** `.next` (auto-detected)

5. **Environment Variables** (CRITICAL - Add all of these):

```bash
# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key

# NextAuth (Generate new secret for production!)
NEXTAUTH_URL=https://your-app.vercel.app
NEXTAUTH_SECRET=$(openssl rand -base64 32)
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Backend API (Use your Render URL)
NEXT_PUBLIC_API_URL=https://voice-assistant-api.onrender.com
NEXT_PUBLIC_WS_URL=wss://voice-assistant-api.onrender.com/ws/voice
```

6. Click **"Deploy"**
7. Wait 2-3 minutes for deployment
8. Copy your frontend URL: `https://your-app.vercel.app`

### Step 3: Update Supabase Site URL

1. Go back to Supabase dashboard
2. **Authentication** → **URL Configuration**
3. Set **Site URL:** `https://your-app.vercel.app`
4. Add to **Redirect URLs:**
   - `https://your-app.vercel.app/api/auth/callback/credentials`
   - `https://your-app.vercel.app/*`

### Step 4: Update Backend CORS

1. Go to Render dashboard
2. Select your backend service
3. **Environment** → Edit `CORS_ORIGINS`:

```bash
CORS_ORIGINS=https://your-app.vercel.app,https://your-app-preview.vercel.app
```

4. Save and redeploy

---

## Part 4: Testing Production Deployment

### Test 1: Frontend Loads

1. Open `https://your-app.vercel.app`
2. Should redirect to `/auth/login`
3. UI should load without errors

### Test 2: User Registration

1. Go to `/auth/register`
2. Create account:
   - Email: test@example.com
   - Password: TestPassword123!
3. Should show success message
4. Check Supabase dashboard:
   - **Authentication** → **Users**
   - Verify user created
   - **Table Editor** → **user_profiles**
   - Verify profile auto-created

### Test 3: User Login

1. Go to `/auth/login`
2. Login with test account
3. Should redirect to chat interface
4. No errors in browser console

### Test 4: WebSocket Connection

1. After login, check browser console
2. Should see: `WebSocket connected`
3. Network tab should show WebSocket connection to:
   `wss://voice-assistant-api.onrender.com/ws/voice?token=...`

### Test 5: Send Message

1. Type: "Hello, what's the weather?"
2. Agent should respond
3. Check Supabase dashboard:
   - **Table Editor** → **conversation_sessions**
   - Verify session created with your user_id
   - **conversation_turns** → Verify turn saved

### Test 6: Conversation History

1. Click History button (clock icon)
2. Should show your conversation
3. Search should work
4. Export should download files

### Test 7: Logout and Re-login

1. Click logout
2. Should redirect to login
3. Login again
4. Previous conversation should still be visible

---

## Part 5: Production Environment Variables Summary

### Supabase Dashboard
```bash
# Get from: Project Settings → API
NEXT_PUBLIC_SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGc...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...
SUPABASE_JWT_SECRET=your-jwt-secret
```

### Render (Backend)
```bash
# AI Services
GEMINI_API_KEY=your-key
ELEVENLABS_API_KEY=your-key
PICOVOICE_ACCESS_KEY=your-key
OPENAI_API_KEY=your-key

# Supabase
SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
SUPABASE_JWT_SECRET=your-jwt-secret
SUPABASE_SERVICE_ROLE_KEY=your-service-key

# Config
ENABLE_CONVERSATION_PERSISTENCE=true
CONVERSATION_RETENTION_DAYS=30
CORS_ORIGINS=https://your-app.vercel.app

# Python
PYTHON_VERSION=3.10.0
```

### Vercel (Frontend)
```bash
# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-key

# NextAuth
NEXTAUTH_URL=https://your-app.vercel.app
NEXTAUTH_SECRET=your-generated-secret-32-chars

# Backend
NEXT_PUBLIC_API_URL=https://voice-assistant-api.onrender.com
NEXT_PUBLIC_WS_URL=wss://voice-assistant-api.onrender.com/ws/voice
```

---

## Part 6: Post-Deployment Configuration

### 1. Custom Domain (Optional)

**Vercel:**
1. Go to **Settings** → **Domains**
2. Add your domain: `app.yourdomain.com`
3. Update DNS records as instructed
4. Update NEXTAUTH_URL to new domain

**Render:**
1. Go to **Settings** → **Custom Domain**
2. Add: `api.yourdomain.com`
3. Update DNS records
4. Update NEXT_PUBLIC_API_URL and NEXT_PUBLIC_WS_URL

### 2. SSL Certificates

- ✅ Vercel: Automatic (Let's Encrypt)
- ✅ Render: Automatic (Let's Encrypt)
- ✅ Supabase: Built-in SSL

### 3. Monitoring and Logs

**Render:**
- **Logs** tab: View real-time logs
- **Metrics** tab: CPU, memory usage
- Set up log retention

**Vercel:**
- **Deployments** → Click deployment → **Function Logs**
- **Analytics** tab: View usage stats
- **Speed Insights**: Enable for performance monitoring

**Supabase:**
- **Database** → **Query Performance**
- **API** → **Logs** (paid feature)
- Set up email alerts for downtime

### 4. Database Maintenance

**Regular Tasks:**
```sql
-- Run monthly in Supabase SQL Editor

-- Vacuum database
VACUUM ANALYZE;

-- Check table sizes
SELECT
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Clean old conversations (optional)
DELETE FROM conversation_sessions
WHERE last_updated < NOW() - INTERVAL '90 days';
```

### 5. Backup Strategy

**Automated Backups:**
1. Supabase free tier: Daily backups (7-day retention)
2. Paid tier: Point-in-time recovery

**Manual Backup:**
```bash
# Using Supabase CLI
supabase db dump -f backup.sql

# Or pg_dump
pg_dump -h db.xxxxxxxxxxxxx.supabase.co -U postgres -d postgres > backup.sql
```

---

## Part 7: Troubleshooting

### Issue: "Failed to fetch" in frontend

**Cause:** CORS not configured

**Solution:**
1. Add Vercel URL to Render's CORS_ORIGINS
2. Verify format: `https://your-app.vercel.app` (no trailing slash)
3. Redeploy backend

### Issue: WebSocket connection fails

**Cause:** Missing JWT token or wrong URL

**Solution:**
1. Check NEXT_PUBLIC_WS_URL uses `wss://` (not `ws://`)
2. Verify token is passed: `?token=...`
3. Check browser console for error details

### Issue: "User not authenticated" errors

**Cause:** JWT validation failing

**Solution:**
1. Verify SUPABASE_JWT_SECRET matches in backend
2. Check NEXTAUTH_SECRET is set in Vercel
3. Clear browser cookies and re-login

### Issue: Database connection errors

**Cause:** Supabase credentials wrong

**Solution:**
1. Verify SUPABASE_URL format: `https://xxx.supabase.co`
2. Check SUPABASE_SERVICE_ROLE_KEY is correct
3. Test connection:
```bash
curl -H "apikey: YOUR_SERVICE_KEY" \
  https://xxx.supabase.co/rest/v1/user_profiles
```

### Issue: Build fails on Vercel

**Cause:** Missing dependencies or environment variables

**Solution:**
1. Check build logs in Vercel
2. Verify all environment variables are set
3. Test build locally: `cd web && npm run build`
4. Check Node.js version (should be 18+)

### Issue: Render service crashes

**Cause:** Missing Python dependencies or environment variables

**Solution:**
1. Check logs in Render dashboard
2. Verify requirements.txt is complete
3. Test locally: `pip install -r requirements.txt`
4. Check Python version (should be 3.10+)

---

## Part 8: Performance Optimization

### 1. Enable Caching

**Vercel:**
- Static assets cached automatically
- Enable Edge caching for API routes

**Render:**
- Add Redis for session caching (paid)
- Enable HTTP/2

### 2. Database Optimization

```sql
-- Add indexes for common queries
CREATE INDEX IF NOT EXISTS idx_sessions_user_updated
  ON conversation_sessions(user_id, last_updated DESC);

CREATE INDEX IF NOT EXISTS idx_turns_session_timestamp
  ON conversation_turns(session_id, timestamp DESC);

-- Analyze query performance
EXPLAIN ANALYZE
SELECT * FROM conversation_sessions
WHERE user_id = 'xxx'
ORDER BY last_updated DESC
LIMIT 10;
```

### 3. Frontend Optimization

```typescript
// Enable SWR caching for API calls
import useSWR from 'swr';

const { data: sessions } = useSWR(
  '/api/conversations',
  fetcher,
  { revalidateOnFocus: false, dedupingInterval: 60000 }
);
```

### 4. CDN Configuration

- ✅ Vercel automatically uses Edge Network
- ✅ Supabase uses global CDN
- ✅ Render: Use Cloudflare (optional)

---

## Part 9: Security Checklist

- [ ] All API keys stored as environment variables (not in code)
- [ ] CORS configured to only allow your Vercel domain
- [ ] RLS policies enabled on all Supabase tables
- [ ] HTTPS enforced on all services
- [ ] JWT tokens have expiration (30 days max)
- [ ] Service role keys only used in backend (never frontend)
- [ ] Rate limiting enabled (Vercel free tier: 1000 req/day)
- [ ] Database backups configured
- [ ] Email confirmation enabled for new users
- [ ] Strong password policy (8+ characters)

---

## Part 10: Cost Breakdown (Free Tier)

| Service | Free Tier Limits | Cost After |
|---------|-----------------|------------|
| **Supabase** | 500MB DB, 50K MAU, 2GB egress | $25/month (Pro) |
| **Vercel** | 100GB bandwidth, unlimited deployments | $20/month (Pro) |
| **Render** | 750 hours/month (sleeps after inactivity) | $7/month (Starter) |
| **Total** | **$0/month** | **$52/month** (paid) |

**Note:** Render free tier sleeps after 15min inactivity. First request takes 30-60s to wake up.

---

## Part 11: Going Live Checklist

- [ ] Supabase production project created
- [ ] Database migrations run successfully
- [ ] Email authentication configured
- [ ] Backend deployed to Render
- [ ] Persistent disk added to Render
- [ ] Frontend deployed to Vercel
- [ ] All environment variables configured
- [ ] CORS updated with Vercel URL
- [ ] Supabase Site URL updated
- [ ] Test user registration works
- [ ] Test login and WebSocket connection
- [ ] Test conversation persistence
- [ ] Test conversation history UI
- [ ] Monitoring and logs configured
- [ ] Database backups enabled

---

## 🎉 Success!

Your Voice Assistant is now live at:
- **Frontend:** `https://your-app.vercel.app`
- **Backend:** `https://voice-assistant-api.onrender.com`
- **Database:** Supabase PostgreSQL with RLS

**Share it:** Send the Vercel URL to users to try your AI voice assistant!

---

## 📞 Support

**Issues?** Check:
1. This troubleshooting guide
2. Render logs: `https://dashboard.render.com`
3. Vercel logs: `https://vercel.com/dashboard`
4. Supabase logs: `https://supabase.com/dashboard`

**Need Help?**
- Render docs: https://render.com/docs
- Vercel docs: https://vercel.com/docs
- Supabase docs: https://supabase.com/docs
