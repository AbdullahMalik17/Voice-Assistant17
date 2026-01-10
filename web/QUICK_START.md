# Quick Start Guide - Voice Assistant Web Integration

## Setup (First Time)

### 1. Install Dependencies
```bash
cd web
npm install
```

### 2. Configure Environment
```bash
# Copy template
cp .env.example .env.local

# Edit .env.local and add your keys:
# TAVILY_API_KEY=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
# NEXT_PUBLIC_WS_URL=wss://your-backend/ws/voice
# etc.
```

### 3. Install Playwright Browsers
```bash
npx playwright install
```

### 4. Start Development Server
```bash
npm run dev
```

Server runs at `http://localhost:3000`

## Testing the Features

### Test Web Search API

```bash
curl -X POST http://localhost:3000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query":"what is machine learning"}'
```

**Expected Response:**
```json
{
  "success": true,
  "query": "what is machine learning",
  "answer": "Machine learning is...",
  "results": [
    {
      "title": "Machine Learning - Wikipedia",
      "url": "https://...",
      "content": "...",
      "score": 0.95
    }
  ]
}
```

### Test Browser Automation API

```bash
# Navigate to Google
curl -X POST http://localhost:3000/api/browser \
  -H "Content-Type: application/json" \
  -d '{"action":"navigate","url":"https://google.com"}'

# Take screenshot
curl -X POST http://localhost:3000/api/browser \
  -H "Content-Type: application/json" \
  -d '{"action":"screenshot"}'

# Google search
curl -X POST http://localhost:3000/api/browser \
  -H "Content-Type: application/json" \
  -d '{"action":"search","query":"python programming"}'
```

### Test Voice Commands in Browser

1. Open http://localhost:3000
2. Click the microphone button or press `Space`
3. Speak a command:
   - "Search for artificial intelligence"
   - "Open Google"
   - "Take a screenshot"

## Development Workflow

### File Structure
```
web/
├── src/
│   ├── app/
│   │   ├── api/
│   │   │   ├── search/      # Web search endpoint
│   │   │   └── browser/     # Browser automation endpoint
│   │   └── ...
│   ├── lib/
│   │   ├── tavily.ts        # Tavily search service
│   │   ├── browser.ts       # Playwright browser service
│   │   ├── voice-commands.ts # Voice command processor
│   │   └── ...
│   ├── hooks/
│   │   ├── useVoiceCommands.ts  # Voice command hook
│   │   └── ...
│   └── ...
├── VOICE_COMMANDS.md        # Feature documentation
├── DEPLOYMENT.md            # Deployment guide
└── ...
```

### Making Changes

1. **Update API Endpoints**: Edit files in `src/app/api/`
2. **Update Services**: Edit files in `src/lib/`
3. **Update Hooks**: Edit files in `src/hooks/`
4. **Update Components**: Edit files in `src/components/`

### Building for Production

```bash
npm run build
npm start
```

## Common Tasks

### Add a New Voice Command Type

1. Update keywords in `src/lib/voice-commands.ts`:
```typescript
const NEW_KEYWORDS = ['command', 'action'];

export function detectCommandType(text: string): string {
  // ... existing code ...
  if (NEW_KEYWORDS.some((k) => lowerText.includes(k))) {
    return 'new-command';
  }
}
```

2. Add handler in `processVoiceCommand()`:
```typescript
case 'new-command': {
  // Your logic here
  return await executeNewCommand(context.text);
}
```

### Add a New Browser Action

1. Update `BrowserAction` type in `src/lib/browser.ts`:
```typescript
export interface BrowserAction {
  type: 'navigate' | 'click' | 'type' | ... | 'new-action';
  // ...
}
```

2. Add handler in `BrowserManager.execute()`:
```typescript
case 'new-action':
  return this.myNewAction();
```

3. Implement the method:
```typescript
async myNewAction(): Promise<BrowserActionResult> {
  try {
    // Your logic
    return { success: true, data: 'Success' };
  } catch (error) {
    return { success: false, error: error?.message };
  }
}
```

### Debug API Calls

Check browser Network tab in DevTools:
1. Open http://localhost:3000
2. Open DevTools (F12)
3. Go to Network tab
4. Issue a command
5. Look for POST requests to `/api/search` and `/api/browser`

View server logs:
```bash
# Terminal where you ran: npm run dev
# Look for console output and errors
```

## Environment Variables Reference

| Variable | Purpose | Example |
|----------|---------|---------|
| `TAVILY_API_KEY` | Web search API key | `tvly-dev-...` |
| `NEXT_PUBLIC_WS_URL` | WebSocket backend | `wss://backend/ws/voice` |
| `NEXT_PUBLIC_API_URL` | API backend | `https://backend` |
| `NEXTAUTH_SECRET` | Auth encryption | Auto-generated |
| `NEXTAUTH_URL` | Auth callback URL | `https://app-url` |

## Troubleshooting

### "TAVILY_API_KEY is not configured"
```bash
# Check .env.local has the key
grep TAVILY_API_KEY .env.local

# Restart dev server
npm run dev
```

### "Module not found: 'playwright'"
```bash
npm install playwright
npx playwright install
npm run dev
```

### "WebSocket connection failed"
```bash
# Check NEXT_PUBLIC_WS_URL in .env.local
# Make sure backend is running
# Check backend logs for errors
```

### "Search API returns empty results"
```bash
# Verify Tavily API key is valid
# Check API quota at tavily.com
# Try a simpler search query
```

## Performance Tips

1. **API Responses**: Check Network tab in DevTools for response times
2. **Browser Automation**: Limit screenshots/interactions (they're slow)
3. **Caching**: Search results are not cached yet (future improvement)
4. **Memory**: Browser automation uses significant memory

## Next Steps

- [ ] Read `VOICE_COMMANDS.md` for feature details
- [ ] Read `DEPLOYMENT.md` for production deployment
- [ ] Test all APIs thoroughly
- [ ] Integrate with your backend
- [ ] Deploy to production

## Resources

- **Next.js Documentation**: https://nextjs.org/docs
- **Playwright Documentation**: https://playwright.dev
- **Tavily API Documentation**: https://tavily.com/docs
- **Tailwind CSS**: https://tailwindcss.com
- **React Documentation**: https://react.dev

## Support

For issues:
1. Check the error message carefully
2. Review logs in browser console and terminal
3. Test APIs with curl before testing in UI
4. Check if services are running (backend, APIs, etc.)
5. Review documentation files in this directory
