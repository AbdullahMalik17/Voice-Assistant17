#!/bin/bash
# Free Deployment Script for Voice Assistant
# This script helps you deploy to Vercel (Frontend) + Render (Backend)

set -e

echo "🚀 Voice Assistant - Free Deployment Script"
echo "==========================================="
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if git repo
if [ ! -d ".git" ]; then
    echo -e "${RED}❌ Not a git repository. Initializing...${NC}"
    git init
    git add .
    git commit -m "Initial commit for deployment"
else
    echo -e "${GREEN}✅ Git repository detected${NC}"
fi

# Check for remote
if ! git remote get-url origin > /dev/null 2>&1; then
    echo -e "${BLUE}📝 Please enter your GitHub repository URL:${NC}"
    read -p "URL (e.g., https://github.com/username/Voice_Assistant.git): " repo_url
    git remote add origin "$repo_url"
    echo -e "${GREEN}✅ Remote added${NC}"
fi

# Push to GitHub
echo -e "${BLUE}📤 Pushing to GitHub...${NC}"
git push -u origin main || git push -u origin master

echo ""
echo -e "${GREEN}✅ Code pushed to GitHub!${NC}"
echo ""

# Deployment instructions
echo "=========================================="
echo "🎯 Next Steps:"
echo "=========================================="
echo ""
echo "📦 STEP 1: Deploy Backend to Render (FREE)"
echo "   1. Go to: https://render.com"
echo "   2. Sign up with GitHub"
echo "   3. Click 'New +' → 'Blueprint'"
echo "   4. Connect your repository"
echo "   5. Render detects render.yaml automatically"
echo "   6. Click 'Apply'"
echo "   7. Add Environment Variables in Dashboard:"
echo "      - GEMINI_API_KEY: your-key-here"
echo "      - OPENAI_API_KEY: your-key-here (optional)"
echo "      - ELEVENLABS_API_KEY: your-key-here (optional)"
echo "   8. Wait 5-10 minutes for build"
echo "   9. Copy backend URL (e.g., https://voice-assistant-backend.onrender.com)"
echo ""

echo "🌐 STEP 2: Deploy Frontend to Vercel (FREE)"
echo "   Run these commands:"
echo ""
echo "   cd web"
echo "   npm install -g vercel"
echo "   vercel login"
echo "   vercel"
echo ""
echo "   Then in Vercel Dashboard:"
echo "   1. Go to Project → Settings → Environment Variables"
echo "   2. Add:"
echo "      NEXT_PUBLIC_WS_URL: wss://YOUR-BACKEND.onrender.com/ws/voice"
echo "      NEXT_PUBLIC_API_URL: https://YOUR-BACKEND.onrender.com"
echo "   3. Redeploy: vercel --prod"
echo ""

echo "🔄 STEP 3: Keep Backend Alive (Optional)"
echo "   1. Go to: https://uptimerobot.com"
echo "   2. Add HTTP(s) monitor"
echo "   3. URL: https://YOUR-BACKEND.onrender.com/health"
echo "   4. Interval: 5 minutes"
echo ""

echo "=========================================="
echo -e "${GREEN}✨ Your Voice Assistant will be live soon!${NC}"
echo "=========================================="
echo ""
echo "📖 For detailed instructions, see: DEPLOYMENT.md"
echo ""
