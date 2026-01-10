# Deployment Guide: Critical Production Fixes

## Overview
This guide walks through deploying the 5 critical production fixes that resolve WebSocket connection failures, conversation persistence, settings management, user memory, and performance issues.

## Fixes Included

### 1. WebSocket Connection (No Longer Requires Auth)
- **Backend**: Made authentication optional
- **Frontend**: Removed NextAuth dependency for WebSocket
- **Result**: WebSocket connects immediately without authentication errors

### 2. Conversation Persistence (SQLite-Based)
- **Backend**: Guaranteed storage via SQLite with fallback logic
- **Frontend**: Migrated from Supabase to REST API endpoints
- **Result**: All conversations automatically saved to local database

### 3. Settings Persistence (New REST API)
- **Endpoints**: `/api/settings`, `/api/settings` (POST), `/api/settings` (PUT), `/api/settings` (DELETE)
- **Storage**: SQLite `settings` table
- **Result**: User settings persist across sessions

### 4. User Memory & Context (New REST API)
- **Endpoints**: `/api/profile`, `/api/profile` (POST)
- **Storage**: SQLite `user_profiles` table
- **Result**: System remembers user information and includes it in LLM context

### 5. Performance Optimizations
- Efficient context loading with last 5 turns only
- Proper SQLite indexing for fast queries
- Better error handling prevents cascading failures

---

## Deployment Steps

### Step 1: Deploy Backend to HuggingFace Spaces

**Important**: These commits are already in your repository.

```bash
# Push to HuggingFace
git push origin main

# HuggingFace Spaces will automatically redeploy when you push
# Watch the "App logs" tab to see deployment progress
```

**What to look for in logs**:
```
✓ SQLite store initialized for conversation persistence
✓ Semantic and persistent session memory services initialized
✓ Agent services initialized
```

### Step 2: Configure Environment Variables

**On HuggingFace Spaces**:

Go to Settings → Secrets and add (if not already present):

```
NEXT_PUBLIC_API_URL=https://abdullahmalik17-voiceassistant17.hf.space
NEXT_PUBLIC_WS_URL=wss://abdullahmalik17-voiceassistant17.hf.space/ws/voice
```

**In your `.env` or HuggingFace Spaces Secrets** (optional):
```
# If you want to use Mem0 API for additional memory (optional)
MEM0_API_KEY=your_mem0_api_key_here

# Supabase (no longer required for basic functionality)
# Can be removed or kept for legacy features
NEXT_PUBLIC_SUPABASE_URL=...
NEXT_PUBLIC_SUPABASE_ANON_KEY=...
```

### Step 3: Deploy Frontend to Vercel

**Push changes**:
```bash
git push origin main
```

**Vercel will automatically redeploy. Ensure environment variables are set**:

Settings → Environment Variables:
```
NEXT_PUBLIC_API_URL=https://abdullahmalik17-voiceassistant17.hf.space
NEXT_PUBLIC_WS_URL=wss://abdullahmalik17-voiceassistant17.hf.space/ws/voice
NEXT_PUBLIC_SUPABASE_URL=... (optional)
NEXT_PUBLIC_SUPABASE_ANON_KEY=... (optional)
```

### Step 4: Verify Deployment

Open browser developer console and check for:

**✅ Good Signs**:
```
✅ Connecting to WebSocket (authentication optional)
Attempting WebSocket connection to: wss://...
Connected (should see "NEXUS link established" message)
```

**❌ Bad Signs**:
```
WebSocket connection failed
Failed to fetch /api/auth/session
Error fetching conversations: invalid input syntax for type uuid
```

---

## Testing the Fixes

### Test 1: WebSocket Connection
1. Open the chat interface
2. Check browser console
3. Should see: `✅ Connecting to WebSocket (authentication optional)`
4. Should see in chat: "NEXUS link established • System online"

### Test 2: Conversation Persistence
1. Send a message: "Hello, remember this conversation"
2. Refresh the page
3. Check conversation history sidebar
4. Previous conversation should appear

### Test 3: Settings Persistence
**Option A: Using API directly**
```bash
# Save settings
curl -X POST "https://abdullahmalik17-voiceassistant17.hf.space/api/settings" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "default",
    "settings": {
      "voice_enabled": true,
      "theme": "dark"
    }
  }'

# Get settings
curl "https://abdullahmalik17-voiceassistant17.hf.space/api/settings?user_id=default"
```

**Option B: Using frontend** (once UI is added)
- Settings panel should save and persist

### Test 4: User Memory
**Option A: Using API directly**
```bash
# Save user profile
curl -X POST "https://abdullahmalik17-voiceassistant17.hf.space/api/profile" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "default",
    "profile": {
      "name": "Abdullah",
      "email": "your@email.com"
    }
  }'

# Get user profile
curl "https://abdullahmalik17-voiceassistant17.hf.space/api/profile?user_id=default"
```

**Option B: Using chat**
1. Send message: "My name is Abdullah"
2. Send message: "What is my name?"
3. Should respond: "Your name is Abdullah"

### Test 5: Performance
- Check browser Network tab
- WebSocket messages should have low latency
- Conversations should load quickly from local database

---

## Database Schema

These tables are automatically created in `data/sessions.db`:

```sql
-- Conversations
CREATE TABLE sessions (
  session_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  state TEXT NOT NULL,
  current_intent TEXT,
  metadata TEXT,
  created_at TIMESTAMP,
  last_updated TIMESTAMP
);

CREATE TABLE turns (
  turn_id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  user_input TEXT NOT NULL,
  assistant_response TEXT NOT NULL,
  intent TEXT,
  intent_confidence REAL,
  entities TEXT,
  timestamp TIMESTAMP,
  FOREIGN KEY (session_id) REFERENCES sessions (session_id)
);

-- Settings & Profiles
CREATE TABLE settings (
  user_id TEXT PRIMARY KEY,
  settings_json TEXT,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);

CREATE TABLE user_profiles (
  user_id TEXT PRIMARY KEY,
  profile_json TEXT,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

---

## Troubleshooting

### Problem: "WebSocket is closed before connection is established"

**Solution**:
1. Check HuggingFace backend is running: `https://abdullahmalik17-voiceassistant17.hf.space/health`
2. Check CORS settings - backend should accept your frontend domain
3. Check WebSocket URL is correct with `wss://` (not `ws://`)

### Problem: "Error fetching conversations: invalid input syntax for type uuid"

**Solution**: This means frontend is still using old Supabase code
1. Hard refresh browser (Ctrl+Shift+R)
2. Clear browser cache
3. Verify Vercel deployment is up to date

### Problem: Settings not persisting

**Solution**:
1. Check SQLite file exists: `data/sessions.db`
2. Verify POST request to `/api/settings` returns success
3. Check database file has write permissions

### Problem: User name not remembered

**Solution**:
1. Save profile via: `POST /api/profile`
2. Verify in logs: "User profile saved for user default"
3. Ensure LLM receives context in prompt

---

## API Reference

### Conversations
```
GET  /api/conversations?user_id=default&limit=20
GET  /api/conversations/{session_id}?user_id=default
DELETE /api/conversations/{session_id}?user_id=default
GET  /api/conversations/search?query=test&user_id=default&limit=10
GET  /api/conversations/export/{session_id}?user_id=default&format=json
```

### Settings
```
GET  /api/settings?user_id=default
POST /api/settings
  Body: { "user_id": "default", "settings": {...} }
PUT  /api/settings
  Body: { "user_id": "default", "settings": {...} }
DELETE /api/settings?user_id=default
```

### User Profile
```
GET  /api/profile?user_id=default
POST /api/profile
  Body: { "user_id": "default", "profile": {"name": "...", ...} }
```

### WebSocket
```
wss://abdullahmalik17-voiceassistant17.hf.space/ws/voice
```

Message format:
```json
{
  "type": "text",
  "content": "Your message here"
}
```

---

## Rollback Plan

If issues occur, rollback with:

```bash
# Get previous commit hash
git log --oneline -n 5

# Revert to previous working state (HuggingFace and Vercel auto-deploy)
git revert HEAD
git push origin main

# This will reverse the changes while keeping git history clean
```

---

## Next Steps

1. ✅ Deploy backend to HuggingFace
2. ✅ Deploy frontend to Vercel
3. ✅ Verify WebSocket connection
4. ✅ Test conversation persistence
5. ⬜ Add settings UI to frontend (optional)
6. ⬜ Add user profile setup form (optional)
7. ⬜ Monitor error logs for issues

---

## Support

If you encounter issues:
1. Check browser console for error messages
2. Check HuggingFace App logs for backend errors
3. Test API endpoints directly with curl
4. Check database file exists and is writable

**Key Log Locations**:
- **HuggingFace**: Settings → "App logs" tab
- **Vercel**: Deployments → view logs
- **Browser**: Developer Tools → Console tab
