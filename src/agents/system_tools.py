"""
System Control Tools
Provides tool definitions for laptop/system automation.
"""

from typing import Any

from .tools import Tool, ToolCategory, ToolParameter, ToolResult
from ..services.system_control import get_system_control


class FindFileTool(Tool):
    """Find files on the system"""
    name = "find_file"
    description = "Search for files by name on the system"
    category = ToolCategory.SYSTEM
    requires_confirmation = False

    def _setup_parameters(self) -> None:
        self._parameters = [
            ToolParameter(
                name="filename",
                type="string",
                description="Name or pattern to search for",
                required=True
            ),
            ToolParameter(
                name="directory",
                type="string",
                description="Directory to search in (defaults to user home)",
                required=False
            )
        ]
        self._examples = [
            "Find file named report.pdf",
            "Search for presentation",
            "Locate document.docx"
        ]

    def execute(self, filename: str, directory: str = None, **params) -> ToolResult:
        """Execute file search"""
        try:
            system = get_system_control()
            result = system.find_file(filename, directory)

            if result["success"]:
                return ToolResult(
                    success=True,
                    data={
                        "message": f"Found {result['count']} files matching '{filename}'",    
                        "results": result["results"],
                        "count": result["count"]
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    error=result.get("error", "Search failed")
                )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"File search error: {str(e)}"
            )


class TakeScreenshotTool(Tool):
    """Take a screenshot"""
    name = "take_screenshot"
    description = "Capture a screenshot of the screen"
    category = ToolCategory.SYSTEM
    requires_confirmation = False

    def _setup_parameters(self) -> None:
        self._parameters = [
            ToolParameter(
                name="filename",
                type="string",
                description="Optional filename to save screenshot",
                required=False
            )
        ]
        self._examples = [
            "Take a screenshot",
            "Capture the screen",
            "Screenshot this"
        ]

    def execute(self, filename: str = None, **params) -> ToolResult:
        """Take screenshot"""
        try:
            system = get_system_control()
            result = system.take_screenshot(filename)

            if result["success"]:
                return ToolResult(
                    success=True,
                    data={
                        "message": "Screenshot captured",
                        "path": result.get("path"),
                        "screenshot": result.get("screenshot")
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    error=result.get("error", "Screenshot failed")
                )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Screenshot error: {str(e)}"
            )


class GetSystemInfoTool(Tool):
    """Get system information"""
    name = "get_system_info"
    description = "Get detailed system information (CPU, memory, disk, battery)"
    category = ToolCategory.SYSTEM
    requires_confirmation = False

    def _setup_parameters(self) -> None:
        self._parameters = []
        self._examples = [
            "Show system info",
            "Get computer status",
            "Check system resources"
        ]

    def execute(self, **params) -> ToolResult:
        """Get system info"""
        try:
            system = get_system_control()
            result = system.get_system_info()

            if result["success"]:
                return ToolResult(
                    success=True,
                    data=result["info"]
                )
            else:
                return ToolResult(
                    success=False,
                    error=result.get("error", "Failed to get system info")
                )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"System info error: {str(e)}"
            )


class MinimizeWindowsTool(Tool):
    """Minimize all windows"""
    name = "minimize_windows"
    description = "Minimize all open windows (show desktop)"
    category = ToolCategory.SYSTEM
    requires_confirmation = False

    def _setup_parameters(self) -> None:
        self._parameters = []
        self._examples = [
            "Minimize all windows",
            "Show desktop",
            "Clear the screen"
        ]

    def execute(self, **params) -> ToolResult:
        """Minimize all windows"""
        try:
            system = get_system_control()
            result = system.minimize_all_windows()

            if result["success"]:
                return ToolResult(
                    success=True,
                    data={"message": result["message"]}
                )
            else:
                return ToolResult(
                    success=False,
                    error=result.get("error", "Failed to minimize windows")
                )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Minimize error: {str(e)}"
            )


class ListProcessesTool(Tool):
    """List running processes"""
    name = "list_processes"
    description = "List currently running processes sorted by CPU usage"
    category = ToolCategory.SYSTEM
    requires_confirmation = False

    def _setup_parameters(self) -> None:
        self._parameters = [
            ToolParameter(
                name="limit",
                type="number",
                description="Number of processes to return",
                required=False,
                default=10
            )
        ]
        self._examples = [
            "Show running processes",
            "List active programs",
            "What's running on my computer"
        ]

    def execute(self, limit: int = 10, **params) -> ToolResult:
        """List processes"""
        try:
            system = get_system_control()
            result = system.list_running_processes(limit)

            if result["success"]:
                return ToolResult(
                    success=True,
                    data={
                        "message": f"Top {result['count']} processes",
                        "processes": result["processes"],
                        "count": result["count"]
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    error=result.get("error", "Failed to list processes")
                )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"List processes error: {str(e)}"
            )


class CreateFolderTool(Tool):
    """Create a new folder"""
    name = "create_folder"
    description = "Create a new folder at the specified path"
    category = ToolCategory.SYSTEM
    requires_confirmation = True  # Requires confirmation for file system changes

    def _setup_parameters(self) -> None:
        self._parameters = [
            ToolParameter(
                name="path",
                type="string",
                description="Path for the new folder",
                required=True
            )
        ]
        self._examples = [
            "Create folder Documents/MyProject",
            "Make a new folder called Reports",
            "Create directory Downloads/Archive"
        ]

    def execute(self, path: str, **params) -> ToolResult:
        """Create folder"""
        try:
            system = get_system_control()
            result = system.create_folder(path)

            if result["success"]:
                return ToolResult(
                    success=True,
                    data={
                        "message": f"Folder created: {path}",
                        "path": result["path"]
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    error=result.get("error", "Failed to create folder")
                )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Create folder error: {str(e)}"
            )


class OpenFileLocationTool(Tool):
    """Open file location in explorer"""
    name = "open_file_location"
    description = "Open the file location in file explorer/finder"
    category = ToolCategory.SYSTEM
    requires_confirmation = False

    def _setup_parameters(self) -> None:
        self._parameters = [
            ToolParameter(
                name="filepath",
                type="string",
                description="Path to the file",
                required=True
            )
        ]
        self._examples = [
            "Open file location for document.pdf",
            "Show me where this file is",
            "Open folder containing report.docx"
        ]

    def execute(self, filepath: str, **params) -> ToolResult:
        """Open file location"""
        try:
            system = get_system_control()
            result = system.open_file_location(filepath)

            if result["success"]:
                return ToolResult(
                    success=True,
                    data={
                        "message": f"Opened location: {filepath}",
                        "path": result["path"]
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    error=result.get("error", "Failed to open location")
                )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Open location error: {str(e)}"
            )


class LaunchAppTool(Tool):
    """Launch an application"""
    name = "launch_app"
    description = "Launch a desktop application by name"
    category = ToolCategory.SYSTEM
    requires_confirmation = False

    def _setup_parameters(self) -> None:
        self._parameters = [
            ToolParameter(
                name="app_name",
                type="string",
                description="Name of the application to launch",
                required=True
            )
        ]
        self._examples = [
            "Open Chrome",
            "Launch Notepad",
            "Start Spotify"
        ]

    def execute(self, app_name: str, **params) -> ToolResult:
        """Launch app"""
        try:
            system = get_system_control()
            result = system.launch_app(app_name)

            if result["success"]:
                return ToolResult(
                    success=True,
                    data=result
                )
            else:
                return ToolResult(
                    success=False,
                    error=result.get("error", "Failed to launch app")
                )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Launch app error: {str(e)}"
            )


class FileOperationTool(Tool):
    """Perform file operations"""
    name = "file_operation"
    description = "Copy, move, or delete files/folders"
    category = ToolCategory.SYSTEM
    requires_confirmation = True

    def _setup_parameters(self) -> None:
        self._parameters = [
            ToolParameter(
                name="operation",
                type="string",
                description="Operation to perform",
                required=True,
                enum=["copy", "move", "delete"]
            ),
            ToolParameter(
                name="source",
                type="string",
                description="Source path",
                required=True
            ),
            ToolParameter(
                name="destination",
                type="string",
                description="Destination path (required for copy/move)",
                required=False
            )
        ]
        self._examples = [
            "Delete file report.txt",
            "Copy folder Data to Backup",
            "Move image.png to Pictures"
        ]

    def execute(self, operation: str, source: str, destination: str = None, **params) -> ToolResult:
        """Execute file operation"""
        try:
            system = get_system_control()
            result = system.perform_file_operation(operation, source, destination)

            if result["success"]:
                return ToolResult(
                    success=True,
                    data=result
                )
            else:
                return ToolResult(
                    success=False,
                    error=result.get("error", "File operation failed")
                )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"File operation error: {str(e)}"
            )

class KillProcessTool(Tool):
    """Terminate a running process"""
    name = "kill_process"
    description = "Terminate a running process by name or PID"
    category = ToolCategory.SYSTEM
    requires_confirmation = True

    def _setup_parameters(self) -> None:
        self._parameters = [
            ToolParameter(
                name="process_identifier",
                type="string",
                description="Process name (e.g., 'chrome') or PID",
                required=True
            )
        ]
        self._examples = [
            "Kill Chrome",
            "Stop process 1234",
            "End task python"
        ]

    def execute(self, process_identifier: str, **params) -> ToolResult:
        try:
            system = get_system_control()
            result = system.kill_process(process_identifier)
            if result["success"]:
                 return ToolResult(success=True, data=result)
            else:
                 return ToolResult(success=False, error=result.get("error", "Failed to kill process"))
        except Exception as e:
             return ToolResult(success=False, error=str(e))