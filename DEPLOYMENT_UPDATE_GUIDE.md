# Deployment Update Guide - Vercel & HuggingFace Spaces

**Status**: Update Guide for Existing Deployments
**Date**: 2026-01-10
**Scope**: Backend (HuggingFace) + Frontend (Vercel)

---

## Table of Contents

1. [HuggingFace Spaces Update](#huggingface-spaces-update)
2. [Vercel Frontend Update](#vercel-frontend-update)
3. [Environment Variables](#environment-variables)
4. [Verification Steps](#verification-steps)
5. [Rollback Procedures](#rollback-procedures)

---

## HuggingFace Spaces Update

### Step 1: Verify Your Current HuggingFace Space

```bash
# Check if you have git access configured
git remote -v

# You should see something like:
# huggingface https://huggingface.co/spaces/YOUR-USERNAME/voice-assistant.git (fetch)
# huggingface https://huggingface.co/spaces/YOUR-USERNAME/voice-assistant.git (push)
```

If not configured:
```bash
git remote add huggingface https://huggingface.co/spaces/YOUR-USERNAME/voice-assistant.git
```

**Replace `YOUR-USERNAME` with your HuggingFace username**

---

### Step 2: Update Your Dockerfile (Backend)

**File**: `Dockerfile` (in project root)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt && \
    python -m spacy download en_core_web_sm && \
    python -m playwright install chromium && \
    python -m playwright install-deps

# Copy application code
COPY src/ ./src/
COPY config/ ./config/

# Create logs directory
RUN mkdir -p logs

# Expose port (HuggingFace uses 7860)
EXPOSE 7860

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:7860/health', timeout=5)"

# Run application on HuggingFace port
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "7860"]
```

**Note**: HuggingFace Spaces uses port **7860**, not 8000

---

### Step 3: Prepare Files for HuggingFace Update

```bash
# 1. Ensure all code is committed locally
git status

# 2. Add new files from this implementation
git add src/agents/slack_tools.py
git add src/agents/discord_tools.py
git add src/agents/notion_tools.py
git add src/agents/trello_tools.py
git add src/services/llm_cache.py
git add src/services/enhanced_entity_extractor.py
git add src/services/advanced_voice_commands.py
git add src/api/websocket_optimization.py
git add src/memory/conversation_summarizer.py

# 3. Add modified files
git add src/agents/tools.py
git add src/agents/browser_tools.py
git add src/services/llm.py
git add src/services/browser_automation.py

# 4. Add configuration files
git add requirements.txt
git add Dockerfile
git add config/.env.template

# 5. Add documentation
git add SETUP_AND_DEPLOYMENT_GUIDE.md
git add TESTING_GUIDE.md
git add IMPLEMENTATION_COMPLETE_SUMMARY.md
git add PROJECT_STATUS_REPORT.md
git add README_IMPLEMENTATION.md
```

---

### Step 4: Commit and Push to HuggingFace

```bash
# Create commit with all enhancements
git commit -m "feat: Add Phase 1-3 enhancements

- Phase 1: 20 integration tools (Slack, Discord, Notion, Trello)
- Phase 2: Performance optimizations (caching, streaming, WebSocket)
- Phase 3: AI features (summarization, entity extraction, voice commands)

This update includes:
✅ LLM response caching (60-80% faster)
✅ Streaming responses (200-500ms first token)
✅ WebSocket optimization (100+ concurrent users)
✅ Browser automation performance (20-30x faster)
✅ Conversation summarization
✅ Enhanced entity extraction
✅ Advanced voice commands

See documentation for details."

# Push to HuggingFace Spaces
git push huggingface main -u
```

**Wait 2-5 minutes** for HuggingFace to build and deploy

---

### Step 5: Verify HuggingFace Deployment

```bash
# Get your HuggingFace Space URL
# Format: https://YOUR-USERNAME-voice-assistant.hf.space

# Test API endpoint (replace with your URL)
curl https://YOUR-USERNAME-voice-assistant.hf.space/health

# Expected response:
# {"status": "ok", "version": "1.0.0"}

# Check OpenAPI docs
# https://YOUR-USERNAME-voice-assistant.hf.space/docs
```

---

### Step 6: Set HuggingFace Environment Variables

1. **Go to your HuggingFace Space**:
   - URL: https://huggingface.co/spaces/YOUR-USERNAME/voice-assistant

2. **Click "Settings" (gear icon)**

3. **Go to "Repository secrets"** section

4. **Add each secret** (click "+ New secret"):

```
Secret Name                 Value
─────────────────────────────────────────────────────
SLACK_BOT_TOKEN            xoxb-your-token-here
SLACK_APP_TOKEN            xapp-your-token-here
DISCORD_BOT_TOKEN          your-discord-token
DISCORD_WEBHOOK_URL        https://discord.com/api/webhooks/...
NOTION_API_KEY             secret_your-notion-key
TRELLO_API_KEY             your-trello-key
TRELLO_API_TOKEN           your-trello-token
GEMINI_API_KEY             your-gemini-key
OPENAI_API_KEY             your-openai-key
ELEVENLABS_API_KEY         your-elevenlabs-key
ENABLE_LLM_CACHE           true
ENABLE_STREAMING           true
BROWSER_ENABLE_CACHE       true
ENABLE_SUMMARIZATION       true
ENABLE_SPACY_NER           true
ENABLE_FUZZY_MATCHING      true
```

5. **Save each secret** (HuggingFace will inject them as environment variables)

---

### Step 7: Restart HuggingFace Space

1. Go to your Space settings
2. Click "Restart Space" button
3. Wait for green "Running" status (2-3 minutes)

---

## Vercel Frontend Update

### Step 1: Verify Vercel Project

```bash
# Check if Vercel CLI is installed
vercel --version

# If not, install:
npm install -g vercel

# Verify you're logged in
vercel whoami
```

---

### Step 2: Update Frontend Environment Variables

**For Vercel Web Interface**:

1. **Go to your Vercel project**: https://vercel.com/dashboard

2. **Select "voice-assistant" project**

3. **Click "Settings"**

4. **Go to "Environment Variables"**

5. **Update these variables**:

```
Variable Name                   Value
──────────────────────────────────────────────────
NEXT_PUBLIC_API_URL            https://YOUR-USERNAME-voice-assistant.hf.space
NEXT_PUBLIC_WS_URL             wss://YOUR-USERNAME-voice-assistant.hf.space
NEXT_PUBLIC_LLM_CACHE_ENABLED  true
NEXT_PUBLIC_STREAMING_ENABLED  true
```

**Replace `YOUR-USERNAME` with your HuggingFace username**

---

### Step 3: Update Frontend Code for Streaming

**File**: `web/src/hooks/useWebSocket.ts`

Add streaming message handler:

```typescript
interface WebSocketMessage {
  type: string;
  content: any;
  session_id: string;
}

export function useWebSocket() {
  const [messages, setMessages] = useState<WebSocketMessage[]>([]);
  const [streamingText, setStreamingText] = useState('');

  const handleMessage = (event: MessageEvent) => {
    const message = JSON.parse(event.data) as WebSocketMessage;

    switch (message.type) {
      case 'RESPONSE_STREAM':
        setStreamingText('');
        break;

      case 'STREAM_CHUNK':
        setStreamingText(prev => prev + message.content.chunk);
        break;

      case 'STREAM_END':
        setMessages(prev => [...prev, {
          type: 'assistant',
          content: streamingText,
          session_id: message.session_id
        }]);
        setStreamingText('');
        break;

      default:
        setMessages(prev => [...prev, message]);
    }
  };

  return { messages, streamingText, handleMessage };
}
```

---

### Step 4: Update Frontend Dependencies

```bash
cd web

# Update package.json with streaming support
npm install fuse.js@7.0.0 --save

# Install/update all dependencies
npm install
```

---

### Step 5: Build and Test Frontend Locally

```bash
cd web

# Build production bundle
npm run build

# Test build locally
npm run start

# Should open http://localhost:3000
# Test streaming by sending a message
```

---

### Step 6: Deploy to Vercel

**Option A: Using Vercel CLI**

```bash
cd web

# Deploy to Vercel
vercel --prod

# Vercel will:
# 1. Ask which project (select "voice-assistant")
# 2. Confirm settings
# 3. Build and deploy
# 4. Show deployment URL

# Takes 2-5 minutes
```

**Option B: Using GitHub (if configured)**

```bash
# If your repo is on GitHub:
git add web/
git commit -m "feat: Add streaming UI and update WebSocket integration"
git push origin main

# Vercel will auto-deploy on push
```

---

### Step 7: Verify Vercel Deployment

```bash
# Your Vercel deployment URL will be:
# https://voice-assistant-YOUR-VERCEL-DOMAIN.vercel.app

# Test it:
curl https://voice-assistant-YOUR-VERCEL-DOMAIN.vercel.app

# Check streaming works:
# 1. Open in browser
# 2. Enable WebSocket connection (check browser console)
# 3. Send a test message
# 4. Verify streaming chunks appear in real-time
```

---

## Environment Variables

### Master List - Configure Both HuggingFace & Vercel

#### HuggingFace Environment Variables (Backend)

**Integration APIs**:
```
SLACK_BOT_TOKEN=xoxb-YOUR-BOT-TOKEN
SLACK_APP_TOKEN=xapp-YOUR-APP-TOKEN
DISCORD_BOT_TOKEN=YOUR-DISCORD-TOKEN
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/ID/TOKEN
NOTION_API_KEY=secret_YOUR-NOTION-KEY
TRELLO_API_KEY=YOUR-KEY
TRELLO_API_TOKEN=YOUR-TOKEN
```

**LLM & Services**:
```
GEMINI_API_KEY=YOUR-GEMINI-KEY
OPENAI_API_KEY=YOUR-OPENAI-KEY
ELEVENLABS_API_KEY=YOUR-ELEVENLABS-KEY
```

**Feature Flags**:
```
ENABLE_LLM_CACHE=true
LLM_CACHE_TTL=1800
ENABLE_STREAMING=true
BROWSER_ENABLE_CACHE=true
BROWSER_CACHE_TTL_SECONDS=300
ENABLE_SUMMARIZATION=true
ENABLE_SPACY_NER=true
ENABLE_FUZZY_MATCHING=true
```

**Optional**:
```
REDIS_URL=redis://localhost:6379/0
USE_REDIS_CACHE=false
RATE_LIMIT_REQUESTS=30
RATE_LIMIT_WINDOW_SECONDS=60
DEBUG_INTEGRATIONS=false
```

#### Vercel Environment Variables (Frontend)

```
NEXT_PUBLIC_API_URL=https://YOUR-USERNAME-voice-assistant.hf.space
NEXT_PUBLIC_WS_URL=wss://YOUR-USERNAME-voice-assistant.hf.space
NEXT_PUBLIC_LLM_CACHE_ENABLED=true
NEXT_PUBLIC_STREAMING_ENABLED=true
```

---

## Verification Steps

### Step 1: Test Backend API

```bash
# Replace with your HuggingFace URL
BACKEND_URL="https://YOUR-USERNAME-voice-assistant.hf.space"

# Test health endpoint
curl $BACKEND_URL/health
# Expected: {"status": "ok"}

# Test API docs accessible
curl $BACKEND_URL/docs
# Should return HTML

# Test Slack tool registration (if token configured)
curl "$BACKEND_URL/api/tools?category=communication"
# Should list Slack, Discord, Notion, Trello tools
```

### Step 2: Test Frontend Deployment

```bash
# Replace with your Vercel URL
FRONTEND_URL="https://voice-assistant-YOUR-VERCEL-DOMAIN.vercel.app"

# Test page loads
curl $FRONTEND_URL

# Open in browser and:
# 1. Check console for WebSocket connection
# 2. Send a test message
# 3. Verify streaming response appears
# 4. Check cache is working (test same query twice)
```

### Step 3: Test Integration Tools

```bash
# Test Slack (requires SLACK_BOT_TOKEN configured)
curl -X POST $BACKEND_URL/api/slack/send \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "#test",
    "message": "Deployment test from API"
  }'

# Expected: success message with message_ts

# Test LLM Cache
curl -X POST $BACKEND_URL/api/llm/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the capital of France?"}'

# Second call should be cached (check response time <100ms)

# Test Streaming
curl -N -X POST $BACKEND_URL/api/llm/stream \
  -H "Content-Type: application/json" \
  -d '{"query": "Tell me a joke"}'

# Should stream chunks in real-time
```

### Step 4: Monitor Performance

```bash
# Check Prometheus metrics
curl $BACKEND_URL/metrics

# Key metrics to verify:
# - llm_cache_hit_rate > 0
# - llm_stream_latency_ms < 500 (first token)
# - websocket_connections_active > 0
# - browser_automation_success_rate > 0.95
```

---

## Rollback Procedures

### Rollback HuggingFace Spaces

If something goes wrong with HuggingFace deployment:

**Option 1: Revert to Previous Commit**

```bash
# Check git log
git log --oneline -5

# Revert to previous version (replace HASH)
git revert HEAD
# or
git reset --hard HASH

# Push to HuggingFace
git push huggingface main -f

# HuggingFace will rebuild from old version (2-3 min)
```

**Option 2: Stop/Restart Space**

1. Go to HuggingFace Space settings
2. Click "Pause space" to stop it
3. Fix the issue locally
4. Push updated code
5. HuggingFace will auto-restart

**Option 3: Manual Rollback (if git is unavailable)**

1. Go to HuggingFace Space
2. Click "Files" tab
3. Edit Dockerfile directly in web UI
4. Remove problematic changes
5. Save - HuggingFace will rebuild

---

### Rollback Vercel

If something goes wrong with Vercel deployment:

**Option 1: Revert to Previous Deployment**

```bash
# Using Vercel CLI
vercel --prod --target production

# Or through Vercel dashboard:
# 1. Go to https://vercel.com/dashboard
# 2. Select "voice-assistant"
# 3. Go to "Deployments"
# 4. Find previous working deployment
# 5. Click "..." menu → "Promote to Production"
```

**Option 2: Git Rollback**

```bash
# Revert to previous commit
git revert HEAD
git push origin main

# Vercel will auto-deploy previous version
```

---

## Deployment Checklist

### Pre-Deployment
- [ ] All code committed locally: `git status`
- [ ] Tests passing: `pytest tests/ -q`
- [ ] Environment variables documented
- [ ] Dockerfile tested locally: `docker build .`
- [ ] Frontend builds: `cd web && npm run build`

### HuggingFace Deployment
- [ ] Files added to git: `git add ...`
- [ ] Commit message meaningful
- [ ] Pushed to HuggingFace: `git push huggingface main`
- [ ] Build succeeded (check Space page)
- [ ] Environment secrets added
- [ ] Space restarted
- [ ] Health check passes: `curl /health`

### Vercel Deployment
- [ ] Environment variables updated
- [ ] Frontend code updated
- [ ] Dependencies installed: `npm install`
- [ ] Build succeeds: `npm run build`
- [ ] Deployed: `vercel --prod`
- [ ] API URL updated in env vars
- [ ] WebSocket connection working

### Post-Deployment
- [ ] Health check passes
- [ ] API docs accessible
- [ ] Frontend loads
- [ ] WebSocket connection works
- [ ] Integration tools respond
- [ ] Cache working (second request faster)
- [ ] Streaming working (chunks appear)
- [ ] Metrics accessible

---

## Common Issues & Solutions

### Issue: HuggingFace Build Fails

**Solution**:
```bash
# Check build logs in HuggingFace web UI
# Common causes:
# 1. Missing system dependencies in Dockerfile
# 2. Incorrect port number (should be 7860)
# 3. Missing requirements

# Fix and redeploy:
git push huggingface main -f
```

### Issue: Vercel Deployment Fails

**Solution**:
```bash
# Check build logs in Vercel dashboard
# Common causes:
# 1. Missing environment variables
# 2. Build errors in Next.js

# Fix:
cd web
npm install
npm run build  # test locally first
vercel --prod
```

### Issue: WebSocket Connection Fails

**Solution**:
```bash
# Check HuggingFace backend is running:
curl https://YOUR-USERNAME-voice-assistant.hf.space/health

# Check frontend env vars (open browser console):
console.log(process.env.NEXT_PUBLIC_WS_URL)
# Should be: wss://YOUR-USERNAME-voice-assistant.hf.space

# If not correct, update in Vercel settings and redeploy
```

### Issue: API Returns 502 Gateway Error

**Solution**:
```bash
# HuggingFace Space likely crashed
# 1. Check Space settings page
# 2. Click "Restart Space"
# 3. Wait for "Running" status (3-5 min)

# If persists:
git push huggingface main -f  # Force rebuild
```

### Issue: Integrations Not Working

**Solution**:
```bash
# Verify environment variables are set:
# 1. Go to HuggingFace Space settings
# 2. Check all API keys in "Repository secrets"
# 3. Restart Space after adding/updating secrets

# Test integration:
curl -X POST https://YOUR-URL/api/slack/test \
  -H "Content-Type: application/json"
```

---

## Deployment Completion Checklist

```
╔═══════════════════════════════════════════════════════╗
║          DEPLOYMENT UPDATE - CHECKLIST                ║
╠═══════════════════════════════════════════════════════╣
║                                                       ║
║  HuggingFace Spaces (Backend)                        ║
║  ├─ [ ] Dockerfile updated                          ║
║  ├─ [ ] Code pushed to HuggingFace                   ║
║  ├─ [ ] Build successful                            ║
║  ├─ [ ] Environment secrets added                   ║
║  ├─ [ ] Space restarted                             ║
║  └─ [ ] Health check passes                         ║
║                                                       ║
║  Vercel (Frontend)                                   ║
║  ├─ [ ] Environment variables updated               ║
║  ├─ [ ] Frontend code built                         ║
║  ├─ [ ] Deployed to production                      ║
║  ├─ [ ] API URL configured                          ║
║  └─ [ ] WebSocket connected                         ║
║                                                       ║
║  Verification                                        ║
║  ├─ [ ] Backend health: curl /health                ║
║  ├─ [ ] Frontend loads: curl /                      ║
║  ├─ [ ] WebSocket works: browser console            ║
║  ├─ [ ] Integrations work: test Slack/Discord       ║
║  ├─ [ ] Cache working: 2nd request <100ms           ║
║  ├─ [ ] Streaming: chunks appear in real-time       ║
║  ├─ [ ] Metrics accessible: /metrics                ║
║  └─ [ ] API docs: /docs                             ║
║                                                       ║
║  DEPLOYMENT COMPLETE ✅                             ║
║                                                       ║
╚═══════════════════════════════════════════════════════╝
```

---

## Need Help?

**HuggingFace Issues**: Check Space Settings → Logs tab
**Vercel Issues**: Check Vercel Dashboard → Deployments → Details
**Git Issues**: `git log` and `git status` to verify state

---

**Deployment Status**: Ready to Update
**Estimated Time**: 30 minutes (both platforms)
**Rollback Time**: 2-3 minutes (if needed)

