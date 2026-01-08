# Free Deployment Guide - Voice Assistant

## Quick Links
- **Frontend (Vercel)**: https://vercel.com
- **Backend (Render)**: https://render.com
- **Uptime Monitor**: https://uptimerobot.com

---

## Prerequisites
- ✅ GitHub account
- ✅ Vercel account (sign up with GitHub)
- ✅ Render account (sign up with GitHub)
- ✅ API keys: GEMINI_API_KEY, OPENAI_API_KEY (optional), ELEVENLABS_API_KEY (optional)

---

## Step-by-Step Deployment

### **Step 1: Push to GitHub** 📤

```bash
# From project root
git add .
git commit -m "Add deployment configuration"
git push origin main
```

If you don't have a GitHub remote:
```bash
# Create repo on GitHub first, then:
git remote add origin https://github.com/YOUR_USERNAME/Voice_Assistant.git
git branch -M main
git push -u origin main
```

---

### **Step 2: Deploy Backend to Render (FREE)** 🐍

1. **Go to** [https://render.com](https://render.com)
2. **Sign up** with GitHub
3. Click **"New +"** → **"Blueprint"**
4. **Connect** your `Voice_Assistant` repository
5. Render will auto-detect `render.yaml`
6. Click **"Apply"**
7. **Wait 5-10 minutes** for build to complete
8. **Add Environment Variables**:
   - Go to Dashboard → `voice-assistant-backend` → Environment
   - Add these secrets:
     - `GEMINI_API_KEY`: `your-gemini-key-here`
     - `OPENAI_API_KEY`: `your-openai-key-here` (optional)
     - `ELEVENLABS_API_KEY`: `your-elevenlabs-key-here` (optional)
9. **Copy Backend URL**: `https://voice-assistant-backend.onrender.com`

---

### **Step 3: Deploy Frontend to Vercel (FREE)** 🌐

```bash
# Install Vercel CLI (one-time)
npm install -g vercel

# Navigate to web directory
cd web

# Login to Vercel
vercel login

# Deploy
vercel
```

**Follow the prompts:**
- Set up and deploy? → **Yes**
- Which scope? → **Your account**
- Link to existing project? → **No**
- Project name? → **voice-assistant-frontend**
- Directory? → **./  **
- Override settings? → **No**

---

### **Step 4: Configure Frontend Environment Variables** ⚙️

**In Vercel Dashboard:**
1. Go to your project → **Settings** → **Environment Variables**
2. Add these variables:
   - `NEXT_PUBLIC_WS_URL`: `wss://voice-assistant-backend.onrender.com/ws/voice`
   - `NEXT_PUBLIC_API_URL`: `https://voice-assistant-backend.onrender.com`
3. **Redeploy**:
   ```bash
   vercel --prod
   ```

---

### **Step 5: Update Backend CORS (If Needed)** 🔒

If you get CORS errors:

**In Render Dashboard:**
1. Go to `voice-assistant-backend` → **Environment**
2. Add/Update:
   - Key: `CORS_ORIGINS`
   - Value: `https://voice-assistant-frontend.vercel.app,https://*.vercel.app`
3. Service will auto-redeploy

---

### **Step 6: Keep Backend Alive (Optional)** 🔄

**Problem**: Render free tier sleeps after 15 minutes of inactivity (50s cold start).

**Solution**: Use UptimeRobot to ping your backend every 5 minutes.

1. **Go to** [https://uptimerobot.com](https://uptimerobot.com)
2. **Sign up** (free account)
3. Click **"Add New Monitor"**
4. Configure:
   - **Monitor Type**: HTTP(s)
   - **Friendly Name**: Voice Assistant Backend
   - **URL**: `https://voice-assistant-backend.onrender.com/health`
   - **Monitoring Interval**: 5 minutes
5. Click **"Create Monitor"**

**Result**: Your backend will never sleep! 🎉

---

## 🎯 Your Deployed URLs

After deployment:
- **Frontend**: `https://voice-assistant-frontend.vercel.app`
- **Backend API**: `https://voice-assistant-backend.onrender.com`
- **Health Check**: `https://voice-assistant-backend.onrender.com/health`
- **WebSocket**: `wss://voice-assistant-backend.onrender.com/ws/voice`

---

## Testing Your Deployment

1. **Open frontend** in browser
2. **First request** may take ~50s (backend waking up)
3. **Test text chat**: Type a message
4. **Test voice**: Hold SPACEBAR to record
5. **Check WebSocket**: Connection indicator should be green 🟢

---

## Troubleshooting

### ❌ Backend Not Responding
**Check Render logs:**
- Dashboard → `voice-assistant-backend` → **Logs**
- Look for errors in build or runtime
- Verify environment variables are set

**Common fixes:**
- Ensure `GEMINI_API_KEY` is set correctly
- Check `requirements.txt` is present
- Verify Python version (should be 3.10+)

---

### ❌ Frontend Can't Connect to Backend
**Check CORS settings:**
- Backend must allow your Vercel domain
- Add to `CORS_ORIGINS` environment variable
- Include: `https://*.vercel.app`

**Check WebSocket URL:**
- Must use `wss://` (not `ws://`)
- Verify in browser console (F12 → Console)

---

### ❌ Cold Start Issues
**Backend takes too long to wake:**
- Set up UptimeRobot (see Step 6)
- Or upgrade Render to paid tier ($7/month, no sleep)

---

### ❌ Build Failures

**Render build fails:**
```bash
# Check requirements.txt is valid
pip install -r requirements.txt

# Ensure Python 3.10+ locally
python --version
```

**Vercel build fails:**
```bash
# Check package.json in web/ directory
cd web
npm install
npm run build
```

---

## Cost Breakdown

| Service | Monthly Cost | What You Get |
|---------|--------------|--------------|
| **Vercel Frontend** | **$0** | Unlimited deployments, 100GB bandwidth, Auto HTTPS, CDN |
| **Render Backend** | **$0** | 750 hours/month (24/7 for 1 service), Auto HTTPS, WebSocket |
| **UptimeRobot** | **$0** | 50 monitors, 5-minute interval |
| **GitHub** | **$0** | Unlimited public repos |
| **Total** | **$0/month** | Full production deployment! |

---

## Upgrade Options (If Needed)

If you exceed free tier limits:

| Upgrade | Cost | Benefits |
|---------|------|----------|
| **Render Starter** | $7/month | No cold starts, 512MB RAM, Always-on |
| **Vercel Pro** | $20/month | Unlimited everything, Advanced analytics |
| **Railway** | $5/month credit | ~100 hours uptime, No cold starts |

---

## CI/CD Auto-Deploy

Both platforms auto-deploy when you push to GitHub:

```bash
# Make changes to code
git add .
git commit -m "Update feature"
git push origin main

# Vercel and Render will automatically deploy! 🚀
```

---

## Advanced Configuration

### Custom Domain (FREE on Vercel)
1. Buy domain (Namecheap, Cloudflare, etc.)
2. Vercel Dashboard → Project → Settings → Domains
3. Add custom domain: `assistant.yourdomain.com`
4. Update DNS records as instructed
5. Vercel auto-provisions SSL certificate

### Environment-Specific Variables
```bash
# Production
vercel env add NEXT_PUBLIC_API_URL production

# Preview (for PR branches)
vercel env add NEXT_PUBLIC_API_URL preview

# Development
vercel env add NEXT_PUBLIC_API_URL development
```

---

## Monitoring & Logs

**Vercel:**
- Dashboard → Project → Deployments → View Logs
- Real-time function logs
- Performance analytics

**Render:**
- Dashboard → Service → Logs (Live tail)
- Metrics: CPU, Memory, Network
- Health check history

---

## Security Best Practices

✅ **Never commit secrets** to GitHub
- Use `.env.local` for local development
- Set environment variables in hosting dashboards
- `.gitignore` includes all credential files

✅ **API Key Rotation**
- Rotate keys every 90 days
- Update in Render/Vercel dashboards
- Services auto-restart with new keys

✅ **CORS Configuration**
- Only allow your domains
- Don't use wildcard `*` in production

---

## Support

📖 **Documentation**: See README.md
🐛 **Issues**: Open GitHub issue
💬 **Community**: GitHub Discussions

---

**🎉 Congratulations! Your Voice Assistant is now live and FREE!**
