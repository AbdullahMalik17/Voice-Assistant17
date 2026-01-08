"""
Desktop Automation Tools
Tools for controlling system volume, brightness, media, and power.
"""

import os
import platform
import subprocess
from typing import Optional, List, Any

from .tools import Tool, ToolResult, ToolCategory, ToolParameter


class PowerShellTool(Tool):
    """Base class for PowerShell-based tools"""
    
    def _run_powershell(self, command: str) -> ToolResult:
        """Execute a PowerShell command"""
        if platform.system() != "Windows":
            return ToolResult(
                success=False,
                error="This tool is only available on Windows"
            )

        try:
            # Use PowerShell to execute
            full_command = f"powershell -Command \"{command}\""
            process = subprocess.Popen(
                full_command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate()

            if process.returncode == 0:
                return ToolResult(
                    success=True,
                    data={"output": stdout.decode('utf-8').strip()}
                )
            else:
                return ToolResult(
                    success=False,
                    error=f"PowerShell error: {stderr.decode('utf-8').strip()}"
                )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Execution error: {str(e)}"
            )


class VolumeControlTool(PowerShellTool):
    """Control system volume"""
    name = "volume_control"
    description = "Control system volume (set level, mute, unmute)"
    category = ToolCategory.SYSTEM
    requires_confirmation = False

    def _setup_parameters(self) -> None:
        self._parameters = [
            ToolParameter(
                name="action",
                type="string",
                description="Action to perform",
                required=True,
                enum=["set", "up", "down", "mute", "unmute"]
            ),
            ToolParameter(
                name="level",
                type="number",
                description="Volume level (0-100) for 'set' action",
                required=False
            )
        ]
        self._examples = [
            "Set volume to 50",
            "Mute volume",
            "Turn up the volume"
        ]

    def execute(self, action: str, level: Optional[int] = None, **params) -> ToolResult:
        if action == "mute":
            # 0xAD is VK_VOLUME_MUTE
            script = "$w = New-Object -ComObject WScript.Shell; $w.SendKeys([char]0xAD)"
            return self._run_powershell(script)
            
        elif action == "unmute":
            # Same key toggles
            script = "$w = New-Object -ComObject WScript.Shell; $w.SendKeys([char]0xAD)"
            return self._run_powershell(script)
            
        elif action == "up":
            # 0xAF is VK_VOLUME_UP (press 5 times for noticeable change)
            script = "$w = New-Object -ComObject WScript.Shell; for($i=0;$i-lt 5;$i++){$w.SendKeys([char]0xAF)}"
            return self._run_powershell(script)
            
        elif action == "down":
            # 0xAE is VK_VOLUME_DOWN
            script = "$w = New-Object -ComObject WScript.Shell; for($i=0;$i-lt 5;$i++){$w.SendKeys([char]0xAE)}"
            return self._run_powershell(script)
            
        elif action == "set":
            if level is None:
                return ToolResult(success=False, error="Level required for 'set' action")
            
            # Setting exact volume is hard with just SendKeys. 
            # We can use a trick: Mute then VolUp until target? No, inaccurate.
            # Ideally use AudioDeviceCmdlets or nircmd. 
            # Without deps, we can try a .NET approach via PowerShell.
            
            # This script sets master volume using CoreAudioApi via PowerShell reflection
            # It's complex, so for reliability without deps, let's use a simpler approx
            # or just log a warning that exact setting needs a library.
            
            # Attempt with a sophisticated PS script for exact volume
            ps_script = """
            $obj = New-Object -ComObject WScript.Shell
            # Reset to 0 (Mute then Unmute creates state issues sometimes)
            # Just hit Down 50 times
            for($i=0; $i -lt 50; $i++) { $obj.SendKeys([char]0xAE) }
            # Calculate steps (each step is 2%)
            $steps = [math]::Round(%d / 2)
            for($i=0; $i -lt $steps; $i++) { $obj.SendKeys([char]0xAF) }
            """ % level
            
            return self._run_powershell(ps_script)

        return ToolResult(success=False, error=f"Unknown action: {action}")


class MediaControlTool(PowerShellTool):
    """Control media playback"""
    name = "media_control"
    description = "Control media playback (play, pause, next, previous)"
    category = ToolCategory.SYSTEM
    requires_confirmation = False

    def _setup_parameters(self) -> None:
        self._parameters = [
            ToolParameter(
                name="action",
                type="string",
                description="Media action",
                required=True,
                enum=["play_pause", "next", "previous", "stop"]
            )
        ]
        self._examples = [
            "Pause music",
            "Next song",
            "Stop playback"
        ]

    def execute(self, action: str, **params) -> ToolResult:
        key_code = ""
        if action == "play_pause":
            key_code = "0xB3" # VK_MEDIA_PLAY_PAUSE
        elif action == "next":
            key_code = "0xB0" # VK_MEDIA_NEXT_TRACK
        elif action == "previous":
            key_code = "0xB1" # VK_MEDIA_PREV_TRACK
        elif action == "stop":
            key_code = "0xB2" # VK_MEDIA_STOP
        else:
            return ToolResult(success=False, error=f"Unknown action: {action}")
            
        script = f"$w = New-Object -ComObject WScript.Shell; $w.SendKeys([char]{key_code})"
        return self._run_powershell(script)


class BrightnessControlTool(PowerShellTool):
    """Control screen brightness"""
    name = "brightness_control"
    description = "Control screen brightness (set level)"
    category = ToolCategory.SYSTEM
    requires_confirmation = False

    def _setup_parameters(self) -> None:
        self._parameters = [
            ToolParameter(
                name="level",
                type="number",
                description="Brightness level (0-100)",
                required=True
            )
        ]
        self._examples = [
            "Set brightness to 70",
            "Dim the screen to 20"
        ]

    def execute(self, level: int, **params) -> ToolResult:
        # WmiMonitorBrightnessMethods
        script = f"""
        (Get-WmiObject -Namespace root/wmi -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, {level})
        """
        return self._run_powershell(script)


class PowerControlTool(PowerShellTool):
    """Control system power"""
    name = "power_control"
    description = "Shutdown, restart, or sleep the computer"
    category = ToolCategory.SYSTEM
    requires_confirmation = True  # Critical!

    def _setup_parameters(self) -> None:
        self._parameters = [
            ToolParameter(
                name="action",
                type="string",
                description="Power action",
                required=True,
                enum=["shutdown", "restart", "sleep", "lock"]
            )
        ]
        self._examples = [
            "Shutdown the computer",
            "Restart now",
            "Lock the screen"
        ]

    def execute(self, action: str, **params) -> ToolResult:
        if action == "shutdown":
            return self._run_powershell("Stop-Computer -Force")
        elif action == "restart":
            return self._run_powershell("Restart-Computer -Force")
        elif action == "sleep":
            return self._run_powershell("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
        elif action == "lock":
            return self._run_powershell("rundll32.exe user32.dll,LockWorkStation")
            
        return ToolResult(success=False, error=f"Unknown action: {action}")
