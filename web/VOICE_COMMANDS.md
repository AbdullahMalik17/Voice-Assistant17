# Voice Commands & Web Integration Guide

This document describes the new web search and browser automation features integrated into the Voice Assistant.

## Features Added

### 1. Web Search via Tavily API
- **Endpoint**: `POST /api/search`
- **Purpose**: Perform intelligent web searches using Tavily's search engine
- **API Key**: Stored in `TAVILY_API_KEY` environment variable

### 2. Browser Automation via Playwright
- **Endpoint**: `POST /api/browser`
- **Purpose**: Control browser actions (navigate, click, type, screenshot, etc.)
- **Headless Mode**: Runs in headless mode for server environments

### 3. Voice Command Processing
- **Service**: `src/lib/voice-commands.ts`
- **Hook**: `useVoiceCommands()` from `src/hooks/useVoiceCommands.ts`
- **Auto-Detection**: Automatically detects command type from spoken/written text

## Voice Command Examples

### Web Search Commands
```
"Search for climate change"
"Find information about quantum computing"
"What is artificial intelligence?"
"Tell me about recent news"
```

### Browser Navigation Commands
```
"Open Google"
"Go to Facebook.com"
"Navigate to GitHub"
"Visit YouTube"
```

### Browser Interaction Commands
```
"Click the search button"
"Type 'hello world' in the search box"
"Take a screenshot"
"Scroll down"
```

## API Usage

### Web Search API

**Request:**
```bash
POST /api/search
Content-Type: application/json

{
  "query": "climate change"
}
```

**Response:**
```json
{
  "success": true,
  "query": "climate change",
  "answer": "Climate change is...",
  "results": [
    {
      "title": "Climate Change - NASA",
      "url": "https://nasa.gov/climate",
      "content": "...",
      "score": 0.95
    }
  ],
  "images": ["url1", "url2"],
  "follow_up_questions": ["What causes climate change?"]
}
```

### Browser Automation API

**Request:**
```bash
POST /api/browser
Content-Type: application/json

{
  "action": "navigate",
  "url": "https://google.com"
}
```

**Available Actions:**
- `navigate` - Navigate to URL (requires `url`)
- `click` - Click element (requires `selector`)
- `type` - Type text in element (requires `selector`, `text`)
- `screenshot` - Take page screenshot
- `search` - Google search (requires `query`)
- `scroll` - Scroll page (optional `scrollAmount`)
- `extract` - Extract text content (optional `selector`)

**Response:**
```json
{
  "success": true,
  "data": {
    "action": "navigate",
    "message": "Navigated to https://google.com"
  }
}
```

## Integration with Voice Commands

The system automatically processes voice input and executes appropriate actions:

1. **Command Detection**: Analyzes text for keywords
2. **Information Extraction**: Extracts relevant parameters (query, URL, selector, etc.)
3. **Execution**: Calls appropriate API endpoint
4. **Response**: Returns results to user

### Using in Components

```tsx
import { useVoiceCommands } from '@/hooks/useVoiceCommands';

function MyComponent() {
  const { execute, isProcessing, lastResponse, error } = useVoiceCommands();

  const handleCommand = async (text: string) => {
    const response = await execute({
      text,
      intent: 'auto-detect',
      timestamp: new Date(),
    });

    if (response.status === 'success') {
      console.log('Success:', response.data);
    } else {
      console.error('Error:', response.message);
    }
  };

  return (
    <div>
      <button onClick={() => handleCommand('search for python tutorials')}>
        Search
      </button>
      {isProcessing && <p>Processing...</p>}
      {error && <p>Error: {error}</p>}
    </div>
  );
}
```

## Environment Variables

Add to `.env.local`:

```env
# Tavily API Configuration
TAVILY_API_KEY=your_api_key_here

# Backend Configuration (existing)
NEXT_PUBLIC_WS_URL=wss://your-backend-url/ws/voice
NEXT_PUBLIC_API_URL=https://your-backend-url
```

## Dependencies

- `playwright`: Browser automation
- `axios`: HTTP client for API calls
- `tavily-js`: Tavily API SDK (optional, using axios instead)

Install:
```bash
npm install playwright axios
```

## Backend Integration

These features work alongside the existing WebSocket connection to the backend:

1. **Voice Input** → Backend (via WebSocket)
2. **Transcription** ← Backend (via WebSocket)
3. **Voice Commands** → Frontend APIs (via HTTP)
4. **Voice Response** → User (via TTS)

The frontend can now:
- Process user commands locally
- Execute web searches
- Control browser automation
- Provide immediate responses

## Security Considerations

1. **API Keys**: Store Tavily API key in environment variables only
2. **Browser Automation**: Runs in headless mode with limited scope
3. **Content**: Search results are validated before use
4. **Rate Limiting**: Implement rate limiting for API endpoints in production

## Troubleshooting

### "TAVILY_API_KEY is not configured"
- Ensure `.env.local` includes `TAVILY_API_KEY`
- Restart development server: `npm run dev`

### Browser automation not working
- Check Playwright installation: `npx playwright install`
- Verify server environment supports headless browsers

### Search results not appearing
- Check network requests in browser DevTools
- Verify Tavily API key is valid
- Check API rate limits

## Future Enhancements

- [ ] Add image search capabilities
- [ ] Implement caching for frequent searches
- [ ] Add browser session persistence
- [ ] Create custom command definitions
- [ ] Add video content extraction
- [ ] Implement voice command analytics

## Testing

To test the APIs manually:

```bash
# Test web search
curl -X POST http://localhost:3000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query":"test"}'

# Test browser automation
curl -X POST http://localhost:3000/api/browser \
  -H "Content-Type: application/json" \
  -d '{"action":"navigate","url":"https://google.com"}'
```

## Support

For issues or questions:
1. Check the Tavily API documentation: https://tavily.com/docs
2. Check Playwright documentation: https://playwright.dev
3. Review application logs for detailed error messages
