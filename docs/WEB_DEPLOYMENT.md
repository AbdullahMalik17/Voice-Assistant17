# Web Interface Deployment Guide

This guide explains how to run and deploy the Voice Assistant web interface globally.

## Quick Start (Local Development)

### 1. Start the Backend API Server

```bash
# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies (if not already done)
pip install -r requirements.txt

# Start the WebSocket server
python -m uvicorn src.api.websocket_server:app --reload --host 0.0.0.0 --port 8000
```

### 2. Start the Next.js Frontend

```bash
# Navigate to web directory
cd web

# Install dependencies
npm install

# Copy environment file
cp .env.local.example .env.local

# Start development server
npm run dev
```

### 3. Access the Application

Open http://localhost:3000 in your browser.

## Alternative Wake Word (No Picovoice Required)

The web interface uses **Push-to-Talk** instead of wake word detection:

- **Hold Space Bar**: Press and hold to speak
- **Click and Hold Mic Button**: Alternative to keyboard
- **Touch and Hold**: For mobile devices

This eliminates the need for Picovoice API keys while providing a reliable voice input method.

## Docker Deployment

### Development with Docker

```bash
# Navigate to docker directory
cd docker

# Create .env file with your API keys
cat > .env << EOF
GEMINI_API_KEY=your-gemini-api-key
OPENAI_API_KEY=your-openai-api-key
ELEVENLABS_API_KEY=your-elevenlabs-api-key
EOF

# Build and start all services
docker-compose up --build

# Access at http://localhost (nginx) or http://localhost:3000 (direct)
```

### Production Deployment

```bash
# Set environment variables
export DOMAIN=yourdomain.com
export GEMINI_API_KEY=your-key
export CORS_ORIGINS=https://yourdomain.com

# Build and deploy
docker-compose -f docker-compose.yml up -d --build
```

## Cloud Deployment Options

### Option 1: Vercel (Frontend) + Railway/Render (Backend)

**Frontend (Vercel):**
```bash
cd web
npx vercel --prod
```

**Backend (Railway):**
1. Connect your GitHub repository
2. Set environment variables (API keys)
3. Deploy from docker/Dockerfile.backend

### Option 2: DigitalOcean App Platform

1. Create a new app
2. Connect your repository
3. Configure both frontend and backend services
4. Set environment variables
5. Deploy

### Option 3: AWS ECS

```bash
# Build and push images
docker build -f docker/Dockerfile.backend -t voice-assistant-backend .
docker build -f docker/Dockerfile.frontend -t voice-assistant-frontend .

# Push to ECR
aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_URL
docker tag voice-assistant-backend:latest $ECR_URL/voice-assistant-backend:latest
docker push $ECR_URL/voice-assistant-backend:latest
```

### Option 4: Self-Hosted VPS

```bash
# On your VPS (Ubuntu)
# Install Docker
curl -fsSL https://get.docker.com | sh

# Clone repository
git clone https://github.com/your-org/voice-assistant
cd voice-assistant

# Configure environment
cp docker/.env.example docker/.env
# Edit docker/.env with your API keys

# Deploy
cd docker
docker-compose up -d

# Set up SSL with Let's Encrypt
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

## Environment Variables

### Backend (.env)
```bash
# Required API Keys
GEMINI_API_KEY=your-gemini-api-key
OPENAI_API_KEY=your-openai-api-key  # Optional
ELEVENLABS_API_KEY=your-elevenlabs-api-key  # Optional

# Service Modes
STT_MODE=api  # local, api, or hybrid
LLM_MODE=api  # local, api, or hybrid
TTS_MODE=api  # local, api, or hybrid

# CORS (for production)
CORS_ORIGINS=https://yourdomain.com
```

### Frontend (.env.local)
```bash
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/voice
NEXT_PUBLIC_API_URL=http://localhost:8000

# For production with SSL
NEXT_PUBLIC_WS_URL=wss://yourdomain.com/ws/voice
NEXT_PUBLIC_API_URL=https://yourdomain.com
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         BROWSER                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    Next.js Frontend                       │  │
│  │  • Push-to-Talk voice recording                          │  │
│  │  • Real-time WebSocket chat                              │  │
│  │  • Audio playback for TTS responses                      │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │ WebSocket (wss://)
                             │ REST API (https://)
┌────────────────────────────┼────────────────────────────────────┐
│                         NGINX                                    │
│            (Reverse Proxy + SSL Termination)                     │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────┼────────────────────────────────────┐
│                    FastAPI Backend                               │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  WebSocket Handler → Session Manager → Voice Pipeline     │  │
│  │                                                           │  │
│  │  STT → Intent → Memory → Planner → Tools → LLM → TTS     │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Troubleshooting

### WebSocket Connection Failed
- Check CORS settings in backend
- Ensure WebSocket URL matches backend host
- Check if nginx is properly proxying /ws/* routes

### Audio Recording Not Working
- Grant microphone permissions in browser
- Use HTTPS in production (required for getUserMedia)
- Check browser console for errors

### Backend Services Unavailable
- Verify API keys are set correctly
- Check Docker container logs: `docker-compose logs -f backend`
- Ensure all dependencies are installed

### High Latency
- Use API mode for STT/LLM/TTS for faster responses
- Consider deploying backend closer to users
- Enable response caching where appropriate
