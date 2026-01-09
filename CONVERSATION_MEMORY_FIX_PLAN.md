# 🧠 Comprehensive Plan: Fix Conversation Memory (SQLite Persistence)

**Status:** Planning
**Created:** 2026-01-09
**Priority:** CRITICAL - Agent forgets conversations

---

## 🔍 ROOT CAUSE ANALYSIS

### ✅ What's Working
- SQLite database schema exists (`src/storage/sqlite_store.py`)
- `DialogueStateManager` has proper SQLite integration
- `update_session()` method correctly saves to database (lines 392-410)
- Data directory exists (`data/`)

### ❌ What's Broken

**ISSUE #1: `update_session()` is barely called**
```
Location: src/api/websocket_server.py:474

# Only called ONCE in entire file:
if self.dialogue:
    self.dialogue.update_session(user_id, text, response)  # Line 474
```

**ISSUE #2: Wrong parameters**
```python
# Current (WRONG):
self.dialogue.update_session(user_id, text, response)

# Expected signature:
update_session(session_id, user_input, assistant_response, intent, ...)
```
❌ Using `user_id` instead of `session_id`
❌ Missing `intent`, `confidence`, `entities`

**ISSUE #3: Not called after tool execution**
```
Lines 285-413: Tool execution path
- Agent executes tools
- Returns natural language response
- ✅ Stores in persistent_memory (mem0)
- ❌ Does NOT call dialogue.update_session()
- Result: SQLite has NO record of tool interactions
```

**ISSUE #4: Not called after audio processing**
```
Lines 505-553: Audio processing path
- Audio transcribed to text
- Processes via process_text()
- ✅ Eventually calls dialogue.update_session (via process_text)
- BUT: Only if NOT using tool execution path
```

**ISSUE #5: Dual memory systems not synced**
```
SessionManager (in-memory only):
├── Stores messages in Python dict
├── Lost on server restart
└── Used for WebSocket context

DialogueStateManager (persistent):
├── Stores in SQLite + semantic memory
├── Survives server restart
└── RARELY USED in websocket_server.py
```

---

## 🎯 FIX STRATEGY

### Phase 1: Fix SQLite Persistence (CRITICAL)

**Goal:** Ensure EVERY conversation turn is saved to SQLite

#### Change 1: Fix `update_session()` call parameters
```python
# File: src/api/websocket_server.py:474

# BEFORE:
if self.dialogue:
    self.dialogue.update_session(user_id, text, response)

# AFTER:
if self.dialogue:
    self.dialogue.update_session(
        session_id=session_id,
        user_input=text,
        assistant_response=response,
        intent=response.get("intent"),
        intent_confidence=response.get("confidence", 0.0),
        entities={}
    )
```

#### Change 2: Add persistence after tool execution
```python
# File: src/api/websocket_server.py:365-391

# AFTER generating natural language response (line 354):
result = {
    "text": response_text,
    ...
}

# ADD THIS:
# Persist tool execution to SQLite
if self.dialogue:
    self.dialogue.update_session(
        session_id=session_id,
        user_input=text,
        assistant_response=response_text,
        intent="tool_execution",
        intent_confidence=1.0,
        entities={"tool_data": tool_data}
    )
```

#### Change 3: Ensure audio turns are persisted
```python
# File: src/api/websocket_server.py:530

# The transcription is processed via process_text(), which eventually
# calls update_session() IF not using tools.
# No changes needed here, but verify it works end-to-end.
```

#### Change 4: Load conversation history on WebSocket connect
```python
# File: src/api/websocket_server.py:652

# AFTER session creation:
session_id = session_manager.create_session(websocket)

# ADD THIS:
# Load previous conversation history from SQLite if available
if handler.dialogue:
    dialogue_state = handler.dialogue.get_session(session_id)
    if dialogue_state and dialogue_state.turns:
        # Send conversation history to client
        history_msg = WebSocketMessage(
            type=MessageType.SYSTEM,
            content={
                "message": "Conversation history loaded",
                "turns": [t.to_dict() for t in dialogue_state.get_recent_turns(10)]
            },
            session_id=session_id
        )
        await websocket.send_json(history_msg.to_dict())
```

---

### Phase 2: Improve Context Retrieval

**Goal:** Agent uses past conversation history when generating responses

#### Change 5: Inject conversation history into LLM context
```python
# File: src/api/websocket_server.py:444-456

# BEFORE:
context_str = ""
if persistent_context:
    context_str = persistent_context + "\n\n"
if context:
    context_str += "\n".join([...])

# AFTER:
context_str = ""

# 1. Add persistent memory (mem0)
if persistent_context:
    context_str = persistent_context + "\n\n"

# 2. Add SQLite conversation history
if self.dialogue:
    dialogue_state = self.dialogue.get_session(session_id)
    if dialogue_state:
        context_str += dialogue_state.get_context_for_llm(max_turns=10) + "\n\n"

# 3. Add current session context (WebSocket messages)
if context:
    context_str += "\n".join([...])
```

#### Change 6: Add conversation search capability
```python
# File: src/agents/user_tools.py (NEW FILE)

class SearchConversationHistoryTool(BaseTool):
    """
    Tool for agent to search past conversations.
    Usage: "What did I ask about weather yesterday?"
    """
    name = "search_conversation_history"
    description = "Search user's past conversations for specific topics or dates"

    def execute(self, user_id: str, query: str, days_back: int = 7) -> dict:
        """
        Search SQLite conversation history.
        Returns matching turns with context.
        """
        # Implementation using SqliteStore
        pass
```

---

### Phase 3: Add User-Specific Persistence

**Goal:** Support multiple users with separate conversation histories

#### Change 7: Add user_id to WebSocket connection
```python
# File: src/api/websocket_server.py:649-662

# OPTION A: Extract from JWT token (requires authentication)
# user_id = extract_from_jwt(websocket.headers.get("Authorization"))

# OPTION B: Accept from client connection message
# Client sends: {"type": "connect", "user_id": "john@example.com"}

# OPTION C: Use session_id as user_id (current behavior - single user)
user_id = session_id  # For now

# Then pass user_id to all handler methods
```

#### Change 8: Add API endpoint to retrieve conversation history
```python
# File: src/api/websocket_server.py:796+

@app.get("/api/conversations/{user_id}")
async def get_user_conversations(user_id: str, limit: int = 20):
    """
    Get user's recent conversation sessions.
    Returns list of sessions with metadata.
    """
    if not handler or not handler.dialogue or not handler.dialogue.sqlite_store:
        raise HTTPException(status_code=503, detail="Storage not available")

    sessions = handler.dialogue.sqlite_store.get_user_sessions(user_id, limit)
    return JSONResponse(content={"sessions": sessions})


@app.get("/api/conversations/{user_id}/{session_id}")
async def get_conversation_details(user_id: str, session_id: str):
    """
    Get full conversation details for a specific session.
    Returns all turns with timestamps.
    """
    if not handler or not handler.dialogue or not handler.dialogue.sqlite_store:
        raise HTTPException(status_code=503, detail="Storage not available")

    session_data = handler.dialogue.sqlite_store.get_session(session_id)
    if not session_data or session_data['user_id'] != user_id:
        raise HTTPException(status_code=404, detail="Session not found")

    return JSONResponse(content={"session": session_data})
```

---

### Phase 4: Frontend Integration

**Goal:** Display conversation history in web UI

#### Change 9: Add conversation history sidebar
```typescript
// File: web/src/components/chat/ConversationHistory.tsx (NEW)

export function ConversationHistory() {
  const [sessions, setSessions] = useState([]);

  useEffect(() => {
    // Fetch user's conversation history
    fetch('/api/conversations/current_user')
      .then(res => res.json())
      .then(data => setSessions(data.sessions));
  }, []);

  return (
    <div className="conversation-history">
      <h3>Past Conversations</h3>
      {sessions.map(session => (
        <ConversationCard key={session.session_id} session={session} />
      ))}
    </div>
  );
}
```

#### Change 10: Load previous conversation on selection
```typescript
// File: web/src/hooks/useWebSocket.ts

const loadConversation = async (sessionId: string) => {
  const response = await fetch(`/api/conversations/current_user/${sessionId}`);
  const data = await response.json();

  // Display turns in chat interface
  setMessages(data.session.turns.map(turn => ({
    role: 'user',
    content: turn.user_input,
  })).concat(...));
};
```

---

## 📋 IMPLEMENTATION CHECKLIST

### ✅ Critical Fixes (Do First)

- [ ] **Fix 1:** Update `dialogue.update_session()` parameters (Line 474)
- [ ] **Fix 2:** Add persistence after tool execution (Lines 365-391)
- [ ] **Fix 3:** Test SQLite database creation (`data/sessions.db`)
- [ ] **Fix 4:** Verify turns are saved to database
- [ ] **Fix 5:** Test conversation history survives server restart

### ⚡ High Priority

- [ ] Load conversation history on WebSocket connect
- [ ] Inject SQLite history into LLM context
- [ ] Add conversation search tool for agent
- [ ] Add REST API endpoints for history retrieval

### 🎨 Nice to Have

- [ ] Frontend conversation history sidebar
- [ ] Search conversations UI
- [ ] Export conversations to JSON/PDF
- [ ] Delete conversation feature

---

## 🧪 TESTING PLAN

### Test 1: Basic Persistence
```
1. Start server: python -m src.api.websocket_server
2. Connect to WebSocket
3. Send message: "Hello, my name is John"
4. Agent responds
5. CHECK: data/sessions.db file created
6. CHECK: SELECT * FROM sessions; (should show 1 row)
7. CHECK: SELECT * FROM turns; (should show 1 row)
```

### Test 2: Conversation Continuity
```
1. Send message: "Remember, my favorite color is blue"
2. Agent responds
3. Disconnect WebSocket
4. Restart server
5. Reconnect WebSocket
6. Send message: "What's my favorite color?"
7. EXPECTED: Agent says "Blue" (remembers from previous session)
```

### Test 3: Tool Execution Persistence
```
1. Send message: "What's the weather?"
2. Agent uses weather tool
3. CHECK: SELECT * FROM turns WHERE intent='tool_execution';
4. EXPECTED: Turn saved with tool_execution intent
```

### Test 4: Multi-Session Persistence
```
1. Create 3 different conversations
2. CHECK: SELECT COUNT(*) FROM sessions; (should be 3)
3. CHECK: Each session has correct user_id
4. CHECK: Can retrieve all 3 sessions via API
```

---

## 📊 SUCCESS METRICS

✅ **Critical:**
- SQLite database file created at `data/sessions.db`
- Every conversation turn saved to database
- Conversation history survives server restart
- Agent can access past conversations

✅ **Important:**
- Agent uses past context when generating responses
- User can retrieve conversation history via API
- Tool executions are persisted

✅ **Nice:**
- Frontend displays conversation history
- User can search past conversations
- Export/delete functionality works

---

## ⚠️ POTENTIAL ISSUES

### Issue 1: Session ID vs User ID confusion
**Problem:** Currently using session_id as user_id (single user mode)
**Solution:** For now, keep it simple. Add proper user_id later with authentication.

### Issue 2: Large conversation history
**Problem:** Loading all turns into context might exceed LLM token limits
**Solution:** Use `get_recent_turns(n=10)` to limit context size

### Issue 3: Database file permissions
**Problem:** SQLite file might not be writable in production
**Solution:** Ensure `data/` directory has write permissions

### Issue 4: Concurrent writes
**Problem:** Multiple WebSocket connections writing to SQLite
**Solution:** SQLite handles this with WAL mode. Consider connection pooling if issues arise.

---

## 🚀 DEPLOYMENT NOTES

### Development
```bash
# Start backend with SQLite enabled
python -m src.api.websocket_server

# Check database
sqlite3 data/sessions.db "SELECT * FROM sessions;"
```

### Production (Render/Railway)
```bash
# Ensure data directory is persistent
# Add volume mount: /app/data -> persistent storage

# Environment variable
ENABLE_CONVERSATION_PERSISTENCE=true
```

### Vercel (Frontend)
```bash
# Add API routes for conversation history
# Use Next.js API routes to proxy to backend
```

---

## 📚 FILES TO MODIFY

### Backend (Python)
1. ✏️ `src/api/websocket_server.py` - Fix persistence calls
2. ✏️ `src/agents/user_tools.py` - Add conversation search tool (NEW)
3. ✅ `src/storage/sqlite_store.py` - Already good
4. ✅ `src/memory/dialogue_state.py` - Already good

### Frontend (TypeScript)
5. 🎨 `web/src/components/chat/ConversationHistory.tsx` - History sidebar (NEW)
6. 🎨 `web/src/hooks/useWebSocket.ts` - Load history (MODIFY)
7. 🎨 `web/src/app/api/conversations/route.ts` - API proxy (NEW)

### Configuration
8. 📝 `.env` - Add persistence flags
9. 📝 `config/assistant_config.yaml` - Enable persistence settings

---

## 🎯 NEXT STEPS

**Option A: Quick Fix (30 minutes)**
- Fix the 3 critical changes in `websocket_server.py`
- Test that conversations are saved
- Verify persistence works

**Option B: Complete Implementation (2-3 hours)**
- All Phase 1 + Phase 2 changes
- Add REST API endpoints
- Test end-to-end

**Option C: Full Feature (1 day)**
- All phases including frontend
- Conversation history UI
- Search and export features

---

**Which option would you like me to implement?**
