# 🤗 Hugging Face Spaces Deployment Guide

Complete guide to deploy Voice Assistant backend to Hugging Face Spaces.

**Your Space:** https://huggingface.co/spaces/AbdullahMalik17/VoiceAssistant17

**Stack:**
- Frontend: Vercel (Next.js)
- Backend: Hugging Face Spaces (FastAPI + Docker)
- Database: Supabase (PostgreSQL)
- Authentication: Supabase Auth + NextAuth.js

---

## Part 1: Prepare Backend for Hugging Face Spaces

### Step 1: Create Dockerfile

Create `Dockerfile` in project root:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory for SQLite
RUN mkdir -p data

# Expose port (HF Spaces uses 7860)
EXPOSE 7860

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:7860/health || exit 1

# Start FastAPI server
CMD ["uvicorn", "src.api.websocket_server:app", "--host", "0.0.0.0", "--port", "7860"]
```

### Step 2: Create README.md for HF Spaces

Create `README.md` in project root (or update existing):

```markdown
---
title: Voice Assistant API
emoji: 🎤
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# Voice Assistant API

AI-powered voice assistant with conversation memory and agentic capabilities.

## Features

- 🎙️ Real-time voice interaction via WebSocket
- 🤖 Gemini-powered AI responses
- 🔊 ElevenLabs text-to-speech
- 💾 Persistent conversation history (Supabase)
- 🔐 User authentication with JWT
- 🛠️ 30+ agent tools (Gmail, Drive, Browser, etc.)

## API Endpoints

- `GET /health` - Health check
- `GET /api/conversations` - List conversations
- `WS /ws/voice` - WebSocket voice connection

## Authentication

Requires Supabase JWT token in WebSocket connection:
```
wss://abdullahmalik17-voiceassistant17.hf.space/ws/voice?token=YOUR_JWT_TOKEN
```

## Environment Variables

Set in Hugging Face Spaces Settings → Variables and secrets:

- `GEMINI_API_KEY` - Google Gemini API key
- `ELEVENLABS_API_KEY` - ElevenLabs API key
- `PICOVOICE_ACCESS_KEY` - Picovoice wake word key
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_JWT_SECRET` - Supabase JWT secret
- `SUPABASE_SERVICE_ROLE_KEY` - Supabase service role key

## Local Development

```bash
pip install -r requirements.txt
python -m src.api.websocket_server
```

## License

MIT
```

### Step 3: Update requirements.txt

Ensure your `requirements.txt` includes all dependencies:

```bash
# Generate up-to-date requirements
pip freeze > requirements.txt
```

Verify these are included:
```txt
fastapi==0.109.0
uvicorn[standard]==0.27.0
websockets==12.0
python-multipart==0.0.6
pydantic==2.5.3
pydantic-settings==2.1.0
python-jose[cryptography]==3.3.0
pyjwt==2.8.0
google-generativeai==0.3.2
elevenlabs==0.2.26
openai==1.10.0
supabase==2.3.0
chromadb==0.4.22
mem0ai==0.0.9
playwright==1.41.0
psutil==5.9.7
pyautogui==0.9.54
```

### Step 4: Create .dockerignore

Create `.dockerignore` in project root:

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.venv/
ENV/

# Data
data/*.db
data/*.db-*
*.sqlite
*.sqlite3

# Secrets
.env
.env.local
.env.production
config/google_token.json
config/google_credentials.json

# IDE
.vscode/
.idea/
*.swp
*.swo

# Git
.git/
.gitignore

# Node
web/node_modules/
web/.next/
web/out/

# Logs
*.log
logs/

# OS
.DS_Store
Thumbs.db
```

---

## Part 2: Deploy to Hugging Face Spaces

### Step 1: Set Up Your Space

Your space is already created at: https://huggingface.co/spaces/AbdullahMalik17/VoiceAssistant17

1. Go to your space
2. Click **"Settings"** tab

### Step 2: Configure Space Settings

1. **Space SDK:** Docker
2. **Space hardware:** CPU basic (free) or upgrade to GPU if needed
3. **Visibility:** Public or Private
4. **Sleep time:** 48 hours (free tier)

### Step 3: Add Environment Variables (Secrets)

1. Go to **Settings** → **Variables and secrets**
2. Click **"New secret"** for each:

```bash
# AI Services (Required)
GEMINI_API_KEY=your-gemini-key-here
ELEVENLABS_API_KEY=your-elevenlabs-key
PICOVOICE_ACCESS_KEY=your-picovoice-key
OPENAI_API_KEY=your-openai-key

# Supabase (Required)
SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
SUPABASE_JWT_SECRET=your-jwt-secret
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Configuration
ENABLE_CONVERSATION_PERSISTENCE=true
CONVERSATION_RETENTION_DAYS=30

# CORS (Important!)
CORS_ORIGINS=https://your-app.vercel.app,http://localhost:3000
```

3. Click **"Save"** for each secret

### Step 4: Push Code to Hugging Face

**Option A: Via Git (Recommended)**

```bash
# Add HF remote
git remote add hf https://huggingface.co/spaces/AbdullahMalik17/VoiceAssistant17

# Or if already exists, update URL
git remote set-url hf https://huggingface.co/spaces/AbdullahMalik17/VoiceAssistant17

# Ensure you're on main branch
git checkout main

# Add all files
git add Dockerfile README.md requirements.txt .dockerignore

# Commit
git commit -m "Deploy FastAPI backend with Docker"

# Push to HF
git push hf main
```

**Option B: Via Hugging Face Web Interface**

1. Go to your space: https://huggingface.co/spaces/AbdullahMalik17/VoiceAssistant17
2. Click **"Files"** tab
3. Click **"Add file"** → **"Upload files"**
4. Upload:
   - Dockerfile
   - README.md
   - requirements.txt
   - .dockerignore
   - All `src/` directory files
5. Commit changes

### Step 5: Wait for Build

1. Go to **"Logs"** tab in your space
2. Watch the Docker build process (takes 5-10 minutes first time)
3. Wait for: `Application startup complete`
4. Check status indicator turns green

### Step 6: Verify Deployment

Test health endpoint:
```bash
curl https://abdullahmalik17-voiceassistant17.hf.space/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "services": {
    "llm": true,
    "tts": true,
    "memory": true,
    "agents": true
  }
}
```

---

## Part 3: Configure Frontend for HF Backend

### Step 1: Update Environment Variables

In your `web/.env.local` (for local testing):

```bash
# Supabase (same as before)
NEXT_PUBLIC_SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key

# NextAuth (same as before)
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your-secret

# Backend API - UPDATE THESE TO YOUR HF SPACE
NEXT_PUBLIC_API_URL=https://abdullahmalik17-voiceassistant17.hf.space
NEXT_PUBLIC_WS_URL=wss://abdullahmalik17-voiceassistant17.hf.space/ws/voice
```

### Step 2: Update Vercel Environment Variables

1. Go to [Vercel Dashboard](https://vercel.com/dashboard)
2. Select your project
3. Go to **Settings** → **Environment Variables**
4. Update or add:

```bash
NEXT_PUBLIC_API_URL=https://abdullahmalik17-voiceassistant17.hf.space
NEXT_PUBLIC_WS_URL=wss://abdullahmalik17-voiceassistant17.hf.space/ws/voice
```

5. Redeploy frontend

### Step 3: Update CORS in HF Space

1. Go to your HF Space settings
2. Update `CORS_ORIGINS` secret:

```bash
CORS_ORIGINS=https://your-app.vercel.app,https://your-app-*.vercel.app,http://localhost:3000
```

3. Wait for space to rebuild (automatic)

---

## Part 4: Hugging Face Spaces Specific Configuration

### Persistent Storage

**Important:** HF Spaces free tier does NOT have persistent storage!

**Options:**

**Option 1: Use Supabase Only (Recommended)**
- Disable SQLite, use only Supabase for conversation storage
- Update `src/api/websocket_server.py` to use Supabase directly

**Option 2: Upgrade to Persistent Storage**
- Upgrade to HF Spaces paid tier ($5/month)
- Get persistent storage mounted at `/data`

**Option 3: Hybrid Approach**
- Keep SQLite for temporary session data
- Sync to Supabase periodically
- Accept that data is lost on space sleep/restart

### Space Sleep/Wake

Free tier spaces sleep after 48 hours of inactivity:
- First request after sleep takes 30-60 seconds to wake up
- All in-memory data is lost on sleep
- Upgrade to "Always On" to prevent sleeping ($9/month)

### Resource Limits

Free tier limits:
- CPU: 2 vCPUs
- RAM: 16GB
- Storage: 50GB (ephemeral)
- Concurrent users: ~10-20

Upgrade options:
- CPU Upgrade: 8 vCPUs, 32GB RAM ($25/month)
- GPU T4: For faster AI processing ($60/month)
- GPU A10G: High performance ($300/month)

---

## Part 5: Testing Production Setup

### Test 1: Health Check

```bash
curl https://abdullahmalik17-voiceassistant17.hf.space/health
```

### Test 2: WebSocket Connection

```javascript
// In browser console on your Vercel frontend
const ws = new WebSocket('wss://abdullahmalik17-voiceassistant17.hf.space/ws/voice?token=YOUR_JWT');

ws.onopen = () => console.log('Connected!');
ws.onmessage = (e) => console.log('Message:', e.data);
ws.onerror = (e) => console.error('Error:', e);
```

### Test 3: Full Flow

1. Go to your Vercel frontend
2. Register/Login
3. Send a message
4. Verify response
5. Check HF Space logs for activity

---

## Part 6: Monitoring and Debugging

### View Logs

1. Go to https://huggingface.co/spaces/AbdullahMalik17/VoiceAssistant17
2. Click **"Logs"** tab
3. See real-time application logs

### Common Issues

**Issue: Space stuck building**

Check Docker logs for errors:
- Missing dependencies in requirements.txt
- Dockerfile syntax errors
- Port conflicts (must use 7860)

**Issue: WebSocket connection fails**

Check:
- URL uses `wss://` (not `ws://`)
- CORS_ORIGINS includes your Vercel domain
- JWT token is valid

**Issue: "Application startup failed"**

Check logs for:
- Missing environment variables
- Import errors
- Port binding issues

### Restart Space

If needed, restart your space:
1. Go to **Settings**
2. Click **"Factory reboot"**
3. Wait 2-3 minutes for rebuild

---

## Part 7: Cost Comparison

### Hugging Face Spaces Pricing

| Tier | Price | Features |
|------|-------|----------|
| **Free** | $0/month | CPU basic, 48h sleep, ephemeral storage |
| **CPU Upgrade** | $25/month | 8 vCPUs, 32GB RAM, same limits |
| **Persistent Storage** | +$5/month | 50GB persistent disk |
| **Always On** | +$9/month | No sleep, guaranteed uptime |
| **GPU T4** | $60/month | GPU acceleration for AI models |

**Recommended for production:** Free + Always On + Persistent = **$14/month**

### vs Render Comparison

| Feature | HF Spaces (Free) | Render (Free) |
|---------|-----------------|---------------|
| Sleep time | 48 hours | 15 minutes |
| Cold start | 30-60s | 30-60s |
| Persistent storage | ❌ | ✅ (1GB) |
| Custom domain | ✅ | ✅ |
| WebSocket support | ✅ | ✅ |
| Community visibility | ✅ High | ❌ Low |

---

## Part 8: Production Checklist

- [ ] Supabase production project created
- [ ] Database migrations run
- [ ] HF Space created and configured
- [ ] All environment secrets added to HF Space
- [ ] Dockerfile created
- [ ] README.md updated with metadata
- [ ] Code pushed to HF Space
- [ ] Build completed successfully
- [ ] Health endpoint responds
- [ ] Frontend deployed to Vercel
- [ ] Vercel env vars updated with HF URLs
- [ ] CORS configured correctly
- [ ] Test registration works
- [ ] Test login and WebSocket connection
- [ ] Test conversation persistence
- [ ] Logs monitored for errors

---

## Part 9: Deployment Commands Quick Reference

```bash
# 1. Create/update files
cat > Dockerfile << 'EOF'
FROM python:3.10-slim
...
EOF

# 2. Commit changes
git add Dockerfile README.md requirements.txt
git commit -m "Deploy to Hugging Face Spaces"

# 3. Add HF remote (if not exists)
git remote add hf https://huggingface.co/spaces/AbdullahMalik17/VoiceAssistant17

# 4. Push to HF
git push hf main

# 5. Test deployment
curl https://abdullahmalik17-voiceassistant17.hf.space/health

# 6. Update Vercel frontend
vercel --prod

# 7. Monitor logs
# Go to: https://huggingface.co/spaces/AbdullahMalik17/VoiceAssistant17/logs
```

---

## Part 10: Next Steps

1. ✅ Set up Supabase (if not done)
2. ✅ Create Dockerfile and README.md
3. ✅ Add secrets to HF Space
4. ✅ Push code to HF Space
5. ✅ Deploy frontend to Vercel
6. ✅ Test authentication flow
7. ⏭️ Monitor usage and upgrade if needed

---

## 🎉 Your URLs

- **Frontend:** https://your-app.vercel.app
- **Backend:** https://abdullahmalik17-voiceassistant17.hf.space
- **Database:** Supabase
- **Space Dashboard:** https://huggingface.co/spaces/AbdullahMalik17/VoiceAssistant17

**Ready to deploy!** 🚀
