# Voice_Assistant Constitution

## Core Objective
To develop a responsive, privacy-centric, and highly extensible AI-powered voice assistant capable of natural language understanding and task automation.

## Guiding Principles

### 1. Privacy First
All voice processing should aim for local execution where possible. User data must never be stored without explicit consent.

### 2. Latency Optimization
Responses must be generated and spoken within sub-500ms thresholds to maintain natural conversation flow.

### 3. Modular Architecture
The system must decouple the **STT** (Speech-to-Text), **LLM** (Logic Engine), and **TTS** (Text-to-Speech) layers to allow for easy hardware/software swapping.

### 4. Reliability
The system should handle intermittent internet connectivity gracefully using "Edge-first" logic.

### 5. System-Wide Control & Automation
The agent must have full system control capabilities to execute complex automation tasks, interact with web applications, and perform desktop operations through browser-based interfaces using Playwright.

## Technical Stack (Baseline)

- **Language**: Python 3.10+
- **STT**: OpenAI Whisper (Local/API)
- **Brain**: Gemini API / Ollama (Local fallback)
- **TTS**: ElevenLabs or Piper (for fast local synthesis)
- **Framework**: FastAPI for the backend service layer
- **System Control**: Playwright MCP Server for laptop/desktop automation

## System Control & Automation Framework

### Playwright Integration for System Control

The agent has full access to Playwright MCP tools for comprehensive system control and automation. This enables interaction with web applications, desktop software (via browser interfaces), and system-level operations.

#### Core Capabilities

**1. Browser Automation & Control**
- Navigate to any URL (`browser_navigate`)
- Take snapshots and screenshots for visual feedback (`browser_snapshot`, `browser_take_screenshot`)
- Execute JavaScript for advanced interactions (`browser_evaluate`)
- Monitor console messages and network requests (`browser_console_messages`, `browser_network_requests`)
- Handle browser dialogs, file uploads, and forms (`browser_handle_dialog`, `browser_file_upload`, `browser_fill_form`)

**2. User Interface Interaction**
- Click elements, buttons, and links (`browser_click`)
- Type text into input fields (`browser_type`)
- Fill complex forms with multiple fields (`browser_fill_form`)
- Select dropdown options (`browser_select_option`)
- Drag and drop elements (`browser_drag`)
- Hover over elements (`browser_hover`)
- Press keyboard keys (`browser_press_key`)

**3. Advanced Automation**
- Run custom Playwright code snippets (`browser_run_code`)
- Multi-tab management (`browser_tabs`)
- Wait for content to appear/disappear (`browser_wait_for`)
- Resize browser windows (`browser_resize`)
- Navigate backward through history (`browser_navigate_back`)

**4. Visual Monitoring & Debugging**
- Capture full-page or element-specific screenshots
- Generate accessibility snapshots for better element targeting
- Monitor network traffic and API calls
- Track console errors and warnings

#### Automation Policies

**Authorization & Safety:**
- Always confirm destructive actions with user before executing
- Never automate financial transactions without explicit user confirmation
- Respect authentication boundaries - ask for credentials, never hardcode
- Use accessibility snapshots over screenshots for element interaction (more reliable)

**Best Practices:**
- Use `browser_snapshot` before any interaction to understand page structure
- Prefer `browser_fill_form` for multi-field forms (more efficient)
- Always verify element references from snapshots before clicking/typing
- Monitor console errors after navigation to catch issues early
- Use `browser_wait_for` when dealing with dynamic content
- Limit screenshot usage to visual confirmation only (not for element targeting)

**Execution Strategy:**
1. **Plan First**: Understand user's automation goal completely
2. **Navigate**: Open the target URL or application
3. **Snapshot**: Capture page structure using `browser_snapshot`
4. **Interact**: Perform actions using exact element references from snapshot
5. **Verify**: Take screenshots or check console for confirmation
6. **Report**: Provide clear feedback on success/failure

**Use Cases Enabled:**
- Web scraping and data extraction
- Form automation and data entry
- Testing web applications
- Monitoring dashboards and applications
- Interacting with web-based system tools
- Automating repetitive browser-based tasks
- Controlling web-based IoT devices or control panels
- Accessing cloud-based system administration interfaces

#### Integration with Voice Assistant

The Playwright system control capabilities should be seamlessly integrated with voice commands:
- User can issue voice commands for browser automation
- Agent executes Playwright operations based on natural language intent
- Visual feedback (screenshots) can be analyzed and described back to user
- Multi-step automation workflows can be triggered by single voice commands

**Example Voice Workflows:**
- "Open Gmail and check my unread messages"
- "Fill out this form with my information"
- "Navigate to the settings page and enable dark mode"
- "Monitor this dashboard and alert me if status changes"
- "Take a screenshot of the current page"
