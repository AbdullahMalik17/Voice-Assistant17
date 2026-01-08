@echo off
REM Free Deployment Script for Voice Assistant (Windows)
REM This script helps you deploy to Vercel (Frontend) + Render (Backend)

echo ========================================
echo  Voice Assistant - Free Deployment
echo ========================================
echo.

REM Check if git repo
if not exist ".git\" (
    echo [INIT] Initializing git repository...
    git init
    git add .
    git commit -m "Initial commit for deployment"
    echo [OK] Git repository initialized
) else (
    echo [OK] Git repository detected
)

REM Check for remote
git remote get-url origin >nul 2>&1
if errorlevel 1 (
    echo.
    set /p repo_url="Enter GitHub repository URL: "
    git remote add origin %repo_url%
    echo [OK] Remote added
)

REM Push to GitHub
echo.
echo [PUSH] Pushing to GitHub...
git push -u origin main
if errorlevel 1 (
    git push -u origin master
)

echo.
echo [SUCCESS] Code pushed to GitHub!
echo.

REM Deployment instructions
echo ========================================
echo  NEXT STEPS:
echo ========================================
echo.
echo [STEP 1] Deploy Backend to Render (FREE)
echo   1. Go to: https://render.com
echo   2. Sign up with GitHub
echo   3. Click 'New +' -^> 'Blueprint'
echo   4. Connect your repository
echo   5. Click 'Apply' (render.yaml detected automatically)
echo   6. Add Environment Variables:
echo      - GEMINI_API_KEY: your-key-here
echo      - OPENAI_API_KEY: your-key-here (optional)
echo      - ELEVENLABS_API_KEY: your-key-here (optional)
echo   7. Wait 5-10 minutes for build
echo   8. Copy backend URL
echo.

echo [STEP 2] Deploy Frontend to Vercel (FREE)
echo   Run these commands in a new terminal:
echo.
echo   cd web
echo   npm install -g vercel
echo   vercel login
echo   vercel
echo.
echo   Then in Vercel Dashboard:
echo   - Settings -^> Environment Variables
echo   - Add NEXT_PUBLIC_WS_URL and NEXT_PUBLIC_API_URL
echo   - Redeploy: vercel --prod
echo.

echo [STEP 3] Keep Backend Alive (Optional)
echo   - Go to: https://uptimerobot.com
echo   - Add HTTP monitor
echo   - URL: https://YOUR-BACKEND.onrender.com/health
echo   - Interval: 5 minutes
echo.

echo ========================================
echo  Your Voice Assistant will be live soon!
echo ========================================
echo.
echo See DEPLOYMENT.md for detailed instructions
echo.

pause
