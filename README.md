# Voice Assistant Baseline

A privacy-first, cross-platform voice assistant with wake word detection, intent recognition, context management, and local action execution capabilities.

## Features

- 🎙️ **Wake Word Activation**: Hands-free activation using "Hey Assistant"
- 🗣️ **Intent Recognition**: Understand informational, task-based, and conversational queries
- 🧠 **Context Management**: Remember last 5 conversation exchanges
- ⚡ **Action Execution**: Execute local scripts and system commands via voice
- 🔒 **Privacy-First**: In-memory context by default, optional encrypted persistence
- 🌐 **Cross-Platform**: Windows 10+, macOS 11+, Linux Ubuntu 20.04+, Raspberry Pi 4/5
- 🔄 **Hybrid Architecture**: Local-first processing with cloud fallback for quality

## Quick Start

See [Quickstart Guide](specs/001-voice-assistant-baseline/quickstart.md) for detailed setup instructions.

### Installation

```bash
# Clone repository
git clone https://github.com/your-org/voice-assistant.git
cd voice-assistant
git checkout 001-voice-assistant-baseline

# Run installation script
chmod +x scripts/install_dependencies.sh
./scripts/install_dependencies.sh

# Configure environment
cp config/.env.template config/.env
# Edit config/.env with your API keys and preferences

# Setup wake word model
chmod +x scripts/setup_wake_word.sh
./scripts/setup_wake_word.sh
```

### Running

```bash
# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Run the assistant
python src/cli/assistant.py
```

## Architecture

### Technology Stack

- **Language**: Python 3.10+
- **Wake Word**: pvporcupine (Picovoice Porcupine)
- **STT**: OpenAI Whisper (local) + OpenAI API (fallback)
- **LLM**: Gemini API + Ollama (local fallback)
- **TTS**: ElevenLabs API + Piper (local fallback)
- **Audio**: PyAudio + sounddevice (cross-platform)
- **Automation**: Playwright MCP Server
- **Storage**: In-memory + encrypted SQLite (opt-in)

### Project Structure

```
voice-assistant/
├── src/
│   ├── core/           # Core system components
│   ├── services/       # STT, LLM, TTS, wake word services
│   ├── models/         # Data models
│   ├── storage/        # Storage implementations
│   ├── api/            # API endpoints
│   ├── cli/            # CLI entry point
│   └── utils/          # Utilities
├── tests/              # Test suites
├── config/             # Configuration files
├── scripts/            # Setup and utility scripts
├── specs/              # Design documentation
└── history/            # Development history
```

## Documentation

- **[Quickstart Guide](specs/001-voice-assistant-baseline/quickstart.md)**: Setup and usage
- **[Specification](specs/001-voice-assistant-baseline/spec.md)**: Feature requirements and user stories
- **[Implementation Plan](specs/001-voice-assistant-baseline/plan.md)**: Architecture decisions
- **[Tasks](specs/001-voice-assistant-baseline/tasks.md)**: Implementation task breakdown
- **[Data Model](specs/001-voice-assistant-baseline/data-model.md)**: Entity definitions
- **[API Contracts](specs/001-voice-assistant-baseline/contracts/)**: Service interfaces

## Performance Targets

- ⚡ Wake word activation: <1 second
- 🎯 Query processing: <2 seconds
- 🚀 End-to-end (wake to response): <3 seconds
- 📊 Speech recognition accuracy: >95% WER

## Privacy & Security

- **In-Memory Default**: No conversation data stored by default
- **Opt-In Persistence**: User-configurable encrypted storage
- **Local-First Processing**: Prioritize on-device processing
- **Encryption**: AES-256 (Fernet) with PBKDF2 key derivation

## Platform Support

- ✅ Windows 10+
- ✅ macOS 11+
- ✅ Linux Ubuntu 20.04+
- ✅ Raspberry Pi 4/5 (Raspbian)

## Testing

```bash
# Run all tests
pytest

# Run specific test suites
pytest tests/unit/          # Unit tests
pytest tests/integration/   # Integration tests
pytest tests/contract/      # Contract tests

# Coverage report
pytest --cov=src --cov-report=html
```

## Development Status

**Current Phase**: Phase 1 - Setup (In Progress)

**Roadmap**:
- [x] Specification and planning complete
- [ ] Phase 1: Setup (T001-T010)
- [ ] Phase 2: Foundational infrastructure (T011-T021)
- [ ] Phase 3: Wake word activation (T022-T031)
- [ ] Phase 4: Intent recognition (T032-T046)
- [ ] Phase 5: Context management (T047-T059)
- [ ] Phase 6: Action execution (T060-T074)
- [ ] Phase 7: Cross-cutting concerns (T075-T087)
- [ ] Phase 8: Polish and finalization (T088-T095)

## Contributing

See [CLAUDE.md](CLAUDE.md) for development guidelines and agent instructions.

## License

[Your License Here]

## Support

For issues or questions:
1. Check the [Quickstart Guide](specs/001-voice-assistant-baseline/quickstart.md)
2. Review the [Troubleshooting Section](specs/001-voice-assistant-baseline/quickstart.md#troubleshooting)
3. Open an issue on GitHub
4. Check project documentation in `specs/`
