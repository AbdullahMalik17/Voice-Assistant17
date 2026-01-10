# Deployment Guide - Voice Assistant with Web Integration

This guide covers deploying the Voice Assistant with web search and browser automation features.

## Pre-Deployment Checklist

- [ ] All environment variables configured
- [ ] Build completes without errors
- [ ] API endpoints tested locally
- [ ] Tavily API key is valid and active
- [ ] Browser automation dependencies installed
- [ ] Git changes committed

## Environment Variables

### 1. Copy Environment Template
```bash
cp .env.example .env.local
```

### 2. Fill in Required Variables

```env
# Backend URLs
NEXT_PUBLIC_WS_URL=wss://your-backend-url/ws/voice
NEXT_PUBLIC_API_URL=https://your-backend-url

# Supabase (if using)
NEXT_PUBLIC_SUPABASE_URL=...
NEXT_PUBLIC_SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...

# Authentication
NEXTAUTH_SECRET=<generate with: openssl rand -base64 32>
NEXTAUTH_URL=https://your-app-url

# Tavily Web Search
TAVILY_API_KEY=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
```

## Deployment Platforms

### Vercel (Recommended for Next.js)

#### 1. Install Vercel CLI
```bash
npm i -g vercel
```

#### 2. Deploy
```bash
vercel deploy
```

#### 3. Configure Environment Variables in Vercel Dashboard
- Go to Settings → Environment Variables
- Add all variables from `.env.local`
- Ensure `TAVILY_API_KEY` is added as private variable

#### 4. Important: Playwright Browser Support
For Vercel deployments with Playwright, use `@vercel/nft` or alternative approach:

**Option A: Use managed Playwright (Recommended)**
Update `next.config.js`:
```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    serverComponentsExternalPackages: ['playwright'],
  },
};

module.exports = nextConfig;
```

**Option B: Disable browser automation for Vercel**
If Playwright causes deployment issues, comment out browser automation features in production:
```typescript
// In src/lib/browser.ts
if (process.env.NODE_ENV === 'production') {
  // Browser automation disabled in production
  export async function executeBrowserAction() {
    return {
      success: false,
      error: 'Browser automation not available in production',
    };
  }
}
```

#### 5. Deploy to Vercel
```bash
git push
# Vercel auto-deploys from your main branch
```

### Docker Deployment

#### 1. Create Dockerfile
```dockerfile
FROM node:18-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Install Playwright browsers
RUN npx playwright install --with-deps chromium

# Build Next.js app
COPY . .
RUN npm run build

# Expose port
EXPOSE 3000

# Start production server
CMD ["npm", "start"]
```

#### 2. Create .dockerignore
```
node_modules
.next
.git
.gitignore
README.md
```

#### 3. Build and Run
```bash
docker build -t voice-assistant .
docker run -p 3000:3000 \
  -e TAVILY_API_KEY=your_key \
  -e NEXT_PUBLIC_WS_URL=wss://your-backend/ws/voice \
  voice-assistant
```

### HuggingFace Spaces Deployment

#### 1. Create Space
- Go to https://huggingface.co/spaces
- Create new space (Docker or static)

#### 2. Upload Files
```bash
git clone https://huggingface.co/spaces/username/voice-assistant
cd voice-assistant
cp -r ../web/* .
```

#### 3. Configure app.py (for HF Spaces)
```python
import subprocess
import os

os.environ['TAVILY_API_KEY'] = os.getenv('TAVILY_API_KEY')
os.environ['NEXT_PUBLIC_WS_URL'] = os.getenv('NEXT_PUBLIC_WS_URL')

subprocess.run(['npm', 'install'], cwd='/app')
subprocess.run(['npm', 'run', 'build'], cwd='/app')
subprocess.run(['npm', 'start'], cwd='/app')
```

## Post-Deployment Testing

### 1. Test Health Check
```bash
curl https://your-app-url/api/search -X GET
# Should return 405 (Method not allowed) for GET, meaning endpoint exists
```

### 2. Test Web Search API
```bash
curl -X POST https://your-app-url/api/search \
  -H "Content-Type: application/json" \
  -d '{"query":"test"}'
```

### 3. Test Browser API
```bash
curl -X POST https://your-app-url/api/browser \
  -H "Content-Type: application/json" \
  -d '{"action":"screenshot"}'
```

### 4. Test Frontend
- Open https://your-app-url
- Check browser console for errors
- Test voice commands

## Production Optimization

### 1. Enable Caching
Add to `next.config.js`:
```javascript
const nextConfig = {
  onDemandEntries: {
    maxInactiveAge: 60 * 60 * 1000,
    pagesBufferLength: 5,
  },
};
```

### 2. API Rate Limiting
Implement rate limiting for `api/search` and `api/browser`:
```typescript
// In src/middleware.ts
import { Ratelimit } from '@upstash/ratelimit';

const ratelimit = new Ratelimit({
  redis: Redis.fromEnv(),
  limiter: Ratelimit.slidingWindow(10, '1 m'),
});

export async function middleware(request: NextRequest) {
  if (request.nextUrl.pathname.startsWith('/api/')) {
    const { success } = await ratelimit.limit(request.ip || 'anonymous');
    if (!success) {
      return NextResponse.json({ error: 'Rate limit exceeded' }, { status: 429 });
    }
  }
  return NextResponse.next();
}
```

### 3. Security Headers
Add to `next.config.js`:
```javascript
async headers() {
  return [
    {
      source: '/api/:path*',
      headers: [
        { key: 'Content-Type', value: 'application/json' },
        { key: 'X-Content-Type-Options', value: 'nosniff' },
      ],
    },
  ];
}
```

### 4. Browser Automation Resource Limits
Add timeouts and resource limits:
```typescript
// In src/lib/browser.ts
const BROWSER_TIMEOUT = 30000; // 30 seconds
const MAX_PAGE_SIZE = 50 * 1024 * 1024; // 50MB

await page.goto(url, {
  waitUntil: 'networkidle',
  timeout: BROWSER_TIMEOUT,
});
```

## Troubleshooting Deployment

### Issue: Playwright not found in production
**Solution:**
- For Vercel: Use `@vercel/nft` to bundle Playwright
- For Docker: Ensure `RUN npx playwright install --with-deps` is in Dockerfile
- For other: Include Playwright browsers in build output

### Issue: API endpoints returning 404
**Solution:**
- Rebuild and redeploy
- Check that `src/app/api/` directory structure is correct
- Verify environment variables are set

### Issue: Web search not working
**Solution:**
- Verify `TAVILY_API_KEY` is correctly set in environment
- Check API key is valid at tavily.com dashboard
- Review API usage quota

### Issue: Browser automation timeout
**Solution:**
- Increase timeout in browser.ts: `timeout: 60000`
- Check server has sufficient CPU/memory
- Consider disabling in production if resources are limited

## Monitoring & Logs

### Vercel Logs
```bash
vercel logs <project-name>
```

### Docker Logs
```bash
docker logs <container-id>
```

### Application Errors
- Check browser console (client-side errors)
- Check server logs (server-side errors)
- Monitor API response times

## Rollback Plan

### Vercel
```bash
vercel rollback <deployment-url>
```

### Docker
```bash
docker run -p 3000:3000 <previous-image-tag>
```

### Git
```bash
git revert <commit-hash>
git push
```

## Performance Benchmarks

Expected metrics:
- Search API: < 3 seconds
- Browser navigation: < 5 seconds
- Screenshot capture: < 2 seconds
- Frontend load time: < 2 seconds

## Maintenance

### Regular Updates
```bash
npm update
npm audit fix
npm run build
```

### Monitor API Quotas
- Check Tavily API usage dashboard monthly
- Monitor server resource usage
- Review browser automation logs

### Backup
- Backup environment variables
- Backup Supabase data regularly
- Version control all code changes

## Support & Resources

- Next.js Deployment: https://nextjs.org/docs/deployment
- Vercel Docs: https://vercel.com/docs
- Playwright Docs: https://playwright.dev
- Tavily API Docs: https://tavily.com/docs
