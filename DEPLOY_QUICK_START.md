# 🚀 Quick Start: Deploy to Production (30 minutes)

Deploy your Voice Assistant with authentication to production in 30 minutes.

**Stack:** Hugging Face Spaces (Backend) + Vercel (Frontend) + Supabase (Database + Auth)

---

## Prerequisites

- GitHub account
- Hugging Face account (https://huggingface.co/join)
- Vercel account (https://vercel.com/signup)
- Supabase account (https://supabase.com/dashboard/sign-up)
- All API keys ready

---

## Step 1: Supabase Setup (10 min)

### 1.1 Create Project

1. Go to https://supabase.com/dashboard
2. Click **"New project"**
3. Enter:
   - Name: `voice-assistant-prod`
   - Database Password: *Generate and save*
   - Region: Choose closest to users
4. Wait 2 minutes for setup

### 1.2 Run Migrations

1. Go to **SQL Editor**
2. Click **"New query"**
3. Copy/paste `supabase/migrations/001_user_profiles.sql`
4. Click **"Run"**
5. Repeat for `002_conversation_sessions.sql` and `003_conversation_turns.sql`

### 1.3 Enable Email Auth

1. Go to **Authentication** → **Providers**
2. Enable **Email** provider
3. Done!

### 1.4 Get API Keys

1. Go to **Project Settings** → **API**
2. Copy these (you'll need them):

```bash
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGc...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...
SUPABASE_JWT_SECRET=your-jwt-secret
```

---

## Step 2: Hugging Face Spaces (10 min)

### 2.1 Configure Your Space

Your space: https://huggingface.co/spaces/AbdullahMalik17/VoiceAssistant17

1. Go to **Settings**
2. Verify:
   - **Space SDK:** Docker
   - **Space hardware:** CPU basic
   - **App port:** 7860

### 2.2 Add Secrets

Click **"Variables and secrets"** → **"New secret"**

Add all of these:

```bash
# AI Services
GEMINI_API_KEY=your-key
ELEVENLABS_API_KEY=your-key
PICOVOICE_ACCESS_KEY=your-key
OPENAI_API_KEY=your-key

# Supabase (from Step 1.4)
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_JWT_SECRET=your-jwt-secret
SUPABASE_SERVICE_ROLE_KEY=your-service-key

# Config
ENABLE_CONVERSATION_PERSISTENCE=true
CORS_ORIGINS=https://your-app.vercel.app,http://localhost:3000
```

### 2.3 Push Code

```bash
# Add HF remote
git remote add hf https://huggingface.co/spaces/AbdullahMalik17/VoiceAssistant17

# Push
git push hf main
```

### 2.4 Wait for Build

1. Go to **"Logs"** tab
2. Wait 5-10 minutes for Docker build
3. Look for: `Application startup complete`

### 2.5 Test Backend

```bash
curl https://abdullahmalik17-voiceassistant17.hf.space/health
```

Should return: `{"status": "healthy", ...}`

---

## Step 3: Vercel Frontend (10 min)

### 3.1 Install Dependencies

```bash
cd web
npm install next-auth @supabase/supabase-js
```

### 3.2 Deploy to Vercel

1. Go to https://vercel.com/dashboard
2. Click **"Add New..."** → **"Project"**
3. Import your GitHub repo
4. Configure:
   - **Framework:** Next.js
   - **Root Directory:** `web`

### 3.3 Add Environment Variables

Click **"Environment Variables"** and add:

```bash
# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://xxxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key

# NextAuth (generate with: openssl rand -base64 32)
NEXTAUTH_URL=https://your-app.vercel.app
NEXTAUTH_SECRET=generate-a-random-32-char-string
SUPABASE_SERVICE_ROLE_KEY=your-service-key

# Backend (HF Spaces)
NEXT_PUBLIC_API_URL=https://abdullahmalik17-voiceassistant17.hf.space
NEXT_PUBLIC_WS_URL=wss://abdullahmalik17-voiceassistant17.hf.space/ws/voice
```

### 3.4 Deploy

1. Click **"Deploy"**
2. Wait 2-3 minutes
3. Copy your URL: `https://your-app.vercel.app`

---

## Step 4: Final Configuration (5 min)

### 4.1 Update Supabase Site URL

1. Go to Supabase → **Authentication** → **URL Configuration**
2. Set **Site URL:** `https://your-app.vercel.app`

### 4.2 Update HF CORS

1. Go to HF Space → **Settings** → **Variables and secrets**
2. Update `CORS_ORIGINS`:

```bash
CORS_ORIGINS=https://your-app.vercel.app,https://your-app-*.vercel.app
```

3. Space will auto-rebuild

---

## Step 5: Test Everything (5 min)

### 5.1 Test Registration

1. Go to `https://your-app.vercel.app`
2. Should redirect to `/auth/register`
3. Create account
4. Check Supabase → **Authentication** → **Users**
5. Verify user created ✅

### 5.2 Test Login

1. Go to `/auth/login`
2. Login with your account
3. Should see chat interface ✅

### 5.3 Test Chat

1. Type: "Hello, what can you do?"
2. Agent should respond ✅
3. Click History button
4. Should see your conversation ✅

### 5.4 Test Persistence

1. Logout
2. Login again
3. Previous conversation should still be there ✅

---

## ✅ Deployment Complete!

Your Voice Assistant is now live at:
- **Frontend:** https://your-app.vercel.app
- **Backend:** https://abdullahmalik17-voiceassistant17.hf.space
- **Database:** Supabase

---

## 📊 What's Deployed

- ✅ User authentication (register/login)
- ✅ Conversation persistence
- ✅ Conversation history UI
- ✅ Search conversations
- ✅ Export conversations (JSON/Text)
- ✅ 30+ agent tools (Gmail, Drive, Browser, etc.)
- ✅ Real-time voice chat via WebSocket
- ✅ Text-to-speech responses
- ✅ Dark mode UI

---

## 🔧 Troubleshooting

### Backend not responding

**Check HF Spaces logs:**
```
https://huggingface.co/spaces/AbdullahMalik17/VoiceAssistant17/logs
```

**Common issues:**
- Missing environment secrets
- Docker build failed
- Port not set to 7860

### Frontend can't connect to backend

**Check:**
1. Vercel env vars have correct HF URL
2. CORS includes your Vercel domain
3. Both services use HTTPS/WSS

### WebSocket connection fails

**Check:**
1. URL is `wss://` (not `ws://`)
2. JWT token is being sent
3. Browser console for errors

### Authentication errors

**Check:**
1. Supabase Site URL matches Vercel URL
2. NEXTAUTH_SECRET is set
3. All Supabase keys are correct

---

## 📈 Next Steps

### Add Custom Domain

**Vercel:**
1. Settings → Domains
2. Add `app.yourdomain.com`
3. Update DNS
4. Update NEXTAUTH_URL

**HF Spaces:**
- Free tier doesn't support custom domains
- Use provided URL: `*.hf.space`

### Upgrade for Production

**Recommended upgrades:**
- HF Spaces: Always On ($9/month) - prevents sleep
- HF Spaces: Persistent Storage ($5/month) - keep data
- Vercel: Pro ($20/month) - better analytics
- Supabase: Pro ($25/month) - more storage/bandwidth

**Total:** $59/month for production-ready setup

### Monitor Usage

**HF Spaces:**
- Go to **Analytics** tab
- Monitor requests, errors, uptime

**Vercel:**
- Go to **Analytics**
- Monitor page views, API calls

**Supabase:**
- Go to **Database** → **Usage**
- Monitor database size, bandwidth

---

## 🎉 Success!

You now have a fully deployed, production-ready AI Voice Assistant with:
- User authentication
- Persistent conversations
- Real-time voice/text chat
- 30+ agent capabilities
- Beautiful web interface

**Share your assistant:** Send users your Vercel URL!

---

## 📚 Additional Resources

- **Full HF Deployment Guide:** `HUGGINGFACE_DEPLOYMENT_GUIDE.md`
- **Supabase Setup:** `SUPABASE_SETUP_GUIDE.md`
- **Frontend Setup:** `FRONTEND_AUTH_SETUP.md`
- **Production Guide:** `PRODUCTION_DEPLOYMENT_GUIDE.md`

**Need help?** Open an issue on GitHub or check the troubleshooting sections in the detailed guides.
