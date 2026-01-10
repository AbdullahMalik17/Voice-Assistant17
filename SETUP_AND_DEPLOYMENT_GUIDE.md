# Voice Assistant - Complete Setup & Deployment Guide

**Status**: Production-Ready
**Last Updated**: 2026-01-10
**Phases Completed**: 1A-E, 2A-D, 3A-C

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Environment Configuration](#environment-configuration)
4. [Running Tests](#running-tests)
5. [Local Development](#local-development)
6. [Production Deployment](#production-deployment)
7. [Monitoring & Debugging](#monitoring--debugging)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements
- **Python**: 3.10+ (required for latest sentence-transformers)
- **Node.js**: 18+ (for frontend)
- **RAM**: 4GB minimum (8GB+ recommended for spaCy models)
- **Disk**: 2GB free (for models and dependencies)
- **OS**: Windows, macOS, or Linux

### API Keys Required

| Service | Purpose | How to Get |
|---------|---------|-----------|
| **Slack** | Send messages to Slack channels/DMs | [Slack Apps](https://api.slack.com/apps) |
| **Discord** | Send messages to Discord channels | [Discord Developers](https://discord.com/developers/applications) |
| **Notion** | Create/update Notion pages | [Notion Integrations](https://www.notion.so/my-integrations) |
| **Trello** | Manage Trello boards/cards | [Trello API Keys](https://trello.com/app-key) |
| **OpenAI** | Speech-to-text (Whisper) | [OpenAI API Keys](https://platform.openai.com/api-keys) |
| **Google Gemini** | LLM responses | [Google AI Studio](https://makersuite.google.com/app/apikey) |
| **ElevenLabs** | Text-to-speech voices | [ElevenLabs Dashboard](https://elevenlabs.io/subscription) |

---

## Installation

### Step 1: Clone Repository

```bash
git clone https://github.com/your-org/voice-assistant.git
cd voice-assistant
```

### Step 2: Create Python Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Backend Dependencies

```bash
# Install all production dependencies
pip install -r requirements.txt

# Download spaCy language model (for entity extraction)
python -m spacy download en_core_web_sm

# Install Playwright browsers
playwright install
```

### Step 4: Install Frontend Dependencies

```bash
cd web
npm install
cd ..
```

### Step 5: Initialize Playwright (Browser Automation)

```bash
# Download Chromium browser for automation
python -m playwright install chromium
```

---

## Environment Configuration

### Step 1: Create Environment Files

Copy the template to actual environment files:

```bash
# Backend environment
cp config/.env.template config/.env

# Frontend environment
cp web/.env.example web/.env.local

# Production environment (for deployment)
cp .env.production.template .env.production
```

### Step 2: Configure Backend (.env)

Edit `config/.env` and fill in your API keys:

```bash
# API Keys (Minimal setup - only Gemini required)
GEMINI_API_KEY=your-gemini-api-key
OPENAI_API_KEY=your-openai-api-key  # For Whisper (speech-to-text)
ELEVENLABS_API_KEY=your-elevenlabs-api-key  # For TTS

# Integration APIs (Optional - add as needed)
SLACK_BOT_TOKEN=xoxb-your-token
DISCORD_BOT_TOKEN=your-token
NOTION_API_KEY=secret_your-key
TRELLO_API_KEY=your-key
TRELLO_API_TOKEN=your-token

# Performance Settings
ENABLE_LLM_CACHE=true
ENABLE_STREAMING=true
LLM_CACHE_TTL=1800

# Browser Automation
BROWSER_ENABLE_CACHE=true
BROWSER_CACHE_TTL_SECONDS=300

# Voice Commands & Memory
ENABLE_SUMMARIZATION=true
ENABLE_SPACY_NER=true
ENABLE_FUZZY_MATCHING=true
```

### Step 3: Configure Frontend (.env.local)

Edit `web/.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

### Step 4: Verify Configuration

```bash
# Check that all required env vars are set
python scripts/verify_config.py
```

---

## Running Tests

### Step 1: Install Test Dependencies

```bash
pip install -r requirements.txt  # Already includes pytest, pytest-asyncio, etc.
```

### Step 2: Run Unit Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test module
pytest tests/services/test_slack_tools.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

### Step 3: Run Integration Tests

```bash
# Test actual integrations (requires real API keys)
pytest tests/integration/ -v --integration

# Test Phase 1 integrations (Slack, Discord, Notion, Trello)
pytest tests/integration/test_slack_integration.py -v
pytest tests/integration/test_discord_integration.py -v
pytest tests/integration/test_notion_integration.py -v
pytest tests/integration/test_trello_integration.py -v

# Test Phase 2 features
pytest tests/integration/test_llm_caching.py -v
pytest tests/integration/test_streaming.py -v

# Test Phase 3 features
pytest tests/integration/test_conversation_summarization.py -v
pytest tests/integration/test_entity_extraction.py -v
pytest tests/integration/test_voice_commands.py -v
```

### Step 4: Run Browser Automation Tests

```bash
# Test browser automation with performance optimizations
pytest tests/services/test_browser_automation.py -v

# Test with specific scenarios
pytest tests/services/test_browser_automation.py::test_navigation_caching -v
pytest tests/services/test_browser_automation.py::test_retry_logic -v
pytest tests/services/test_browser_automation.py::test_form_filling -v
```

### Step 5: Test Coverage Report

```bash
# Generate HTML coverage report
pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

**Target Coverage**: 80%+ for production-critical code

---

## Local Development

### Step 1: Start Backend Server

```bash
# Start with auto-reload
cd src
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Or use the run script
python run_backend.py
```

Backend will be available at: `http://localhost:8000`

### Step 2: Start Frontend Development Server

```bash
cd web
npm run dev
```

Frontend will be available at: `http://localhost:3000`

### Step 3: View API Documentation

Open browser: `http://localhost:8000/docs` (Swagger UI)
Alternative: `http://localhost:8000/redoc` (ReDoc)

### Step 4: Monitor Logs

```bash
# Stream backend logs
tail -f logs/voice_assistant.log

# Stream with filtering
tail -f logs/voice_assistant.log | grep "ERROR\|WARN"
```

### Step 5: Test WebSocket Connection

```bash
# Use provided WebSocket testing tool
python scripts/test_websocket.py

# Or use websocat
websocat ws://localhost:8000/ws/test-session-123
```

---

## Production Deployment

### Option 1: Deploy to HuggingFace Spaces

**Pros**: Free tier, no credit card, auto-scaling
**Cons**: Limited resources, public by default

#### Steps:

1. **Create HuggingFace Space**:
   ```bash
   # Go to https://huggingface.co/spaces/create
   # Name: voice-assistant
   # License: openrail
   # Space SDK: Docker
   ```

2. **Create Dockerfile**:
   ```dockerfile
   FROM python:3.11-slim

   WORKDIR /app

   COPY requirements.txt .
   RUN pip install -r requirements.txt && \
       python -m spacy download en_core_web_sm && \
       python -m playwright install chromium

   COPY src/ ./src/
   COPY config/ ./config/

   CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "7860"]
   ```

3. **Set Environment Variables**:
   - Go to Space Settings → Secrets
   - Add all API keys from `config/.env`

4. **Push to HuggingFace**:
   ```bash
   git add Dockerfile requirements.txt src/ config/
   git commit -m "Deploy to HuggingFace Spaces"
   git push --force huggingface main
   ```

### Option 2: Deploy to Vercel (Frontend + Serverless API)

**Pros**: Serverless, auto-scaling, free tier
**Cons**: Cold starts, function time limits

#### Steps:

1. **Install Vercel CLI**:
   ```bash
   npm install -g vercel
   ```

2. **Configure Backend as Serverless Function**:
   ```bash
   # Create api/ directory in root
   mkdir api
   ```

3. **Create API handler** (`api/[route].ts`):
   ```typescript
   import { createServerAdapter } from '@hattip/adapter-node'
   import app from '../src/main'  // Export FastAPI app as ASGI

   export default createServerAdapter(app)
   ```

4. **Deploy**:
   ```bash
   cd web
   vercel
   ```

5. **Configure environment variables**:
   ```bash
   vercel env add GEMINI_API_KEY
   vercel env add SLACK_BOT_TOKEN
   # ... add all other keys
   ```

### Option 3: Deploy to Docker + Cloud VM (AWS/GCP/Azure)

**Pros**: Full control, auto-scaling options, unlimited resources
**Cons**: Requires DevOps knowledge, costs money

#### Steps:

1. **Build Docker Image**:
   ```bash
   docker build -t voice-assistant:latest .
   ```

2. **Push to Registry**:
   ```bash
   # AWS ECR
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
   docker tag voice-assistant:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/voice-assistant:latest
   docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/voice-assistant:latest
   ```

3. **Deploy to Kubernetes** (optional):
   ```bash
   kubectl apply -f deployment.yaml
   ```

---

## Monitoring & Debugging

### View System Metrics

```bash
# Check Python memory usage
python -c "import psutil; print(f'Memory: {psutil.virtual_memory().percent}%')"

# Monitor in real-time
watch -n 1 'python -c "import psutil; print(f\"Memory: {psutil.virtual_memory().percent}%\")"'
```

### Access Prometheus Metrics

```
http://localhost:9090/metrics
```

Key metrics to monitor:
- `llm_response_time_ms` - LLM latency
- `llm_cache_hit_rate` - Cache effectiveness
- `websocket_connections_active` - Connected users
- `browser_automation_success_rate` - Tool reliability

### View Logs

```bash
# All logs
tail -f logs/voice_assistant.log

# Error logs only
tail -f logs/voice_assistant.log | grep ERROR

# Specific service
tail -f logs/voice_assistant.log | grep "slack_tools\|discord_tools"

# Real-time with color
tail -f logs/voice_assistant.log | ccze -A
```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python -m uvicorn src.main:app --reload

# Enable integration debugging
export DEBUG_INTEGRATIONS=true
```

---

## Troubleshooting

### Issue: Dependencies Installation Fails

**Solution**:
```bash
# Update pip
pip install --upgrade pip setuptools wheel

# Try installing without cache
pip install --no-cache-dir -r requirements.txt

# For specific package failures
pip install --verbose slack-sdk
```

### Issue: spaCy Model Not Found

**Solution**:
```bash
# Download the model
python -m spacy download en_core_web_sm

# Verify installation
python -c "import spacy; nlp = spacy.load('en_core_web_sm'); print('✓ spaCy model loaded')"
```

### Issue: Slack/Discord Messages Not Sending

**Solution**:
```bash
# Verify token is valid
python -c "from slack_sdk import WebClient; client = WebClient(token='YOUR_TOKEN'); client.auth_test()"

# Check error logs
tail -f logs/voice_assistant.log | grep -i "slack\|discord"

# Test with debug
export DEBUG_INTEGRATIONS=true
```

### Issue: Browser Automation Times Out

**Solution**:
```bash
# Check browser is installed
python -m playwright install chromium --with-deps

# Verify browser automation
python scripts/test_browser_automation.py

# Increase timeout
export BROWSER_TIMEOUT=30000  # 30 seconds
```

### Issue: LLM Cache Not Working

**Solution**:
```bash
# Verify cache is enabled
python -c "import os; print(f'Cache enabled: {os.getenv(\"ENABLE_LLM_CACHE\")}')"

# Check Redis connection (if using Redis)
redis-cli ping  # Should print PONG

# Clear cache and restart
python -c "from src.services.llm_cache import LLMCache; LLMCache().clear()"
```

### Issue: WebSocket Connection Drops

**Solution**:
```bash
# Test connection stability
python scripts/test_websocket_stability.py --duration 60

# Check rate limiting
export RATE_LIMIT_REQUESTS=100  # Increase from default 30

# Monitor connection logs
tail -f logs/voice_assistant.log | grep -i "websocket\|connection"
```

### Issue: Out of Memory

**Solution**:
```bash
# Check memory usage
python scripts/check_memory.py

# Reduce cache size
export LLM_CACHE_TTL=600  # Reduce from 1800

# Limit concurrent connections
export MAX_WEBSOCKET_CONNECTIONS=500

# Run memory profiler
python -m memory_profiler src/main.py
```

---

## Performance Optimization Checklist

- [ ] LLM caching enabled (`ENABLE_LLM_CACHE=true`)
- [ ] Streaming responses enabled (`ENABLE_STREAMING=true`)
- [ ] Browser automation cache enabled (`BROWSER_ENABLE_CACHE=true`)
- [ ] Redis configured for high-traffic (if needed)
- [ ] Rate limiting configured (`RATE_LIMIT_REQUESTS=30`)
- [ ] Conversation summarization enabled (`ENABLE_SUMMARIZATION=true`)
- [ ] Entity extraction using spaCy (`ENABLE_SPACY_NER=true`)
- [ ] Fuzzy matching enabled (`ENABLE_FUZZY_MATCHING=true`)

---

## Production Readiness Checklist

### Code Quality
- [ ] All tests passing (target: 80%+ coverage)
- [ ] No security vulnerabilities (run `pip audit`)
- [ ] Code linted (Black, flake8, mypy)
- [ ] All PR reviews completed

### Performance
- [ ] LLM response latency <2s (cached <100ms)
- [ ] WebSocket message latency <500ms
- [ ] Browser automation success rate >95%
- [ ] Memory usage <500MB

### Reliability
- [ ] Error handling for all integrations
- [ ] Graceful degradation for optional APIs
- [ ] Comprehensive logging
- [ ] Backup/rollback plan documented

### Security
- [ ] All API keys in environment variables
- [ ] HTTPS enabled in production
- [ ] CORS properly configured
- [ ] Input validation on all endpoints
- [ ] Rate limiting enabled

### Operations
- [ ] Monitoring setup (Prometheus/Grafana)
- [ ] Log aggregation (optional but recommended)
- [ ] Alerting configured
- [ ] Runbooks written
- [ ] On-call rotation established

---

## Quick Start Commands

```bash
# Fresh setup
python scripts/setup.sh

# Run tests
pytest tests/ -v

# Start local development
./start_dev.sh

# Deploy to HuggingFace
git push huggingface main

# Deploy to Vercel
cd web && vercel

# Monitor production
python scripts/monitor.py

# Troubleshoot
python scripts/diagnose.py
```

---

## Support & Resources

- **Documentation**: `/docs`
- **API Reference**: `http://localhost:8000/docs`
- **Architecture Decision Records**: `history/adr/`
- **Implementation Details**: `IMPLEMENTATION_SUMMARY.md`
- **Phase Documentation**:
  - Phase 1: `INTEGRATION_TOOLS_SUMMARY.md`
  - Phase 2A: `LLM_CACHING_IMPLEMENTATION.md`
  - Phase 2B: `STREAMING_RESPONSES_IMPLEMENTATION.md`
  - Phase 2C: `WEBSOCKET_OPTIMIZATION_IMPLEMENTATION.md`
  - Phase 2D: `BROWSER_AUTOMATION_PERFORMANCE.md`

---

**Status**: ✅ READY FOR PRODUCTION DEPLOYMENT

All phases implemented and tested. Follow this guide for smooth deployment.
