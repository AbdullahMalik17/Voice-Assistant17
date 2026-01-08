"""
Action Executor Service
Executes system commands and launches applications based on voice intents
"""

import platform
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

import psutil

from ..core.config import Config
from ..models.action_script import ActionScript, ActionCategory, Platform
from ..models.system_status import get_system_status, SystemStatus
from ..models.intent import Intent, IntentType, ActionType
from ..utils.logger import EventLogger, MetricsLogger
from ..agents.desktop_tools import VolumeControlTool, MediaControlTool, BrightnessControlTool, PowerControlTool


class ActionExecutor:
    """
    Executes task-based actions including:
    - Application launching
    - System status queries
    - Custom script execution
    """

    def __init__(
        self,
        config: Config,
        logger: EventLogger,
        metrics_logger: MetricsLogger
    ):
        self.config = config
        self.logger = logger
        self.metrics_logger = metrics_logger

        # Detect current platform
        self.current_platform = self._detect_platform()

        # Load action registry
        self.action_registry: Dict[str, ActionScript] = {}
        self._load_default_actions()

        self.logger.info(
            event='ACTION_EXECUTOR_INITIALIZED',
            message=f'Action executor initialized on {self.current_platform}',
            platform=self.current_platform,
            actions_loaded=len(self.action_registry)
        )

    def _detect_platform(self) -> Platform:
        """Detect current operating system"""
        system = platform.system().lower()

        if system == 'windows':
            return Platform.WINDOWS
        elif system == 'darwin':
            return Platform.MACOS
        elif system == 'linux':
            return Platform.LINUX
        else:
            self.logger.warning(
                event='UNKNOWN_PLATFORM',
                message=f'Unknown platform: {system}, using ALL as fallback'
            )
            return Platform.ALL

    def _load_default_actions(self) -> None:
        """Load default action scripts for common tasks"""
        # Application launchers (platform-specific)
        if self.current_platform == Platform.WINDOWS:
            self._register_action(ActionScript(
                name="open_spotify",
                command_template="start spotify:",
                platform=Platform.WINDOWS,
                timeout_seconds=10,
                category=ActionCategory.APPLICATION,
                description="Launch Spotify"
            ))

            self._register_action(ActionScript(
                name="open_notepad",
                command_template="notepad.exe",
                platform=Platform.WINDOWS,
                timeout_seconds=5,
                category=ActionCategory.APPLICATION,
                description="Launch Notepad"
            ))

            self._register_action(ActionScript(
                name="open_browser",
                command_template="start microsoft-edge:",
                platform=Platform.WINDOWS,
                timeout_seconds=10,
                category=ActionCategory.APPLICATION,
                description="Launch Microsoft Edge browser"
            ))

        elif self.current_platform == Platform.MACOS:
            self._register_action(ActionScript(
                name="open_spotify",
                command_template="open -a Spotify",
                platform=Platform.MACOS,
                timeout_seconds=10,
                category=ActionCategory.APPLICATION,
                description="Launch Spotify"
            ))

            self._register_action(ActionScript(
                name="open_browser",
                command_template="open -a Safari",
                platform=Platform.MACOS,
                timeout_seconds=10,
                category=ActionCategory.APPLICATION,
                description="Launch Safari browser"
            ))

        elif self.current_platform == Platform.LINUX:
            self._register_action(ActionScript(
                name="open_spotify",
                command_template="spotify",
                platform=Platform.LINUX,
                timeout_seconds=10,
                category=ActionCategory.APPLICATION,
                description="Launch Spotify"
            ))

            self._register_action(ActionScript(
                name="open_browser",
                command_template="firefox",
                platform=Platform.LINUX,
                timeout_seconds=10,
                category=ActionCategory.APPLICATION,
                description="Launch Firefox browser"
            ))

    def _register_action(self, action: ActionScript) -> None:
        """Register an action script"""
        self.action_registry[action.name] = action

    def execute_action(self, intent: Intent) -> str:
        """
        Execute action based on intent
        Returns: Human-readable result message
        """
        start_time = time.time()

        try:
            # Route based on action type
            if intent.action_type == ActionType.SYSTEM_STATUS:
                result = self._execute_system_status(intent)

            elif intent.action_type == ActionType.LAUNCH_APP:
                result = self._execute_launch_app(intent)

            elif intent.action_type == ActionType.SYSTEM_CONTROL:
                result = self._execute_system_control(intent)

            elif intent.action_type == ActionType.FILE_OPERATION:
                result = "File operations are not yet implemented."

            elif intent.action_type == ActionType.BROWSER_AUTOMATION:
                result = "Browser automation is not yet implemented."

            else:
                result = "Unknown action type."

            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)

            # Log success
            self.logger.info(
                event='ACTION_EXECUTED',
                message=f'Action executed successfully: {intent.action_type.value}',
                action_type=intent.action_type.value,
                duration_ms=duration_ms,
                result=result[:100]
            )

            # Record metrics
            self.metrics_logger.record_metric('action_execution_latency_ms', duration_ms)
            self.metrics_logger.record_metric('action_executions', 1)

            return result

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)

            self.logger.error(
                event='ACTION_EXECUTION_FAILED',
                message=f'Action execution failed: {str(e)}',
                action_type=intent.action_type.value if intent.action_type else 'UNKNOWN',
                error=str(e),
                duration_ms=duration_ms
            )

            # Record metrics
            self.metrics_logger.record_metric('action_failures', 1)

            return f"I encountered an error: {str(e)}"

    def _execute_system_status(self, intent: Intent) -> str:
        """Execute system status query"""
        # Get status type from entities
        status_type = intent.entities.get('status_type', 'all')

        # Capture system status
        status = get_system_status(network_connected=True)

        # Format response based on requested type
        if status_type in ['cpu', 'processor']:
            response = f"CPU usage is at {status.cpu_percent:.1f}%"
            if status.cpu_temp_celsius:
                response += f" and temperature is {status.cpu_temp_celsius:.1f} degrees Celsius"

        elif status_type in ['memory', 'ram']:
            response = f"Memory usage is at {status.memory_percent:.1f}%, with {status.memory_available_mb} megabytes available"

        elif status_type in ['disk', 'storage']:
            response = f"Disk usage is at {status.disk_percent:.1f}%, with {status.disk_available_gb:.1f} gigabytes available"

        elif status_type == 'battery':
            # Check battery status
            try:
                battery = psutil.sensors_battery()
                if battery:
                    response = f"Battery is at {battery.percent:.0f}%"
                    if battery.power_plugged:
                        response += ", charging"
                    else:
                        response += f", about {battery.secsleft // 60} minutes remaining"
                else:
                    response = "No battery detected on this system"
            except AttributeError:
                response = "Battery information is not available on this system"

        elif status_type == 'temperature':
            if status.cpu_temp_celsius:
                response = f"CPU temperature is {status.cpu_temp_celsius:.1f} degrees Celsius"
            else:
                response = "Temperature sensors are not available on this system"

        else:
            # Return full status
            response = f"System status: {status.to_human_readable()}"

        return response

    def _execute_launch_app(self, intent: Intent) -> str:
        """Execute application launch"""
        # Get app name from entities
        app_name = intent.entities.get('app_name', '').lower()

        if not app_name:
            return "I couldn't determine which application to open. Please specify an app name."

        # Map common app names to action scripts
        app_mapping = {
            'spotify': 'open_spotify',
            'notepad': 'open_notepad',
            'browser': 'open_browser',
            'edge': 'open_browser',
            'safari': 'open_browser',
            'firefox': 'open_browser',
        }

        action_name = app_mapping.get(app_name)

        if not action_name or action_name not in self.action_registry:
            return f"I don't know how to open {app_name}. Available apps: {', '.join(app_mapping.keys())}"

        action = self.action_registry[action_name]

        # Execute the command
        try:
            command = action.format_command({})

            self.logger.info(
                event='EXECUTING_COMMAND',
                message=f'Executing command: {command}',
                action_name=action_name,
                app_name=app_name
            )

            # Execute command
            if self.current_platform == Platform.WINDOWS:
                # Use shell=True for Windows to handle "start" command
                process = subprocess.Popen(
                    command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            else:
                # For Unix-like systems, split command
                process = subprocess.Popen(
                    command.split(),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )

            # Don't wait for GUI apps to complete
            # Just check if they started
            time.sleep(0.5)

            if process.poll() is None or process.returncode == 0:
                return f"Opening {app_name}"
            else:
                _, stderr = process.communicate(timeout=1)
                error_msg = stderr.decode('utf-8', errors='ignore').strip()
                return f"Failed to open {app_name}: {error_msg}"

        except subprocess.TimeoutExpired:
            # Process is still running (expected for GUI apps)
            return f"Opening {app_name}"

        except FileNotFoundError:
            return f"{app_name} is not installed on this system"

        except Exception as e:
            self.logger.error(
                event='APP_LAUNCH_FAILED',
                message=f'Failed to launch {app_name}: {str(e)}',
                error=str(e)
            )
            return f"Failed to open {app_name}: {str(e)}"

    def _execute_system_control(self, intent: Intent) -> str:
        """Execute system control actions (volume, brightness, etc.)"""
        control_type = intent.entities.get('control_type')
        action = intent.entities.get('action')
        
        if not control_type:
            return f"I'm not sure what system control to perform. Target: {intent.entities.get('target', 'unknown')}"

        result = None
        
        if control_type == 'volume':
            tool = VolumeControlTool()
            level = intent.entities.get('level')
            if not action: action = 'set' if level is not None else 'up'
            result = tool.execute(action=action, level=level)
            
        elif control_type == 'media':
            tool = MediaControlTool()
            if not action: action = 'play_pause'
            result = tool.execute(action=action)
            
        elif control_type == 'brightness':
            tool = BrightnessControlTool()
            level = intent.entities.get('level', 50)
            result = tool.execute(level=level)
            
        elif control_type == 'power':
            tool = PowerControlTool()
            if not action: return "Please specify power action (shutdown, restart, sleep)"
            result = tool.execute(action=action)
            
        else:
            return f"Unsupported control type: {control_type}"

        if result and result.success:
            return f"Executed {control_type} control: {action or 'default'}"
        else:
            return f"Failed to execute control: {result.error if result else 'Unknown error'}"

    def test_service(self) -> bool:
        """Test action executor with system status query"""
        try:
            # Test system status
            status = get_system_status()

            self.logger.info(
                event='ACTION_EXECUTOR_TEST_COMPLETED',
                message='Action executor test completed',
                cpu_percent=status.cpu_percent,
                memory_percent=status.memory_percent
            )

            return True

        except Exception as e:
            self.logger.error(
                event='ACTION_EXECUTOR_TEST_FAILED',
                message=f'Action executor test failed: {str(e)}',
                error=str(e)
            )
            return False


def create_action_executor(
    config: Config,
    logger: EventLogger,
    metrics_logger: MetricsLogger
) -> ActionExecutor:
    """Factory function to create action executor"""
    executor = ActionExecutor(
        config=config,
        logger=logger,
        metrics_logger=metrics_logger
    )
    return executor
