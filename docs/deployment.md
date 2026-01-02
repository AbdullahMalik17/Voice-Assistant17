# Deployment Guide: Voice Assistant Baseline

**Version**: 1.0.0
**Date**: 2026-01-02

## Overview

This guide covers deployment options for the Voice Assistant, from development to production environments.

---

## Deployment Options

### 1. Development Environment

For local development and testing.

```bash
# Clone and setup
git clone https://github.com/your-org/voice-assistant.git
cd voice-assistant

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp config/.env.template config/.env
# Edit config/.env with your settings

# Run assistant
python -m src.cli.assistant
```

### 2. Production Deployment (Desktop)

For dedicated desktop machines (Windows, macOS, Linux).

#### System Preparation

```bash
# Create dedicated user (Linux)
sudo useradd -m -s /bin/bash voice-assistant
sudo su - voice-assistant

# Clone repository
git clone https://github.com/your-org/voice-assistant.git ~/voice-assistant
cd ~/voice-assistant

# Run installation script
chmod +x scripts/install_dependencies.sh
./scripts/install_dependencies.sh
```

#### Service Configuration (Linux systemd)

Create `/etc/systemd/system/voice-assistant.service`:

```ini
[Unit]
Description=Voice Assistant Service
After=network.target pulseaudio.service

[Service]
Type=simple
User=voice-assistant
WorkingDirectory=/home/voice-assistant/voice-assistant
Environment=PATH=/home/voice-assistant/voice-assistant/venv/bin
ExecStart=/home/voice-assistant/voice-assistant/venv/bin/python -m src.cli.assistant
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable voice-assistant
sudo systemctl start voice-assistant
sudo systemctl status voice-assistant
```

#### Windows Service

Use NSSM (Non-Sucking Service Manager):

```powershell
# Download NSSM from https://nssm.cc
nssm install VoiceAssistant

# Configure in GUI:
# Path: C:\VoiceAssistant\venv\Scripts\python.exe
# Startup directory: C:\VoiceAssistant
# Arguments: -m src.cli.assistant
```

### 3. Raspberry Pi Deployment

Optimized for Raspberry Pi 4/5.

#### Hardware Requirements

- Raspberry Pi 4 (4GB RAM recommended) or Pi 5
- USB microphone (or HAT with microphone)
- Speakers or 3.5mm audio output
- 16GB+ microSD card
- Power supply (5V 3A for Pi 4, 5V 5A for Pi 5)

#### Raspberry Pi OS Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install audio dependencies
sudo apt install -y portaudio19-dev python3-pyaudio
sudo apt install -y pulseaudio pulseaudio-utils

# Install Python development headers
sudo apt install -y python3-dev python3-pip python3-venv

# Clone and setup
git clone https://github.com/your-org/voice-assistant.git ~/voice-assistant
cd ~/voice-assistant

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

#### Audio Configuration

```bash
# Test microphone
arecord -l  # List recording devices
arecord -d 5 test.wav  # Record 5 seconds

# Test speakers
aplay -l  # List playback devices
aplay test.wav

# Set default audio device in ~/.asoundrc if needed
```

#### Autostart on Boot

Add to `/etc/rc.local` or use systemd as above.

#### Performance Optimization

```bash
# Use whisper-tiny for faster processing
echo "STT_MODEL=whisper-tiny" >> config/.env

# Enable local-only mode to reduce latency
echo "STT_MODE=local" >> config/.env
echo "LLM_MODE=local" >> config/.env
echo "TTS_MODE=local" >> config/.env
```

---

## Configuration for Deployment

### Environment Variables

**Required (for cloud services)**:
```bash
OPENAI_API_KEY=sk-...        # For Whisper API fallback
GEMINI_API_KEY=AIza...       # For Gemini LLM
ELEVENLABS_API_KEY=...       # For ElevenLabs TTS
```

**Optional**:
```bash
# Privacy
ENABLE_CONVERSATION_PERSISTENCE=false
CONVERSATION_ENCRYPTION_KEY=...

# Performance
WAKE_WORD_SENSITIVITY=0.5
STT_MODEL=whisper-base
LLM_MODEL=gemini-pro

# Logging
LOG_LEVEL=INFO
LOG_DIR=/var/log/voice-assistant
METRICS_ENABLED=true
```

### Log Rotation

Configure logrotate for production:

```bash
# /etc/logrotate.d/voice-assistant
/var/log/voice-assistant/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 voice-assistant voice-assistant
}
```

---

## Security Considerations

### API Key Protection

1. Never commit `.env` files to version control
2. Use environment variables in production
3. Consider using a secrets manager (HashiCorp Vault, AWS Secrets Manager)

### Network Security

1. Run behind firewall - no inbound ports required
2. Outbound connections:
   - `api.openai.com` (STT API)
   - `generativelanguage.googleapis.com` (Gemini API)
   - `api.elevenlabs.io` (TTS API)

### Audio Privacy

1. Audio is processed locally by default (Whisper)
2. Only transcribed text is sent to cloud LLM
3. No audio recordings are stored unless explicitly configured

### Encrypted Storage

If context persistence is enabled:
- Uses Fernet encryption (AES-128)
- Encryption key derived from password via PBKDF2
- Data stored locally only

---

## Monitoring

### Health Checks

The assistant logs health events:
- `SYSTEM_STARTUP` - Startup complete
- `WAKE_WORD_DETECTED` - Wake word activation
- `STT_COMPLETED` - Transcription complete
- `LLM_RESPONSE` - LLM response generated
- `TTS_COMPLETED` - Speech output complete
- `SYSTEM_SHUTDOWN` - Graceful shutdown

### Metrics Collection

Metrics are exported to `logs/metrics.json`:
```json
{
  "wake_word_detections": 150,
  "stt_latency_avg_ms": 850,
  "llm_latency_avg_ms": 1200,
  "tts_latency_avg_ms": 450,
  "total_interactions": 145,
  "errors": 3
}
```

### Alerting (Optional)

Integrate with monitoring systems:
```bash
# Prometheus exporter (requires additional setup)
pip install prometheus_client

# Add to assistant config
METRICS_PROMETHEUS_PORT=9090
```

---

## Backup and Recovery

### What to Back Up

1. `config/.env` - Configuration and API keys
2. `config/assistant_config.yaml` - Custom settings
3. `logs/` - Historical logs (optional)
4. Encrypted context storage (if persistence enabled)

### Backup Script

```bash
#!/bin/bash
BACKUP_DIR="/backup/voice-assistant"
DATE=$(date +%Y%m%d)

mkdir -p $BACKUP_DIR

# Backup config
tar -czf $BACKUP_DIR/config-$DATE.tar.gz config/

# Backup logs (last 7 days)
find logs/ -mtime -7 -name "*.log" | tar -czf $BACKUP_DIR/logs-$DATE.tar.gz -T -

echo "Backup complete: $BACKUP_DIR"
```

### Recovery Steps

1. Stop the service: `sudo systemctl stop voice-assistant`
2. Restore config: `tar -xzf config-YYYYMMDD.tar.gz -C .`
3. Verify configuration: `cat config/.env`
4. Start the service: `sudo systemctl start voice-assistant`

---

## Updating

### Standard Update

```bash
# Stop service
sudo systemctl stop voice-assistant

# Backup current version
cp -r ~/voice-assistant ~/voice-assistant.backup

# Pull updates
cd ~/voice-assistant
git pull origin main

# Update dependencies
source venv/bin/activate
pip install -r requirements.txt --upgrade

# Start service
sudo systemctl start voice-assistant
```

### Rollback

```bash
sudo systemctl stop voice-assistant
rm -rf ~/voice-assistant
mv ~/voice-assistant.backup ~/voice-assistant
sudo systemctl start voice-assistant
```

---

## Troubleshooting Deployment Issues

See `docs/troubleshooting.md` for detailed troubleshooting guidance.

### Quick Checks

```bash
# Check service status
sudo systemctl status voice-assistant

# View logs
journalctl -u voice-assistant -f

# Check audio devices
arecord -l
aplay -l

# Test network
ping api.openai.com
```

---

## Support

For deployment issues:
1. Check logs: `tail -f logs/assistant.log`
2. Verify configuration: `python -c "from src.core.config import get_config; print(get_config())"`
3. Test individual components manually
4. Open an issue on GitHub with logs and configuration (redact API keys)
