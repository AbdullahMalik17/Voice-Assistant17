# Voice Assistant - Complete Deployment Guide

## 📋 Overview

This guide will walk you through deploying your Voice Assistant with full authentication, conversation history, and production features.

## 🏗️ Architecture

- **Frontend**: Vercel (Next.js 14)
- **Backend**: Hugging Face Spaces (FastAPI + WebSocket)
- **Database**: Supabase (PostgreSQL)
- **Authentication**: NextAuth.js + Supabase Auth

## 🚀 Quick Start (30 Minutes)

### Step 1: Supabase Setup (10 min)

1. **Create Supabase Project**
   - Go to https://supabase.com/dashboard
   - Click "New project"
   - Name: `voice-assistant-prod`
   - Database Password: Generate and save securely
   - Region: Choose closest to your users
   - Wait 2-3 minutes for provisioning

2. **Run Database Migrations**
   - Go to SQL Editor
   - Run these migrations in order:
     - `supabase/migrations/001_user_profiles.sql`
     - `supabase/migrations/002_conversation_sessions.sql`
     - `supabase/migrations/003_conversation_turns.sql`

3. **Configure Authentication**
   - Go to Authentication → Providers → Email
   - Enable Email provider
   - **For Testing**: Turn OFF "Confirm email"
   - **For Production**: Turn ON "Confirm email"

4. **Get API Keys**
   - Go to Project Settings → API
   - Copy these values:
     ```
     NEXT_PUBLIC_SUPABASE_URL=https://xxxxx.supabase.co
     NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGc...
     SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...
     SUPABASE_JWT_SECRET=your-jwt-secret
     ```

5. **Configure URLs**
   - Go to Authentication → URL Configuration
   - Site URL: `https://voice-assistant-orcin.vercel.app`
   - Redirect URLs:
     ```
     https://voice-assistant-orcin.vercel.app/api/auth/callback/credentials
     https://voice-assistant-orcin.vercel.app/auth/login
     https://voice-assistant-orcin.vercel.app/auth/reset-password
     http://localhost:3000/api/auth/callback/credentials
     http://localhost:3000
     ```

### Step 2: Hugging Face Spaces Setup (10 min)

1. **Check Your Space**
   - Your space: https://huggingface.co/spaces/AbdullahMalik17/VoiceAssistant17
   - Should already be deployed

2. **Add Environment Variables**
   - Go to your Space → Settings → Variables and secrets
   - Add these secrets:
     ```
     NEXTAUTH_SECRET=JlSlfwZsQDQeozQQaqw9vA5LXNgGZlSmz7oGtv2dUz36rgKxwppaT2kJGbYhO7MiSjk949zFpOh/rrBzaJf5WA==
     SUPABASE_JWT_SECRET=your-jwt-secret-from-supabase
     ```

3. **Update CORS** (if needed)
   - Make sure `CORS_ORIGINS` includes your Vercel domain
   - Default already includes common domains

### Step 3: Vercel Deployment (10 min)

1. **Configure Environment Variables**
   - Go to https://vercel.com/dashboard
   - Select your project → Settings → Environment Variables
   - Add these 7 variables (All environments):

   ```bash
   # Backend (Hugging Face)
   NEXT_PUBLIC_WS_URL=wss://abdullahmalik17-voiceassistant17.hf.space/ws/voice
   NEXT_PUBLIC_API_URL=https://abdullahmalik17-voiceassistant17.hf.space

   # Supabase
   NEXT_PUBLIC_SUPABASE_URL=https://ytelwprjbtscdpqklake.supabase.co
   NEXT_PUBLIC_SUPABASE_ANON_KEY=<your-anon-key>
   SUPABASE_SERVICE_ROLE_KEY=<your-service-role-key>

   # NextAuth
   NEXTAUTH_SECRET=JlSlfwZsQDQeozQQaqw9vA5LXNgGZlSmz7oGtv2dUz36rgKxwppaT2kJGbYhO7MiSjk949zFpOh/rrBzaJf5WA==
   NEXTAUTH_URL=https://voice-assistant-orcin.vercel.app
   ```

2. **Redeploy**
   - Go to Deployments tab
   - Click latest deployment → ⋯ menu → Redeploy
   - Uncheck "Use existing Build Cache"
   - Wait 2-3 minutes

3. **Test**
   - Visit https://voice-assistant-orcin.vercel.app
   - Try registration and login
   - Send a test message

## ✅ Verification Checklist

### Frontend (Vercel)
- [ ] Login page loads without errors
- [ ] Can register new user
- [ ] Can login with credentials
- [ ] User menu shows in header
- [ ] Logout works correctly

### Backend (Hugging Face)
- [ ] WebSocket connects successfully
- [ ] Messages get responses
- [ ] Voice input/output works
- [ ] Tools execute correctly
- [ ] Authenticated users show in logs

### Database (Supabase)
- [ ] Users appear in Authentication → Users
- [ ] User profiles are created automatically
- [ ] Conversation sessions are stored
- [ ] RLS policies are active

### Authentication Flow
- [ ] Registration creates user in Supabase
- [ ] Login returns JWT token
- [ ] WebSocket receives token
- [ ] Backend validates token
- [ ] User context available in session

## 🔧 Advanced Configuration

### Enable Email Confirmation (Production)

1. **Supabase Settings**
   - Go to Authentication → Providers → Email
   - Turn ON "Confirm email"
   - Save

2. **Email Templates** (Optional)
   - Go to Authentication → Email Templates
   - Customize "Confirm signup" template
   - Update confirmation URL if needed

3. **SMTP Configuration** (Optional)
   - Go to Project Settings → Auth → SMTP Settings
   - Configure your SMTP server for branded emails
   - Or use Supabase's default email service

### Password Reset Flow

Users can reset passwords at:
- https://voice-assistant-orcin.vercel.app/auth/forgot-password

Email will be sent with reset link to:
- https://voice-assistant-orcin.vercel.app/auth/reset-password

### Custom Domain (Optional)

1. **Vercel**
   - Go to Settings → Domains
   - Add your custom domain
   - Follow DNS configuration instructions

2. **Update Supabase**
   - Authentication → URL Configuration
   - Update Site URL to your custom domain
   - Add custom domain to Redirect URLs

3. **Update Environment Variables**
   - Update `NEXTAUTH_URL` in Vercel

## 🛡️ Security Checklist

- [ ] NEXTAUTH_SECRET is strong and secret
- [ ] SUPABASE_SERVICE_ROLE_KEY is never exposed to client
- [ ] Email confirmation enabled for production
- [ ] RLS policies tested and working
- [ ] CORS origins restricted to your domains
- [ ] JWT tokens have reasonable expiration (30 days)
- [ ] HTTPS enabled on all endpoints

## 📊 Monitoring & Logging

### Backend Logs (Hugging Face)
- View at: https://huggingface.co/spaces/AbdullahMalik17/VoiceAssistant17/logs
- Look for:
  - `✅ Authenticated user:` - Successful auth
  - `❌ Authentication failed:` - Auth errors
  - WebSocket connection/disconnection events

### Frontend Logs (Vercel)
- Go to Deployments → Latest → Runtime Logs
- Look for:
  - Build errors
  - Runtime errors
  - API call failures

### Database Activity (Supabase)
- Go to Project Settings → Database → Query Performance
- Monitor slow queries
- Check table sizes

### Browser Console
- Open DevTools (F12) → Console
- Look for:
  - `🔐 Connecting to WebSocket with authentication`
  - `⚠️  Connecting to WebSocket without authentication`
  - WebSocket connection status

## 🐛 Troubleshooting

### "Connection lost" Error
**Cause**: Backend not running or wrong URL
**Fix**:
1. Check Hugging Face Space is running
2. Verify `NEXT_PUBLIC_WS_URL` in Vercel
3. Check browser console for connection errors

### "Invalid login credentials"
**Cause**: User not confirmed or wrong password
**Fix**:
1. Check Supabase → Authentication → Users
2. Manually confirm user or disable email confirmation
3. Verify password is correct

### "Email signups are disabled"
**Cause**: Email provider not enabled in Supabase
**Fix**:
1. Go to Authentication → Providers → Email
2. Toggle ON
3. Save

### WebSocket Authentication Fails
**Cause**: Missing or invalid JWT token
**Fix**:
1. Check `NEXTAUTH_SECRET` matches in Vercel and HF
2. Verify `SUPABASE_JWT_SECRET` is set in HF Space
3. Check browser console for token errors
4. Logout and login again to get fresh token

### Password Reset Email Not Received
**Cause**: Email not configured or wrong redirect URL
**Fix**:
1. Check Supabase → Authentication → URL Configuration
2. Verify redirect URLs include `/auth/reset-password`
3. Check spam folder
4. Configure SMTP for reliable delivery

## 📈 Performance Tips

1. **Enable Build Cache** (after first successful deploy)
   - Speeds up subsequent deployments

2. **Monitor Bundle Size**
   - Keep client-side bundle < 200KB
   - Use dynamic imports for large components

3. **Database Indexes**
   - Already created via migrations
   - Monitor slow queries in Supabase

4. **WebSocket Connection Pooling**
   - Backend handles this automatically
   - Max 100 concurrent connections on free tier

## 💰 Cost Breakdown

### Free Tier (Current Setup)
- **Vercel**: Free (Hobby plan)
  - 100GB bandwidth/month
  - Unlimited deployments
- **Hugging Face**: Free (Community)
  - 2 CPU cores, 16GB RAM
  - Sleeps after 15min inactivity
- **Supabase**: Free
  - 500MB database
  - 50,000 monthly active users
  - 2GB bandwidth

### Paid Upgrades
- **Vercel Pro**: $20/month
  - 1TB bandwidth
  - Advanced analytics
- **HF Spaces Persistent**: ~$0.60/hour
  - Always running, no sleep
  - 16GB RAM, 4 CPU cores
- **Supabase Pro**: $25/month
  - 8GB database
  - 100,000 MAU
  - 50GB bandwidth

## 📞 Support

- **Supabase**: https://supabase.com/docs
- **Vercel**: https://vercel.com/docs
- **Hugging Face**: https://huggingface.co/docs/hub

## 🎉 You're Done!

Your Voice Assistant is now deployed with:
- ✅ Full authentication (JWT + Supabase)
- ✅ User registration and login
- ✅ Password reset functionality
- ✅ User settings page
- ✅ Conversation history (frontend + backend)
- ✅ Production-ready security
- ✅ Scalable architecture

Visit your deployed app: **https://voice-assistant-orcin.vercel.app**
