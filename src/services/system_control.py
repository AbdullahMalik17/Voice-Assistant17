"""
System Control Service
Provides cross-platform laptop/system automation capabilities.
Handles file operations, window management, screenshots, and system queries.
"""

import os
import platform
import subprocess
import logging
import shutil
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import base64

try:
    from fuzzywuzzy import process
except ImportError:
    process = None

logger = logging.getLogger(__name__)


class SystemControlService:
    """
    Cross-platform system control service.
    Provides file operations, window management, and system automation.
    """

    def __init__(self):
        """Initialize system control service."""
        self.platform = platform.system()  # Windows, Darwin (macOS), Linux
        logger.info(f"SystemControlService initialized for {self.platform}")

    def find_file(
        self,
        filename: str,
        directory: Optional[str] = None,
        max_results: int = 10
    ) -> Dict[str, Any]:
        """
        Find files by name on the system.

        Args:
            filename: Name or pattern to search for
            directory: Directory to search in (defaults to user home)
            max_results: Maximum number of results to return

        Returns:
            Dict with found files
        """
        try:
            if directory is None:
                directory = str(Path.home())

            results = []
            search_path = Path(directory)

            # Search for files
            for path in search_path.rglob(f"*{filename}*"):
                if len(results) >= max_results:
                    break
                results.append({
                    "path": str(path),
                    "name": path.name,
                    "is_file": path.is_file(),
                    "size_bytes": path.stat().st_size if path.is_file() else None
                })

            logger.info(f"Found {len(results)} files matching '{filename}'")

            return {
                "success": True,
                "query": filename,
                "directory": directory,
                "results": results,
                "count": len(results)
            }
        except Exception as e:
            logger.error(f"File search failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "query": filename
            }

    def take_screenshot(
        self,
        filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Take a screenshot of the entire screen.

        Args:
            filename: Optional filename to save (PNG format)

        Returns:
            Dict with screenshot data or path
        """
        try:
            import pyautogui

            # Take screenshot
            screenshot = pyautogui.screenshot()

            if filename:
                # Save to file
                screenshot.save(filename)
                logger.info(f"Screenshot saved to {filename}")

                return {
                    "success": True,
                    "path": filename
                }
            else:
                # Return as base64
                import io
                buffer = io.BytesIO()
                screenshot.save(buffer, format='PNG')
                screenshot_b64 = base64.b64encode(buffer.getvalue()).decode()

                logger.info("Screenshot captured (base64)")

                return {
                    "success": True,
                    "screenshot": screenshot_b64
                }
        except ImportError:
            logger.error("pyautogui not installed")
            return {
                "success": False,
                "error": "pyautogui not installed. Install with: pip install pyautogui"
            }
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_system_info(self) -> Dict[str, Any]:
        """
        Get comprehensive system information.

        Returns:
            Dict with system stats
        """
        try:
            import psutil

            info = {
                "platform": self.platform,
                "platform_version": platform.version(),
                "processor": platform.processor(),
                "cpu_count": psutil.cpu_count(),
                "cpu_percent": psutil.cpu_percent(interval=0.5),
                "memory": {
                    "total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
                    "available_gb": round(psutil.virtual_memory().available / (1024**3), 2),
                    "percent_used": psutil.virtual_memory().percent
                },
                "disk": {
                    "total_gb": round(psutil.disk_usage('/').total / (1024**3), 2),
                    "free_gb": round(psutil.disk_usage('/').free / (1024**3), 2),
                    "percent_used": psutil.disk_usage('/').percent
                }
            }

            # Add battery info if available
            battery = psutil.sensors_battery()
            if battery:
                info["battery"] = {
                    "percent": battery.percent,
                    "charging": battery.power_plugged,
                    "time_left_minutes": battery.secsleft // 60 if battery.secsleft > 0 else None
                }

            logger.info("System info retrieved")

            return {
                "success": True,
                "info": info
            }
        except Exception as e:
            logger.error(f"Get system info failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def open_file_location(self, filepath: str) -> Dict[str, Any]:
        """
        Open the file location in file explorer.

        Args:
            filepath: Path to the file

        Returns:
            Dict with success status
        """
        try:
            path = Path(filepath)

            if not path.exists():
                return {
                    "success": False,
                    "error": f"File not found: {filepath}"
                }

            if self.platform == "Windows":
                # Open in Explorer and select the file
                subprocess.run(["explorer", "/select,", str(path)])
            elif self.platform == "Darwin":  # macOS
                subprocess.run(["open", "-R", str(path)])
            else:  # Linux
                # Open parent directory
                subprocess.run(["xdg-open", str(path.parent)])

            logger.info(f"Opened file location: {filepath}")

            return {
                "success": True,
                "path": filepath
            }
        except Exception as e:
            logger.error(f"Open file location failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def minimize_all_windows(self) -> Dict[str, Any]:
        """
        Minimize all windows (show desktop).

        Returns:
            Dict with success status
        """
        try:
            if self.platform == "Windows":
                # Windows: Win+D
                import pyautogui
                pyautogui.hotkey('win', 'd')
            elif self.platform == "Darwin":  # macOS
                # macOS: F11 or Command+F3
                import pyautogui
                pyautogui.hotkey('command', 'f3')
            else:  # Linux
                # Linux: Ctrl+Alt+D (may vary by DE)
                import pyautogui
                pyautogui.hotkey('ctrl', 'alt', 'd')

            logger.info("Minimized all windows")

            return {
                "success": True,
                "message": "All windows minimized"
            }
        except Exception as e:
            logger.error(f"Minimize windows failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_active_window_title(self) -> Dict[str, Any]:
        """
        Get the title of the currently active window.

        Returns:
            Dict with window title
        """
        try:
            if self.platform == "Windows":
                import win32gui
                window = win32gui.GetForegroundWindow()
                title = win32gui.GetWindowText(window)
            else:
                # For macOS/Linux, use simpler approach
                title = "Active window detection not implemented for this platform"

            logger.info(f"Active window: {title}")

            return {
                "success": True,
                "title": title
            }
        except ImportError:
            logger.error("pywin32 not installed")
            return {
                "success": False,
                "error": "pywin32 not installed for Windows. Install with: pip install pywin32"
            }
        except Exception as e:
            logger.error(f"Get active window failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def list_running_processes(self, limit: int = 10) -> Dict[str, Any]:
        """
        List running processes sorted by CPU or memory usage.

        Args:
            limit: Number of processes to return

        Returns:
            Dict with process list
        """
        try:
            import psutil

            processes = []

            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    processes.append({
                        "pid": proc.info['pid'],
                        "name": proc.info['name'],
                        "cpu_percent": proc.info['cpu_percent'],
                        "memory_percent": round(proc.info['memory_percent'], 2)
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            # Sort by CPU usage
            processes.sort(key=lambda x: x['cpu_percent'] or 0, reverse=True)
            top_processes = processes[:limit]

            logger.info(f"Listed top {limit} processes")

            return {
                "success": True,
                "processes": top_processes,
                "count": len(top_processes)
            }
        except Exception as e:
            logger.error(f"List processes failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def create_folder(self, path: str) -> Dict[str, Any]:
        """
        Create a new folder.

        Args:
            path: Path for the new folder

        Returns:
            Dict with success status
        """
        try:
            folder_path = Path(path)
            folder_path.mkdir(parents=True, exist_ok=True)

            logger.info(f"Created folder: {path}")

            return {
                "success": True,
                "path": path
            }
        except Exception as e:
            logger.error(f"Create folder failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_clipboard_content(self) -> Dict[str, Any]:
        """
        Get text content from clipboard.

        Returns:
            Dict with clipboard content
        """
        try:
            import pyautogui
            content = pyautogui.paste()

            logger.info("Retrieved clipboard content")

            return {
                "success": True,
                "content": content
            }
        except Exception as e:
            logger.error(f"Get clipboard failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def set_clipboard_content(self, text: str) -> Dict[str, Any]:
        """
        Set text content to clipboard.

        Args:
            text: Text to copy to clipboard

        Returns:
            Dict with success status
        """
        try:
            import pyautogui
            pyautogui.copy(text)

            logger.info("Set clipboard content")

            return {
                "success": True,
                "message": "Text copied to clipboard"
            }
        except Exception as e:
            logger.error(f"Set clipboard failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def launch_app(self, app_name: str) -> Dict[str, Any]:
        """
        Launch an application by name.
        Uses fuzzy matching to find the best match.
        """
        try:
            if not process:
                return {"success": False, "error": "fuzzywuzzy not installed"}

            # 1. Simple direct execution check (e.g. "notepad")
            if shutil.which(app_name):
                subprocess.Popen(app_name, shell=True)
                return {"success": True, "message": f"Launched {app_name}"}

            # 2. Search in Start Menu (Windows)
            if self.platform == "Windows":
                app_path = self._find_windows_app(app_name)
                if app_path:
                    os.startfile(app_path)
                    return {"success": True, "message": f"Launched {Path(app_path).stem}", "path": app_path}
            
            # 3. macOS/Linux implementation (simplified)
            elif self.platform == "Darwin":
                subprocess.run(["open", "-a", app_name])
                return {"success": True, "message": f"Launched {app_name}"}
            elif self.platform == "Linux":
                 subprocess.Popen(app_name.split(), shell=True) # Basic linux fallback
                 return {"success": True, "message": f"Launched {app_name}"}

            return {"success": False, "error": f"Application '{app_name}' not found"}
        except Exception as e:
            logger.error(f"Launch app failed: {e}")
            return {"success": False, "error": str(e)}

    def _find_windows_app(self, app_name: str) -> Optional[str]:
        """Find Windows app path using fuzzy matching."""
        try:
            # Common start menu paths
            paths = [
                os.path.join(os.environ.get("ProgramData", "C:\\ProgramData"), "Microsoft", "Windows", "Start Menu", "Programs"),
                os.path.join(os.environ.get("APPDATA", "C:\\Users\\Default\\AppData\\Roaming"), "Microsoft", "Windows", "Start Menu", "Programs")
            ]
            
            apps = {}
            for path in paths:
                if not os.path.exists(path):
                    continue
                for root, dirs, files in os.walk(path):
                    for file in files:
                        if file.endswith(".lnk"):
                            name = file[:-4].lower()
                            full_path = os.path.join(root, file)
                            apps[name] = full_path
            
            # Fuzzy match
            if not apps:
                return None

            match = process.extractOne(app_name.lower(), list(apps.keys()))
            if match and match[1] > 70: # Threshold
                return apps[match[0]]
            return None
        except Exception as e:
            logger.error(f"App search error: {e}")
            return None

    def perform_file_operation(self, operation: str, source: str, destination: Optional[str] = None) -> Dict[str, Any]:
        """
        Perform file operations (copy, move, delete).
        """
        try:
            src_path = Path(source)
            if not src_path.exists():
                return {"success": False, "error": f"Source not found: {source}"}

            if operation == "delete":
                if src_path.is_dir():
                    shutil.rmtree(src_path)
                else:
                    src_path.unlink()
                return {"success": True, "message": f"Deleted {source}"}

            if not destination:
                return {"success": False, "error": "Destination required for copy/move"}

            dest_path = Path(destination)
            # Ensure parent exists
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            if operation == "copy":
                if src_path.is_dir():
                    shutil.copytree(src_path, dest_path, dirs_exist_ok=True)
                else:
                    shutil.copy2(src_path, dest_path)
                return {"success": True, "message": f"Copied {source} to {destination}"}

            elif operation == "move":
                shutil.move(str(src_path), str(dest_path))
                return {"success": True, "message": f"Moved {source} to {destination}"}

            return {"success": False, "error": f"Unknown operation: {operation}"}
        except Exception as e:
            logger.error(f"File operation failed: {e}")
            return {"success": False, "error": str(e)}

    def control_app_volume(self, app_name: str, level: int) -> Dict[str, Any]:
        """Control volume for a specific application (Windows only)."""
        if self.platform != "Windows":
             return {"success": False, "error": "App volume control only supported on Windows"}
        
        try:
            # Lazy import
            from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume
            
            sessions = AudioUtilities.GetAllSessions()
            target_found = False
            
            for session in sessions:
                volume = session._ctl.QueryInterface(ISimpleAudioVolume)
                if session.Process and session.Process.name():
                    proc_name = session.Process.name().lower()
                    # Fuzzy match process name
                    if app_name.lower() in proc_name:
                         volume.SetMasterVolume(level / 100.0, None)
                         target_found = True
                    elif process:
                         match = process.extractOne(app_name.lower(), [proc_name])
                         if match and match[1] > 80:
                             volume.SetMasterVolume(level / 100.0, None)
                             target_found = True
            
            if target_found:
                 return {"success": True, "message": f"Set volume for {app_name} to {level}%"}
            else:
                 return {"success": False, "error": f"Application {app_name} not found in audio mixer (it must be playing audio)"}
                 
        except Exception as e:
            logger.error(f"App volume control failed: {e}")
            return {"success": False, "error": str(e)}

    def control_window(self, action: str, title_pattern: str = None) -> Dict[str, Any]:
        """
        Control application windows (minimize, maximize, close, focus).
        """
        if self.platform != "Windows":
             return {"success": False, "error": "Window control only supported on Windows currently"}

        try:
            import pygetwindow as gw
            
            target_window = None
            if title_pattern:
                # Find window
                windows = gw.getWindowsWithTitle(title_pattern)
                if not windows:
                     return {"success": False, "error": f"Window '{title_pattern}' not found"}
                target_window = windows[0]
            else:
                target_window = gw.getActiveWindow()
                
            if not target_window:
                 return {"success": False, "error": "No target window found"}

            if action == "minimize":
                target_window.minimize()
            elif action == "maximize":
                target_window.maximize()
            elif action == "restore":
                target_window.restore()
            elif action == "close":
                target_window.close()
            elif action == "focus":
                target_window.activate()
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
                
            return {"success": True, "message": f"Performed {action} on {target_window.title}"}

        except Exception as e:
            logger.error(f"Window control failed: {e}")
            return {"success": False, "error": str(e)}

    def kill_process(self, name_or_pid: str) -> Dict[str, Any]:
        """Kill a process by name or PID."""
        try:
            import psutil
            killed_count = 0
            
            # Check if PID
            if name_or_pid.isdigit():
                pid = int(name_or_pid)
                if psutil.pid_exists(pid):
                    psutil.Process(pid).terminate()
                    return {"success": True, "message": f"Terminated process PID {pid}"}
            
            # Kill by name (fuzzy or exact)
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'] and name_or_pid.lower() in proc.info['name'].lower():
                    proc.terminate()
                    killed_count += 1
            
            if killed_count > 0:
                return {"success": True, "message": f"Terminated {killed_count} processes matching '{name_or_pid}'"}
            else:
                return {"success": False, "error": f"No process found matching '{name_or_pid}'"}
                
        except Exception as e:
            logger.error(f"Kill process failed: {e}")
            return {"success": False, "error": str(e)}


# Singleton instance
_system_control: Optional[SystemControlService] = None


def get_system_control() -> SystemControlService:
    """
    Get or create system control service instance.

    Returns:
        SystemControlService instance
    """
    global _system_control

    if _system_control is None:
        _system_control = SystemControlService()

    return _system_control
