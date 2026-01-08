# Free Deployment Guide - Voice Assistant

## Prerequisites
- GitHub account
- Vercel account (sign up with GitHub)
- Render account (sign up with GitHub)
- API keys: GEMINI_API_KEY, OPENAI_API_KEY (optional), ELEVENLABS_API_KEY (optional)

## Step 1: Push to GitHub

```bash
# If not already a git repo
git init
git add .
git commit -m "Initial commit"

# Create repo on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/Voice_Assistant.git
git branch -M main
git push -u origin main
```

## Step 2: Deploy Backend to Render (FREE)

1. Go to https://render.com → Sign up with GitHub
2. Click "New +" → "Blueprint"
3. Connect your `Voice_Assistant` repository
4. Render will detect `render.yaml` automatically
5. Click "Apply"
6. Go to Dashboard → voice-assistant-backend → Environment
7. Add these secrets:
   - `GEMINI_API_KEY`: your-gemini-key-here
   - `OPENAI_API_KEY`: your-openai-key-here (optional)
   - `ELEVENLABS_API_KEY`: your-elevenlabs-key-here (optional)
8. Wait 5-10 minutes for build
9. Copy your backend URL: `https://voice-assistant-backend.onrender.com`

## Step 3: Deploy Frontend to Vercel (FREE)

```bash
# Install Vercel CLI
npm install -g vercel

# Navigate to web directory
cd web

# Deploy
vercel login
vercel

# Follow prompts:
# - Set up and deploy? Yes
# - Which scope? Your account
# - Link to existing project? No
# - Project name? voice-assistant-frontend
# - Directory? ./
# - Override settings? No
```

## Step 4: Configure Frontend Environment Variables

In Vercel Dashboard:
1. Go to your project → Settings → Environment Variables
2. Add these variables:
   - `NEXT_PUBLIC_WS_URL`: `wss://voice-assistant-backend.onrender.com/ws/voice`
   - `NEXT_PUBLIC_API_URL`: `https://voice-assistant-backend.onrender.com`
3. Redeploy: `vercel --prod`

## Step 5: Update CORS Settings (Backend)

Update `config/assistant_config.yaml` or backend code to allow your Vercel domain:

```yaml
# In assistant_config.yaml or via Render environment variable
CORS_ORIGINS=https://voice-assistant-frontend.vercel.app,https://*.vercel.app
```

Or in Render Dashboard:
- Environment → Add Variable
- Key: `CORS_ORIGINS`
- Value: `https://voice-assistant-frontend.vercel.app,https://*.vercel.app`

## Step 6: Test Your Deployment

1. Open frontend: `https://voice-assistant-frontend.vercel.app`
2. First request will take ~50s (backend waking up)
3. Subsequent requests are fast
4. Test voice input/output

## Optional: Keep Backend Alive (Prevent Cold Starts)

### Option A: UptimeRobot (FREE)
1. Go to https://uptimerobot.com (free account)
2. Add Monitor:
   - Type: HTTP(s)
   - URL: `https://voice-assistant-backend.onrender.com/health`
   - Interval: 5 minutes
3. Backend will never sleep!

### Option B: Cron-job.org (FREE)
1. Go to https://cron-job.org
2. Create job:
   - URL: `https://voice-assistant-backend.onrender.com/health`
   - Interval: Every 14 minutes

## Troubleshooting

### Backend Not Responding
- Check Render logs: Dashboard → voice-assistant-backend → Logs
- Verify environment variables are set
- Check health endpoint: `https://voice-assistant-backend.onrender.com/health`

### Frontend Can't Connect to Backend
- Verify CORS_ORIGINS includes your Vercel domain
- Check WebSocket URL uses `wss://` (not `ws://`)
- Open browser console for WebSocket errors

### Cold Start Issues
- Set up uptime monitor (see Optional section above)
- Consider upgrading to Render paid tier ($7/month, no sleep)

## Cost Breakdown

| Service | Monthly Cost | What You Get |
|---------|--------------|--------------|
| Vercel Frontend | **FREE** | Unlimited bandwidth (100GB Fair Use), Auto HTTPS, CDN |
| Render Backend | **FREE** | 750 hours/month (24/7 for 1 service), Auto HTTPS, WebSocket |
| UptimeRobot | **FREE** | 50 monitors, 5min interval |
| **Total** | **$0/month** | Full production deployment! |

## Upgrade Paths (If Needed)

If you exceed free tier:
- **Vercel Pro**: $20/month (unlimited everything)
- **Render Starter**: $7/month (no cold starts, 512MB RAM)
- **Railway**: $5/month credit (~100 hours uptime)

## URLs After Deployment

- **Frontend**: https://voice-assistant-frontend.vercel.app
- **Backend API**: https://voice-assistant-backend.onrender.com
- **Backend Health**: https://voice-assistant-backend.onrender.com/health
- **WebSocket**: wss://voice-assistant-backend.onrender.com/ws/voice

## Auto-Deploy Setup

Both Vercel and Render auto-deploy on git push:

```bash
# Make changes
git add .
git commit -m "Update feature"
git push origin main

# Vercel and Render will auto-deploy!
```

---

**You're now live with a free, production-ready Voice Assistant!** 🎉
