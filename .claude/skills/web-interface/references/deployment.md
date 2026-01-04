# Deployment Guide

Complete deployment configuration for Voice Assistant with Docker.

## Table of Contents
1. [Docker Setup](#docker-setup)
2. [Production Configuration](#production-configuration)
3. [Cloud Deployment](#cloud-deployment)
4. [SSL/TLS Setup](#ssl-tls-setup)

## Docker Setup

### Directory Structure

```
voice-assistant/
├── docker/
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   ├── docker-compose.yml
│   ├── docker-compose.prod.yml
│   └── nginx/
│       ├── nginx.conf
│       └── ssl/
├── src/                 # Python backend
├── web/                 # Next.js frontend
└── config/
```

### Backend Dockerfile (`docker/Dockerfile.backend`)

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    portaudio19-dev \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install uvicorn gunicorn

# Copy application code
COPY src/ ./src/
COPY config/ ./config/

# Environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["gunicorn", "src.api.websocket_server:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
```

### Frontend Dockerfile (`docker/Dockerfile.frontend`)

```dockerfile
# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

COPY web/package*.json ./
RUN npm ci

COPY web/ .

ARG NEXT_PUBLIC_WS_URL
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_WS_URL=$NEXT_PUBLIC_WS_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

RUN npm run build

# Production stage
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
```

### Docker Compose (`docker/docker-compose.yml`)

```yaml
version: '3.8'

services:
  backend:
    build:
      context: ..
      dockerfile: docker/Dockerfile.backend
    container_name: voice-assistant-backend
    ports:
      - "8000:8000"
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ELEVENLABS_API_KEY=${ELEVENLABS_API_KEY}
      - STT_MODE=api
      - LLM_MODE=api
      - TTS_MODE=api
    volumes:
      - ../config:/app/config:ro
      - voice-data:/app/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
    networks:
      - voice-network

  frontend:
    build:
      context: ..
      dockerfile: docker/Dockerfile.frontend
      args:
        - NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/voice
        - NEXT_PUBLIC_API_URL=http://localhost:8000
    container_name: voice-assistant-frontend
    ports:
      - "3000:3000"
    depends_on:
      backend:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - voice-network

  # Optional: nginx reverse proxy
  nginx:
    image: nginx:alpine
    container_name: voice-assistant-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
    depends_on:
      - frontend
      - backend
    restart: unless-stopped
    networks:
      - voice-network

volumes:
  voice-data:

networks:
  voice-network:
    driver: bridge
```

### Production Docker Compose (`docker/docker-compose.prod.yml`)

```yaml
version: '3.8'

services:
  backend:
    build:
      context: ..
      dockerfile: docker/Dockerfile.backend
    container_name: voice-backend-prod
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - CORS_ORIGINS=${CORS_ORIGINS}
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '2'
          memory: 4G
    restart: always
    networks:
      - voice-network

  frontend:
    build:
      context: ..
      dockerfile: docker/Dockerfile.frontend
      args:
        - NEXT_PUBLIC_WS_URL=wss://${DOMAIN}/ws/voice
        - NEXT_PUBLIC_API_URL=https://${DOMAIN}
    container_name: voice-frontend-prod
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '1'
          memory: 1G
    restart: always
    networks:
      - voice-network

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.prod.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - ./nginx/certbot:/var/www/certbot:ro
    depends_on:
      - frontend
      - backend
    restart: always
    networks:
      - voice-network

networks:
  voice-network:
    driver: bridge
```

### Nginx Configuration (`docker/nginx/nginx.conf`)

```nginx
events {
    worker_connections 1024;
}

http {
    upstream backend {
        server backend:8000;
    }

    upstream frontend {
        server frontend:3000;
    }

    server {
        listen 80;
        server_name localhost;

        # Frontend
        location / {
            proxy_pass http://frontend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_cache_bypass $http_upgrade;
        }

        # Backend API
        location /api {
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }

        # WebSocket
        location /ws {
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_read_timeout 86400;
        }

        # Health check
        location /health {
            proxy_pass http://backend/health;
        }
    }
}
```

## Running with Docker

### Development

```bash
# Build and run
cd docker
docker-compose up --build

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Production

```bash
# Create .env file with secrets
cat > .env << EOF
GEMINI_API_KEY=your-key
DOMAIN=yourdomain.com
CORS_ORIGINS=https://yourdomain.com
EOF

# Build and run
docker-compose -f docker-compose.prod.yml up --build -d
```

## Cloud Deployment Options

### Option 1: AWS ECS/Fargate

```bash
# Push images to ECR
aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_URL
docker tag voice-backend:latest $ECR_URL/voice-backend:latest
docker push $ECR_URL/voice-backend:latest

# Deploy with ECS task definition
aws ecs update-service --cluster voice-cluster --service voice-service --force-new-deployment
```

### Option 2: Google Cloud Run

```bash
# Backend
gcloud run deploy voice-backend \
    --image gcr.io/$PROJECT/voice-backend \
    --platform managed \
    --allow-unauthenticated \
    --set-env-vars GEMINI_API_KEY=$GEMINI_API_KEY

# Frontend
gcloud run deploy voice-frontend \
    --image gcr.io/$PROJECT/voice-frontend \
    --platform managed \
    --allow-unauthenticated
```

### Option 3: DigitalOcean App Platform

Create `app.yaml`:

```yaml
name: voice-assistant
services:
  - name: backend
    dockerfile_path: docker/Dockerfile.backend
    http_port: 8000
    envs:
      - key: GEMINI_API_KEY
        scope: RUN_TIME
        type: SECRET

  - name: frontend
    dockerfile_path: docker/Dockerfile.frontend
    http_port: 3000
    build_command: npm run build
```

### Option 4: Self-Hosted with VPS

```bash
# On your VPS (Ubuntu)
# Install Docker
curl -fsSL https://get.docker.com | sh

# Clone and deploy
git clone https://github.com/your-org/voice-assistant
cd voice-assistant/docker
docker-compose -f docker-compose.prod.yml up -d

# Set up SSL with certbot
sudo apt install certbot
sudo certbot certonly --webroot -w /var/www/certbot -d yourdomain.com
```

## SSL/TLS Setup

### Using Let's Encrypt

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renewal
sudo systemctl enable certbot.timer
```

### Nginx with SSL (`docker/nginx/nginx.prod.conf`)

```nginx
events {
    worker_connections 1024;
}

http {
    # SSL settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;

    upstream backend {
        server backend:8000;
    }

    upstream frontend {
        server frontend:3000;
    }

    # Redirect HTTP to HTTPS
    server {
        listen 80;
        server_name yourdomain.com;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name yourdomain.com;

        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;

        location / {
            proxy_pass http://frontend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
        }

        location /api {
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /ws {
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_read_timeout 86400;
        }
    }
}
```
