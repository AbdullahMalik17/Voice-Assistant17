# Voice Assistant with Web Interface and Agent Tools

This repository contains a voice assistant with a web interface that integrates a comprehensive set of agent tools.

## Features

- **Web Interface**: Next.js-based web interface with real-time chat and voice capabilities
- **WebSocket Communication**: Real-time communication between web interface and backend
- **Agent Tools**: 27+ tools across multiple categories:
  - System tools (system status, app launching)
  - Productivity tools (timers)
  - Information tools (web search, weather)
  - Browser automation tools
  - System control tools
  - Gmail/Drive API tools
- **Agentic Planning**: Complex request decomposition and execution
- **Voice Processing**: STT (Speech-to-Text) and TTS (Text-to-Speech)
- **Memory**: Persistent and semantic memory capabilities

## Setup

### Backend Setup

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
# Copy the example environment file and fill in your values
cp .env.example .env
```

3. Install additional dependencies for specific tools:
```bash
# For browser automation tools
playwright install

# For Google APIs (if using Gmail/Drive tools)
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

### Frontend Setup

1. Navigate to the web directory:
```bash
cd web
```

2. Install dependencies:
```bash
npm install
```

3. Set up environment variables:
```bash
cp .env.local.example .env.local
# Edit .env.local to set your WebSocket URL
```

## Running the Application

### Backend Server

```bash
cd src/api
python websocket_server.py
```

The server will start on `http://localhost:8000` with WebSocket endpoint at `ws://localhost:8000/ws/voice`.

### Frontend Server

In a separate terminal:

```bash
cd web
npm run dev
```

The web interface will be available at `http://localhost:3000`.

## Using Agent Tools

The agent tools are automatically used when the system detects appropriate requests. Examples include:

- "Open Chrome" - uses `launch_app` tool
- "Find file named report.pdf" - uses `find_file` tool
- "Check my system status" - uses `system_status` tool
- "Set a timer for 5 minutes" - uses `set_timer` tool
- "Search for Python tutorials" - uses `web_search` tool
- "Show my emails" - uses `list_emails` tool
- "Open Gmail" - uses `open_gmail` tool

## Architecture

```
┌─────────────────┐    WebSocket     ┌──────────────────┐
│   Web UI       │◄────────────────►│  Backend API    │
│                │                  │                 │
│ - Next.js 14   │    REST API      │ - FastAPI       │
│ - React 18     │◄────────────────►│ - WebSockets    │
│ - TypeScript   │                  │ - Agent Tools   │
│ - Tailwind CSS │                  │ - STT/TTS/LLM   │
└─────────────────┘                  └──────────────────┘
```

## Deployment

### Backend
The FastAPI backend can be deployed to any cloud provider that supports Python applications (AWS, GCP, Azure, etc.).

### Frontend
The Next.js frontend can be deployed to Vercel, Netlify, or any platform that supports Next.js applications.

## Configuration

Key configuration options:

- `NEXT_PUBLIC_WS_URL`: WebSocket URL for the web interface (in `.env.local`)
- API keys for various services (in `.env`)
- CORS settings for the backend

## Development

For development, run both servers in parallel:

Backend:
```bash
cd src/api
python websocket_server.py
```

Frontend:
```bash
cd web
npm run dev
```

## Troubleshooting

1. If tools are not working, check that all required dependencies are installed
2. Verify environment variables are properly set
3. Check logs for specific error messages
4. Ensure the WebSocket connection is established between frontend and backend