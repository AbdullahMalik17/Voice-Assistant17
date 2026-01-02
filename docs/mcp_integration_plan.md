# MCP Integration Plan for Voice Assistant

## Overview

Extend the Voice Assistant with MCP (Model Context Protocol) servers to add powerful integrations like email, calendar, smart home, and more.

---

## Proposed MCP Integrations

### 1. Gmail MCP Server
**Use Case**: "Send an email to John about the meeting tomorrow"

**Capabilities**:
- Send emails via voice
- Read unread emails
- Search emails
- Create drafts

**Example Commands**:
```
"Send an email to john@example.com saying I'll be late"
"Read my unread emails"
"Do I have any emails from Sarah?"
"Reply to the last email saying thank you"
```

### 2. Google Calendar MCP Server
**Use Case**: "Schedule a meeting for tomorrow at 3pm"

**Capabilities**:
- Create events
- Check schedule
- Find free time
- Set reminders

**Example Commands**:
```
"What's on my calendar today?"
"Schedule a meeting with Bob tomorrow at 2pm"
"When am I free this week?"
"Remind me about the dentist appointment"
```

### 3. Home Assistant MCP Server
**Use Case**: "Turn off the living room lights"

**Capabilities**:
- Control smart lights
- Adjust thermostat
- Lock/unlock doors
- Check sensor status

**Example Commands**:
```
"Turn on the bedroom lights"
"Set the thermostat to 72 degrees"
"Is the front door locked?"
"Turn off all lights"
```

### 4. Spotify MCP Server
**Use Case**: "Play my workout playlist"

**Capabilities**:
- Play/pause music
- Skip tracks
- Search songs
- Control volume

**Example Commands**:
```
"Play some jazz music"
"Skip this song"
"What song is this?"
"Add this to my favorites"
```

### 5. Todoist/Tasks MCP Server
**Use Case**: "Add buy groceries to my todo list"

**Capabilities**:
- Create tasks
- List tasks
- Mark complete
- Set due dates

**Example Commands**:
```
"Add milk to my shopping list"
"What's on my todo list?"
"Mark the laundry task as done"
"What tasks are due today?"
```

### 6. Weather MCP Server
**Use Case**: "What's the weather forecast?"

**Capabilities**:
- Current conditions
- Forecasts
- Alerts
- Historical data

**Example Commands**:
```
"What's the weather like?"
"Will it rain tomorrow?"
"What's the temperature outside?"
"Do I need an umbrella today?"
```

### 7. Notes/Notion MCP Server
**Use Case**: "Take a note about the project idea"

**Capabilities**:
- Create notes
- Search notes
- Update pages
- Query databases

**Example Commands**:
```
"Take a note: remember to call mom"
"Find my notes about the project"
"Add to my ideas list: voice-controlled robot"
```

---

## Architecture

### Current Flow
```
Wake Word → STT → Intent Classifier → LLM/Action Executor → TTS
```

### Extended Flow with MCP
```
Wake Word → STT → Intent Classifier → MCP Router → MCP Server(s) → TTS
                                    ↓
                              LLM (for complex queries)
```

### Integration Points

1. **Intent Classifier Enhancement**
   - Add new intent types: EMAIL, CALENDAR, SMART_HOME, MUSIC, TASKS, NOTES
   - Entity extraction for: recipients, dates, device names, etc.

2. **MCP Router Service** (new)
   - Routes intents to appropriate MCP servers
   - Handles MCP protocol communication
   - Aggregates responses

3. **Action Executor Extension**
   - Add MCP action types
   - Handle async MCP calls
   - Format responses for TTS

---

## Implementation Plan

### Phase 1: MCP Infrastructure
- [ ] Create MCP client wrapper in `src/services/mcp_client.py`
- [ ] Add MCP configuration to `config/assistant_config.yaml`
- [ ] Extend intent classifier with new intent types
- [ ] Create MCP router in `src/services/mcp_router.py`

### Phase 2: Gmail Integration
- [ ] Set up Gmail MCP server
- [ ] Add EMAIL intent type and patterns
- [ ] Implement email-specific entity extraction
- [ ] Add Gmail actions to router

### Phase 3: Calendar Integration
- [ ] Set up Google Calendar MCP server
- [ ] Add CALENDAR intent type and patterns
- [ ] Implement date/time entity extraction
- [ ] Add calendar actions to router

### Phase 4: Smart Home Integration
- [ ] Set up Home Assistant MCP server
- [ ] Add SMART_HOME intent type and patterns
- [ ] Implement device entity extraction
- [ ] Add smart home actions to router

### Phase 5: Additional Integrations
- [ ] Spotify MCP
- [ ] Todoist MCP
- [ ] Weather MCP
- [ ] Notes/Notion MCP

---

## Configuration Example

```yaml
# config/assistant_config.yaml (extended)

mcp:
  enabled: true
  servers:
    gmail:
      enabled: true
      server_path: "mcp-servers/gmail"
      credentials_path: "config/gmail_credentials.json"

    calendar:
      enabled: true
      server_path: "mcp-servers/google-calendar"
      credentials_path: "config/calendar_credentials.json"

    home_assistant:
      enabled: true
      server_url: "http://homeassistant.local:8123"
      token_env: "HASS_TOKEN"

    spotify:
      enabled: true
      server_path: "mcp-servers/spotify"
      client_id_env: "SPOTIFY_CLIENT_ID"
      client_secret_env: "SPOTIFY_CLIENT_SECRET"

intent:
  types:
    - "INFORMATIONAL"
    - "TASK_BASED"
    - "CONVERSATIONAL"
    - "EMAIL"          # New
    - "CALENDAR"       # New
    - "SMART_HOME"     # New
    - "MUSIC"          # New
    - "TASKS"          # New
    - "NOTES"          # New
```

---

## Intent Patterns (Examples)

### Email Intents
```python
EMAIL_PATTERNS = {
    "send": r"(send|write|compose|email|mail).*(to|email)",
    "read": r"(read|check|show|open).*(email|mail|inbox)",
    "search": r"(find|search|look for).*(email|mail)",
    "reply": r"(reply|respond|answer).*(email|mail)",
}
```

### Calendar Intents
```python
CALENDAR_PATTERNS = {
    "create": r"(schedule|create|add|book|set up).*(meeting|event|appointment)",
    "query": r"(what|when|show|check).*(calendar|schedule|meeting|free)",
    "reminder": r"(remind|reminder|alert)",
}
```

### Smart Home Intents
```python
SMART_HOME_PATTERNS = {
    "lights": r"(turn|switch|dim|brighten).*(light|lamp)",
    "thermostat": r"(set|change|adjust).*(temperature|thermostat|heat|cool)",
    "lock": r"(lock|unlock).*(door|gate)",
    "status": r"(is|are|check).*(locked|on|off|open|closed)",
}
```

---

## Security Considerations

1. **OAuth Tokens**: Store securely, never in code
2. **Scope Limitation**: Request minimal permissions
3. **Confirmation**: Require voice confirmation for sensitive actions
4. **Audit Logging**: Log all MCP actions
5. **Rate Limiting**: Prevent abuse

---

## Example Voice Interactions

### Email
```
User: "Hey Assistant"
Assistant: "I'm listening"
User: "Send an email to Sarah about tomorrow's lunch"
Assistant: "What would you like to say in the email?"
User: "Let's meet at noon at the Italian place"
Assistant: "Sending email to Sarah: Let's meet at noon at the Italian place. Sent successfully."
```

### Calendar
```
User: "Hey Assistant"
Assistant: "I'm listening"
User: "What's on my schedule tomorrow?"
Assistant: "Tomorrow you have: 9am team standup, 11am dentist appointment, and 3pm call with client."
```

### Smart Home
```
User: "Hey Assistant"
Assistant: "I'm listening"
User: "Turn off all the lights and set the thermostat to 68"
Assistant: "Turning off all lights. Setting thermostat to 68 degrees. Done."
```

---

## Getting Started

1. **Install MCP Servers**:
   ```bash
   # Gmail
   npx @anthropic/create-mcp-server gmail

   # Or use existing community servers
   npm install -g @anthropic/mcp-server-gmail
   ```

2. **Configure Credentials**:
   - Set up OAuth for Google services
   - Get API tokens for third-party services
   - Store in `.env` or secure credential store

3. **Enable in Config**:
   ```yaml
   mcp:
     enabled: true
     servers:
       gmail:
         enabled: true
   ```

4. **Test**:
   ```bash
   python test_mcp_integration.py
   ```

---

## Resources

- [MCP Documentation](https://modelcontextprotocol.io)
- [MCP Server Examples](https://github.com/anthropics/mcp-servers)
- [Claude Code MCP Guide](https://docs.anthropic.com/claude-code/mcp)
