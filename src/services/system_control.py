"""
System Control Service
Provides cross-platform laptop/system automation capabilities.
Handles file operations, window management, screenshots, and system queries.
"""

import os
import platform
import subprocess
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
import base64

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
