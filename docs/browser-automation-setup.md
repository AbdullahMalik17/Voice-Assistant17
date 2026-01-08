# Browser Automation & System Control Setup Guide

## Overview

Phase 1 of the Browser Automation integration adds comprehensive laptop control capabilities to your Voice Assistant:

- **Browser Automation**: Control Chrome/Firefox/WebKit via Playwright
- **Gmail & Google Drive**: Open and interact with Google services
- **System Control**: File operations, screenshots, window management
- **Cross-Platform**: Works on Windows, macOS, and Linux

## Installation

### Step 1: Install Dependencies

#### Windows:
```bash
# Navigate to project root
cd F:\Voice_Assistant

# Run the installation script
scripts\install_browser_automation.bat

# Or install manually
python -m pip install playwright psutil pyautogui pywin32
playwright install
```

#### macOS/Linux:
```bash
# Navigate to project root
cd ~/Voice_Assistant

# Make script executable
chmod +x scripts/install_browser_automation.sh

# Run the installation script
./scripts/install_browser_automation.sh

# Or install manually
python3 -m pip install playwright psutil pyautogui
playwright install
```

### Step 2: Verify Installation

```bash
# Test Playwright
python -c "from playwright.sync_api import sync_playwright; print('✓ Playwright OK')"

# Test system automation
python -c "import psutil; print('✓ psutil OK')"
python -c "import pyautogui; print('✓ pyautogui OK')"
```

### Step 3: Configure Browser Settings

Edit `config/assistant_config.yaml`:

```yaml
# Browser automation settings
browser:
  enabled: true           # Enable browser automation
  browser_type: "chromium"  # chromium, firefox, or webkit
  headless: false         # false = show browser window
  default_timeout_ms: 30000
  screenshot_on_error: true
```

## Available Voice Commands

### Browser Navigation

| Voice Command | Action |
|--------------|--------|
| "Open Gmail" | Opens Gmail in browser |
| "Open Google Drive" | Opens Google Drive in browser |
| "Go to YouTube" | Navigates to YouTube |
| "Navigate to github.com" | Opens specified website |
| "Search for Python tutorials" | Google search |

### System Control

| Voice Command | Action |
|--------------|--------|
| "Take a screenshot" | Captures screen |
| "Find file named report.pdf" | Searches for file |
| "Show system info" | Displays CPU/RAM/disk stats |
| "Minimize all windows" | Shows desktop |
| "List running processes" | Shows top processes |
| "Create folder MyProject" | Creates new folder |

### Email & Drive (Browser-based)

| Voice Command | Action |
|--------------|--------|
| "Check my email" | Opens Gmail |
| "Open my Drive" | Opens Google Drive |

## Testing

### Test 1: Browser Navigation

```bash
# Start backend
python -m uvicorn src.api.websocket_server:app --host 0.0.0.0 --port 8000

# In web interface (http://localhost:3000), say:
"Open Gmail"
```

**Expected Result**: Browser opens and navigates to Gmail

### Test 2: Google Search

```
Voice: "Search for artificial intelligence"
```

**Expected Result**: Browser opens, performs Google search

### Test 3: Screenshot

```
Voice: "Take a screenshot"
```

**Expected Result**: Screenshot captured and displayed in chat

### Test 4: System Info

```
Voice: "Show system info"
```

**Expected Result**: CPU, RAM, disk stats displayed

### Test 5: File Search

```
Voice: "Find file named config"
```

**Expected Result**: List of matching files with paths

## Architecture

```
┌─────────────────────────────────────────────┐
│  Voice Command: "Open Gmail"                │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────┐
│  IntentClassifier                            │
│  ├─ Type: TASK_BASED                        │
│  ├─ Action: EMAIL_ACCESS                    │
│  └─ Entities: {action: "open"}              │
└──────────────┬───────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────┐
│  AgenticPlanner (Tool Registry)              │
│  └─ Tool: OpenGmailTool                      │
└──────────────┬───────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────┐
│  BrowserAutomationService                    │
│  ├─ Initialize Playwright                   │
│  ├─ Launch Chromium                         │
│  └─ Navigate to mail.google.com             │
└──────────────┬───────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────┐
│  Browser Window Opens                        │
│  Gmail loads in Chromium                     │
└──────────────────────────────────────────────┘
```

## Registered Tools

### Browser Tools (AUTOMATION category)
- `browser_navigate` - Navigate to URL
- `browser_search` - Google search
- `open_gmail` - Open Gmail
- `open_google_drive` - Open Drive
- `browser_screenshot` - Capture page
- `browser_click` - Click element (requires confirmation)
- `browser_type` - Type text (requires confirmation)

### System Tools (SYSTEM category)
- `find_file` - Search for files
- `take_screenshot` - Capture screen
- `get_system_info` - System stats
- `minimize_windows` - Show desktop
- `list_processes` - Running processes
- `create_folder` - New folder (requires confirmation)
- `open_file_location` - Open in explorer

## Configuration Options

### Browser Types

```yaml
browser_type: "chromium"  # Default, fastest
browser_type: "firefox"   # Mozilla Firefox
browser_type: "webkit"    # Safari engine
```

### Headless Mode

```yaml
headless: false  # Show browser (default)
headless: true   # Background mode (faster, no UI)
```

### Timeouts

```yaml
default_timeout_ms: 30000  # 30 seconds
default_timeout_ms: 60000  # 60 seconds for slow networks
```

## Troubleshooting

### Issue: "Playwright not installed"

**Solution**:
```bash
pip install playwright
playwright install
```

### Issue: Browser doesn't open

**Solution**:
1. Check `browser.enabled: true` in config
2. Verify Playwright browsers installed: `playwright install chromium`
3. Check logs: `python -m uvicorn src.api.websocket_server:app --log-level debug`

### Issue: "pyautogui not found"

**Solution**:
```bash
pip install pyautogui
```

**Windows**: Also install `pywin32`:
```bash
pip install pywin32
```

### Issue: Screenshots not working

**Solution**:
- **Linux**: Install `python3-tk` and `python3-dev`
  ```bash
  sudo apt-get install python3-tk python3-dev
  ```
- **macOS**: Enable Screen Recording permissions in System Preferences

### Issue: File search slow

**Solution**:
- Specify directory: "Find file report.pdf in Documents"
- Index less files by limiting search path

## Next Steps: Phase 2

Phase 2 will add:
- **Gmail API**: Read/send emails programmatically
- **Google Drive API**: Download/upload files via API
- **OAuth2 Authentication**: Secure Google account access
- **Email composition**: Voice-driven email writing
- **Calendar integration**: Schedule events

## Security Considerations

- **Confirmation Required**: Dangerous operations (click, type, create folder) require confirmation
- **Command Allowlist**: Only whitelisted system commands allowed
- **No Credentials Stored**: Browser automation uses manual login
- **Local Execution**: All automation runs locally on your machine

## Performance

| Operation | Expected Time |
|-----------|--------------|
| Browser launch | 2-3 seconds |
| Page navigation | 1-2 seconds |
| Screenshot | <1 second |
| File search (10 results) | 1-3 seconds |
| System info | <0.5 seconds |

## Support

If you encounter issues:
1. Check this guide's Troubleshooting section
2. Review logs in terminal
3. Verify all dependencies installed
4. Test individual components (see Testing section)
