"""
Configuration Management for Voice Assistant
Loads and validates configuration from .env and YAML files
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator


class AudioConfig(BaseModel):
    """Audio input/output configuration"""
    sample_rate: int = Field(default=16000, ge=8000, le=48000)
    channels: int = Field(default=1, ge=1, le=2)
    chunk_size: int = Field(default=1024, ge=256, le=8192)
    input_device: Optional[int] = None
    output_device: Optional[int] = None


class ContextConfig(BaseModel):
    """Conversation context management configuration"""
    max_exchanges: int = Field(default=5, ge=1, le=20)
    timeout_seconds: int = Field(default=300, ge=60, le=1800)
    topic_shift_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    enable_persistence: bool = False


class NetworkConfig(BaseModel):
    """Network resilience configuration"""
    check_interval_seconds: int = Field(default=5, ge=1, le=60)
    retry_delay_seconds: int = Field(default=30, ge=5, le=300)
    max_queue_items: int = Field(default=10, ge=1, le=100)
    health_check_url: str = "https://www.google.com"
    dns_fallback: str = "8.8.8.8"


class ActionsConfig(BaseModel):
    """Action execution configuration"""
    require_confirmation: bool = False
    timeout_seconds: int = Field(default=30, ge=5, le=300)
    allowed_commands: list[str] = Field(default_factory=lambda: ["open", "status"])
    blocked_patterns: list[str] = Field(default_factory=lambda: ["rm -rf", "del /f", "format"])


class LoggingConfig(BaseModel):
    """Logging and monitoring configuration"""
    level: str = Field(default="INFO")
    format: str = Field(default="json")
    event_log_max_size_mb: int = Field(default=10, ge=1, le=100)
    event_log_backup_count: int = Field(default=5, ge=1, le=20)
    metrics_export_interval_seconds: int = Field(default=60, ge=10, le=300)
    console_output: bool = True

    @field_validator('level')
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'Log level must be one of: {valid_levels}')
        return v.upper()

    @field_validator('format')
    @classmethod
    def validate_log_format(cls, v: str) -> str:
        valid_formats = ['json', 'text']
        if v.lower() not in valid_formats:
            raise ValueError(f'Log format must be one of: {valid_formats}')
        return v.lower()


class WakeWordConfig(BaseModel):
    """Wake word detection configuration"""
    library: str = "openwakeword"
    sensitivity: float = Field(default=0.5, ge=0.0, le=1.0)
    model_path: str = "models/wake_word/"
    models: list[str] = Field(default_factory=lambda: ["alexa", "hey_jarvis"])


class AudioPreprocessorConfig(BaseModel):
    """Audio preprocessing configuration for noise reduction and AEC"""
    enabled: bool = True
    noise_reduction_enabled: bool = True
    noise_reduction_method: str = Field(default="spectral_gating")
    noise_threshold_db: float = Field(default=-40.0, ge=-80.0, le=0.0)
    aec_enabled: bool = False
    aec_filter_length: int = Field(default=1024, ge=256, le=4096)
    normalization_enabled: bool = True
    target_level_db: float = Field(default=-3.0, ge=-20.0, le=0.0)
    vad_enabled: bool = True
    vad_aggressiveness: int = Field(default=2, ge=0, le=3)

    @field_validator('noise_reduction_method')
    @classmethod
    def validate_method(cls, v: str) -> str:
        valid_methods = ['spectral_gating', 'wiener', 'simple_gate']
        if v.lower() not in valid_methods:
            raise ValueError(f'Noise reduction method must be one of: {valid_methods}')
        return v.lower()


class STTConfig(BaseModel):
    """Speech-to-Text configuration"""
    primary_mode: str = Field(default="hybrid")
    local_model: str = "whisper-base"
    api_provider: str = "openai"
    language: str = "en"
    fallback_timeout_ms: int = Field(default=2000, ge=500, le=5000)
    confidence_threshold: float = Field(default=0.4, ge=0.0, le=1.0)
    clarification_prompt: str = "I didn't catch that clearly. Could you repeat?"

    @field_validator('primary_mode')
    @classmethod
    def validate_mode(cls, v: str) -> str:
        valid_modes = ['local', 'api', 'hybrid']
        if v.lower() not in valid_modes:
            raise ValueError(f'STT mode must be one of: {valid_modes}')
        return v.lower()


class LLMConfig(BaseModel):
    """Language Model configuration"""
    primary_mode: str = Field(default="hybrid")
    api_provider: str = "gemini"
    api_model: str = "gemini-1.5-flash"
    local_provider: str = "ollama"
    local_model: str = "llama2:7b"
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=150, ge=50, le=32000)
    system_prompt: str = """You are an intelligent and professional Voice Assistant, designed to help users control their computer and access information efficiently.

**Your Capabilities & Tools:**

**1. System Control & Desktop Automation:**
- `system_status`: Get CPU, memory, disk, and battery info.
- `get_system_info`: Detailed system information.
- `volume_control`: Set level, mute/unmute system volume.
- `app_volume_control`: Control volume for specific apps.
- `media_control`: Play, pause, next, previous, stop media.
- `brightness_control`: Set screen brightness.
- `power_control`: Shutdown, restart, sleep, lock.
- `window_control`: Minimize, maximize, close, focus windows.
- `minimize_windows`: Minimize all windows to show desktop.
- `list_processes`: List running processes (top CPU).
- `kill_process`: Terminate a process by name or PID.
- `launch_app`: Launch a desktop application.
- `find_file`: Search for files by name.
- `create_folder`: Create a new directory.
- `open_file_location`: Open file explorer at a specific path.
- `file_operation`: Copy, move, or delete files/folders.
- `take_screenshot`: Capture the screen.

**2. Browser Automation:**
- `browser_navigate`: Go to a URL.
- `browser_search`: Google search.
- `browser_click`, `browser_type`: Interact with page elements.
- `fill_form`, `select_dropdown`: Fill forms and select options.
- `handle_popup`: Accept/dismiss alerts.
- `browser_screenshot`: Capture browser viewport or full page.
- `wait_for_navigation`, `switch_to_iframe`, `execute_script`: Advanced control.
- `get_cookies`, `set_cookies`: Manage session cookies.
- `open_gmail`, `open_google_drive`: Quick shortcuts.

**3. Communication (Slack, Discord, Email):**
- **Slack:** `send_slack_message`, `list_slack_channels`, `search_slack_messages`, `get_slack_thread`, `post_slack_file`.
- **Discord:** `send_discord_message`, `list_discord_servers`, `post_discord_embed`, `post_discord_file`, `send_discord_thread_message`.
- **Gmail:** `list_emails`, `read_email`, `search_emails`, `send_email`.

**4. Productivity (Notion, Trello, Drive, Timer):**
- **Notion:** `create_notion_page`, `update_notion_page`, `query_notion_database`, `search_notion`, `retrieve_notion_page`.
- **Trello:** `create_trello_card`, `list_trello_boards`, `move_trello_card`, `add_trello_comment`, `search_trello`.
- **Google Drive:** `list_drive_files`, `search_drive_files`, `download_drive_file`, `upload_drive_file`.
- `set_timer`: Set a countdown timer.

**5. Information & User Data:**
- `web_search`: General web search.
- `get_weather`: Weather forecast.
- `search_conversation_history`: Search past chats.
- `get_recent_conversations`: Review recent sessions.

**Operational Standards (Context7 Compliance):**
1.  **Grounded Truth:** specific tools are your source of truth. Always prioritize tool outputs over internal knowledge for dynamic information (time, weather, news, user data).
2.  **Precise Action:** specific tools are precise. Choose the most specific tool for the task. For example, use `open_gmail` for emails rather than generic browser navigation if possible.
3.  **Spoken Output Optimization:**
    - Keep responses concise (under 40 words) for simple queries.
    - Use natural, conversational language suitable for Text-to-Speech.
    - Avoid reading out raw identifiers (IDs, file paths) unless necessary; use human-readable names.
4.  **Error Handling:** If a tool fails, explain *why* simply and suggest the next step.

**Interaction Protocol:**
- If a user asks a question, answer it directly using available information.
- If a user commands an action, execute it using the relevant tool and confirm completion briefly.
- If you lack the necessary tool or permission, politely decline and explain the limitation."""

    @field_validator('primary_mode')
    @classmethod
    def validate_mode(cls, v: str) -> str:
        valid_modes = ['local', 'api', 'hybrid']
        if v.lower() not in valid_modes:
            raise ValueError(f'LLM mode must be one of: {valid_modes}')
        return v.lower()


class TTSConfig(BaseModel):
    """Text-to-Speech configuration"""
    primary_mode: str = Field(default="hybrid")
    api_provider: str = "elevenlabs"
    local_provider: str = "piper"
    voice: str = "default"
    speed: float = Field(default=1.0, ge=0.5, le=2.0)
    quality: str = "medium"

    @field_validator('primary_mode')
    @classmethod
    def validate_mode(cls, v: str) -> str:
        valid_modes = ['local', 'api', 'hybrid']
        if v.lower() not in valid_modes:
            raise ValueError(f'TTS mode must be one of: {valid_modes}')
        return v.lower()

    @field_validator('quality')
    @classmethod
    def validate_quality(cls, v: str) -> str:
        valid_qualities = ['low', 'medium', 'high']
        if v.lower() not in valid_qualities:
            raise ValueError(f'TTS quality must be one of: {valid_qualities}')
        return v.lower()


class IntentConfig(BaseModel):
    """Intent classification configuration"""
    confidence_threshold: float = Field(default=0.4, ge=0.0, le=1.0)
    types: list[str] = Field(default_factory=lambda: ["INFORMATIONAL", "TASK_BASED", "CONVERSATIONAL"])
    entity_extraction: bool = True


class PerformanceConfig(BaseModel):
    """Performance targets for monitoring"""
    wake_word_activation_ms: int = 1000
    query_processing_ms: int = 2000
    end_to_end_ms: int = 3000


class AssistantConfig(BaseModel):
    """Main assistant configuration"""
    name: str = "Assistant"
    wake_word: str = "Hey Assistant"
    version: str = "1.0.0-baseline"


class Config:
    """
    Central configuration manager
    Loads configuration from .env and YAML files
    """

    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self._load_environment()
        self._load_yaml_config()
        self._validate_config()

    def _load_environment(self) -> None:
        """Load environment variables from .env file"""
        env_path = self.config_dir / ".env"
        if env_path.exists():
            load_dotenv(env_path)

    def _load_yaml_config(self) -> None:
        """Load configuration from YAML file"""
        yaml_path = self.config_dir / "assistant_config.yaml"
        if yaml_path.exists():
            with open(yaml_path, 'r') as f:
                self._yaml_config = yaml.safe_load(f)
        else:
            self._yaml_config = {}

    def _validate_config(self) -> None:
        """Validate and initialize configuration objects"""
        # Initialize configuration objects
        self.assistant = AssistantConfig(**self._yaml_config.get('assistant', {}))
        self.audio = AudioConfig(**self._yaml_config.get('audio', {}))
        self.audio_preprocessor = AudioPreprocessorConfig(**self._yaml_config.get('audio_preprocessor', {}))
        self.context = ContextConfig(**self._yaml_config.get('context', {}))
        self.network = NetworkConfig(**self._yaml_config.get('network', {}))
        self.actions = ActionsConfig(**self._yaml_config.get('actions', {}))
        self.logging = LoggingConfig(**self._yaml_config.get('logging', {}))
        self.wake_word = WakeWordConfig(**self._yaml_config.get('wake_word', {}))
        self.stt = STTConfig(**self._yaml_config.get('stt', {}))
        self.llm = LLMConfig(**self._yaml_config.get('llm', {}))
        self.tts = TTSConfig(**self._yaml_config.get('tts', {}))
        self.intent = IntentConfig(**self._yaml_config.get('intent', {}))
        self.performance = PerformanceConfig(**self._yaml_config.get('performance', {}))

        # Override with environment variables
        self._apply_env_overrides()

    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides"""
        # API Keys
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        self.elevenlabs_api_key = os.getenv('ELEVENLABS_API_KEY')
        self.mem0_api_key = os.getenv('MEM0_API_KEY')

        # Service modes
        if os.getenv('STT_MODE'):
            self.stt.primary_mode = os.getenv('STT_MODE')
        if os.getenv('LLM_MODE'):
            self.llm.primary_mode = os.getenv('LLM_MODE')
        if os.getenv('TTS_MODE'):
            self.tts.primary_mode = os.getenv('TTS_MODE')

        # Privacy settings
        if os.getenv('ENABLE_CONVERSATION_PERSISTENCE'):
            self.context.enable_persistence = os.getenv('ENABLE_CONVERSATION_PERSISTENCE').lower() == 'true'

        # Performance tuning
        if os.getenv('WAKE_WORD_SENSITIVITY'):
            self.wake_word.sensitivity = float(os.getenv('WAKE_WORD_SENSITIVITY'))
        if os.getenv('STT_MODEL'):
            self.stt.local_model = os.getenv('STT_MODEL')
        if os.getenv('LLM_MODEL'):
            self.llm.api_model = os.getenv('LLM_MODEL')
        if os.getenv('OLLAMA_MODEL'):
            self.llm.local_model = os.getenv('OLLAMA_MODEL')

        # Logging
        if os.getenv('LOG_LEVEL'):
            self.logging.level = os.getenv('LOG_LEVEL')
        if os.getenv('LOG_DIR'):
            self.log_dir = Path(os.getenv('LOG_DIR'))
        else:
            self.log_dir = Path('logs')

        # Storage
        self.data_dir = Path(os.getenv('DATA_DIR', 'data'))
        self.conversation_encryption_key = os.getenv('CONVERSATION_ENCRYPTION_KEY')

        # Playwright
        self.playwright_enabled = os.getenv('PLAYWRIGHT_ENABLED', 'true').lower() == 'true'

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dotted key path"""
        keys = key.split('.')
        value = self._yaml_config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default

        return value if value is not None else default

    def to_dict(self) -> Dict[str, Any]:
        """Export configuration as dictionary"""
        return {
            'assistant': self.assistant.model_dump(),
            'audio': self.audio.model_dump(),
            'audio_preprocessor': self.audio_preprocessor.model_dump(),
            'context': self.context.model_dump(),
            'network': self.network.model_dump(),
            'actions': self.actions.model_dump(),
            'logging': self.logging.model_dump(),
            'wake_word': self.wake_word.model_dump(),
            'stt': self.stt.model_dump(),
            'llm': self.llm.model_dump(),
            'tts': self.tts.model_dump(),
            'intent': self.intent.model_dump(),
            'performance': self.performance.model_dump(),
        }


# Global configuration instance
_config: Optional[Config] = None


def get_config(config_dir: str = "config") -> Config:
    """Get or create global configuration instance"""
    global _config
    if _config is None:
        _config = Config(config_dir)
    return _config


def reload_config(config_dir: str = "config") -> Config:
    """Reload configuration from files"""
    global _config
    _config = Config(config_dir)
    return _config
