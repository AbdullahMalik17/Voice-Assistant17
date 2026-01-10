"""
Tools Module
Provides the Tool interface and ToolRegistry for agentic tool execution.
"""

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type

logger = logging.getLogger(__name__)


class ToolCategory(str, Enum):
    """Categories of tools"""
    SYSTEM = "system"
    COMMUNICATION = "communication"
    PRODUCTIVITY = "productivity"
    INFORMATION = "information"
    AUTOMATION = "automation"
    CUSTOM = "custom"


@dataclass
class ToolParameter:
    """Definition of a tool parameter"""
    name: str
    type: str  # string, number, boolean, array, object
    description: str
    required: bool = True
    default: Optional[Any] = None
    enum: Optional[List[Any]] = None  # Allowed values

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "required": self.required,
            "default": self.default,
            "enum": self.enum
        }


@dataclass
class ToolResult:
    """Result of a tool execution"""
    success: bool
    data: Optional[Any] = None
    message: Optional[str] = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "message": self.message,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
            "metadata": self.metadata
        }


@dataclass
class ToolDescription:
    """Description of a tool for the planner"""
    name: str
    description: str
    category: ToolCategory
    parameters: List[ToolParameter]
    requires_confirmation: bool
    examples: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "parameters": [p.to_dict() for p in self.parameters],
            "requires_confirmation": self.requires_confirmation,
            "examples": self.examples
        }

    def to_prompt_format(self) -> str:
        """Format for LLM prompts"""
        params_str = ", ".join(
            f"{p.name}: {p.type}" + ("" if p.required else "?")
            for p in self.parameters
        )
        return f"- {self.name}({params_str}): {self.description}"


class Tool(ABC):
    """
    Abstract base class for all tools.

    Tools are the atomic actions that the agent can execute.
    Each tool should have a clear purpose and well-defined parameters.
    """

    # Class attributes to be overridden
    name: str = "base_tool"
    description: str = "Base tool"
    category: ToolCategory = ToolCategory.CUSTOM
    requires_confirmation: bool = False

    def __init__(self):
        self._parameters: List[ToolParameter] = []
        self._examples: List[str] = []
        self._setup_parameters()

    def _setup_parameters(self) -> None:
        """Override to define tool parameters"""
        pass

    @abstractmethod
    def execute(self, **params: Any) -> ToolResult:
        """
        Execute the tool with the given parameters.

        Args:
            **params: Tool-specific parameters

        Returns:
            ToolResult with success/failure and data
        """
        pass

    def validate_params(self, params: Dict[str, Any]) -> Optional[str]:
        """
        Validate parameters before execution.

        Returns:
            Error message if validation fails, None if valid
        """
        for param in self._parameters:
            if param.required and param.name not in params:
                return f"Missing required parameter: {param.name}"

            if param.name in params and param.enum:
                if params[param.name] not in param.enum:
                    return f"Invalid value for {param.name}. Must be one of: {param.enum}"

        return None

    def get_description(self) -> ToolDescription:
        """Get the tool description for the planner"""
        return ToolDescription(
            name=self.name,
            description=self.description,
            category=self.category,
            parameters=self._parameters,
            requires_confirmation=self.requires_confirmation,
            examples=self._examples
        )

    def safe_execute(self, **params: Any) -> ToolResult:
        """
        Execute with validation and error handling.
        """
        start_time = time.time()

        # Validate parameters
        validation_error = self.validate_params(params)
        if validation_error:
            return ToolResult(
                success=False,
                error=validation_error,
                execution_time_ms=0
            )

        try:
            result = self.execute(**params)
            result.execution_time_ms = (time.time() - start_time) * 1000
            return result
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                execution_time_ms=(time.time() - start_time) * 1000
            )


class ToolRegistry:
    """
    Registry for managing available tools.

    Provides tool discovery, registration, and lookup for the planner.
    """

    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._categories: Dict[ToolCategory, List[str]] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool"""
        self._tools[tool.name] = tool

        # Update category index
        if tool.category not in self._categories:
            self._categories[tool.category] = []
        self._categories[tool.category].append(tool.name)

    def unregister(self, tool_name: str) -> bool:
        """Unregister a tool"""
        if tool_name in self._tools:
            tool = self._tools[tool_name]
            del self._tools[tool_name]

            if tool.category in self._categories:
                self._categories[tool.category].remove(tool_name)

            return True
        return False

    def get(self, tool_name: str) -> Optional[Tool]:
        """Get a tool by name"""
        return self._tools.get(tool_name)

    def list_available(self) -> List[ToolDescription]:
        """List all available tools"""
        return [tool.get_description() for tool in self._tools.values()]

    def list_by_category(self, category: ToolCategory) -> List[ToolDescription]:
        """List tools in a specific category"""
        tool_names = self._categories.get(category, [])
        return [
            self._tools[name].get_description()
            for name in tool_names
            if name in self._tools
        ]

    def get_tools_for_prompt(self) -> str:
        """Format all tools for LLM prompts"""
        lines = ["Available tools:"]
        for tool in self._tools.values():
            lines.append(tool.get_description().to_prompt_format())
        return "\n".join(lines)

    def execute(self, tool_name: str, **params: Any) -> ToolResult:
        """Execute a tool by name"""
        tool = self.get(tool_name)
        if not tool:
            return ToolResult(
                success=False,
                error=f"Tool not found: {tool_name}"
            )
        return tool.safe_execute(**params)

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics"""
        return {
            "total_tools": len(self._tools),
            "categories": {
                cat.value: len(tools)
                for cat, tools in self._categories.items()
            }
        }


# ============================================================================
# Built-in Tools
# ============================================================================

class SystemStatusTool(Tool):
    """Get system status information"""
    name = "system_status"
    description = "Get system information like CPU, memory, disk usage, and battery status"
    category = ToolCategory.SYSTEM
    requires_confirmation = False

    def _setup_parameters(self) -> None:
        self._parameters = [
            ToolParameter(
                name="info_type",
                type="string",
                description="Type of information to get",
                required=False,
                default="all",
                enum=["cpu", "memory", "disk", "battery", "temperature", "all"]
            )
        ]
        self._examples = [
            "Check my CPU usage",
            "How much disk space do I have?",
            "What's my battery level?"
        ]

    def execute(self, info_type: str = "all", **params) -> ToolResult:
        import psutil

        data = {}

        if info_type in ["cpu", "all"]:
            data["cpu_percent"] = psutil.cpu_percent(interval=0.1)
            data["cpu_count"] = psutil.cpu_count()

        if info_type in ["memory", "all"]:
            mem = psutil.virtual_memory()
            data["memory_percent"] = mem.percent
            data["memory_available_gb"] = round(mem.available / (1024**3), 2)
            data["memory_total_gb"] = round(mem.total / (1024**3), 2)

        if info_type in ["disk", "all"]:
            disk = psutil.disk_usage('/')
            data["disk_percent"] = disk.percent
            data["disk_free_gb"] = round(disk.free / (1024**3), 2)
            data["disk_total_gb"] = round(disk.total / (1024**3), 2)

        if info_type in ["battery", "all"]:
            battery = psutil.sensors_battery()
            if battery:
                data["battery_percent"] = battery.percent
                data["battery_charging"] = battery.power_plugged
            else:
                data["battery"] = "Not available"

        if info_type in ["temperature", "all"]:
            try:
                temps = psutil.sensors_temperatures()
                if temps:
                    for name, entries in temps.items():
                        if entries:
                            data[f"temp_{name}"] = entries[0].current
            except Exception:
                data["temperature"] = "Not available"

        return ToolResult(success=True, data=data)


class SetTimerTool(Tool):
    """Set a countdown timer"""
    name = "set_timer"
    description = "Set a countdown timer for a specified duration"
    category = ToolCategory.PRODUCTIVITY
    requires_confirmation = False

    def _setup_parameters(self) -> None:
        self._parameters = [
            ToolParameter(
                name="duration_seconds",
                type="number",
                description="Duration in seconds",
                required=True
            ),
            ToolParameter(
                name="label",
                type="string",
                description="Label for the timer",
                required=False,
                default="Timer"
            )
        ]
        self._examples = [
            "Set a timer for 5 minutes",
            "Timer for 30 seconds",
            "Remind me in 1 hour"
        ]

    def execute(self, duration_seconds: int, label: str = "Timer", **params) -> ToolResult:
        # In a real implementation, this would start a background timer
        # For now, we just acknowledge the request
        minutes = duration_seconds // 60
        seconds = duration_seconds % 60

        if minutes > 0:
            time_str = f"{minutes} minute{'s' if minutes != 1 else ''}"
            if seconds > 0:
                time_str += f" and {seconds} second{'s' if seconds != 1 else ''}"
        else:
            time_str = f"{seconds} second{'s' if seconds != 1 else ''}"

        return ToolResult(
            success=True,
            data={
                "message": f"Timer '{label}' set for {time_str}",
                "duration_seconds": duration_seconds,
                "label": label,
                "end_time": (datetime.now().timestamp() + duration_seconds)
            }
        )


class WebSearchTool(Tool):
    """Search the web"""
    name = "web_search"
    description = "Search the web for information"
    category = ToolCategory.INFORMATION
    requires_confirmation = False

    def _setup_parameters(self) -> None:
        self._parameters = [
            ToolParameter(
                name="query",
                type="string",
                description="Search query",
                required=True
            )
        ]
        self._examples = [
            "Search for Python tutorials",
            "Look up weather in Tokyo",
            "Find information about AI"
        ]

    def execute(self, query: str, **params) -> ToolResult:
        # In a real implementation, this would call a search API
        # For now, we acknowledge the request
        return ToolResult(
            success=True,
            data={
                "message": f"Searching for: {query}",
                "query": query,
                "note": "Web search API integration required"
            }
        )


class GetWeatherTool(Tool):
    """Get weather information"""
    name = "get_weather"
    description = "Get current weather or forecast for a location"
    category = ToolCategory.INFORMATION
    requires_confirmation = False

    def _setup_parameters(self) -> None:
        self._parameters = [
            ToolParameter(
                name="location",
                type="string",
                description="Location to get weather for",
                required=False,
                default="current location"
            ),
            ToolParameter(
                name="forecast_days",
                type="number",
                description="Number of forecast days (0 for current only)",
                required=False,
                default=0
            )
        ]
        self._examples = [
            "What's the weather today?",
            "Weather in New York",
            "5-day forecast for London"
        ]

    def execute(
        self,
        location: str = "current location",
        forecast_days: int = 0,
        **params
    ) -> ToolResult:
        # In a real implementation, this would call a weather API
        return ToolResult(
            success=True,
            data={
                "message": f"Getting weather for {location}",
                "location": location,
                "forecast_days": forecast_days,
                "note": "Weather API integration required"
            }
        )


def create_default_registry(sqlite_store=None) -> ToolRegistry:
    """
    Create a registry with default built-in tools.

    Args:
        sqlite_store: Optional SqliteStore instance for conversation history tools

    Returns:
        ToolRegistry with all available tools registered
    """
    registry = ToolRegistry()

    # Register built-in tools
    registry.register(SystemStatusTool())
    registry.register(SetTimerTool())
    registry.register(WebSearchTool())
    registry.register(GetWeatherTool())

    # Register browser automation tools
    try:
        from .browser_tools import (
            BrowserNavigateTool,
            BrowserSearchTool,
            OpenGmailTool,
            OpenGoogleDriveTool,
            BrowserScreenshotTool,
            BrowserClickTool,
            BrowserTypeTool,
            # Enhanced browser tools (Phase 1D)
            FillFormTool,
            SelectDropdownTool,
            HandlePopupTool,
            WaitForNavigationTool,
            SwitchToIframeTool,
            GetCookiesTool,
            SetCookiesTool,
            ExecuteScriptTool
        )

        registry.register(BrowserNavigateTool())
        registry.register(BrowserSearchTool())
        registry.register(OpenGmailTool())
        registry.register(OpenGoogleDriveTool())
        registry.register(BrowserScreenshotTool())
        registry.register(BrowserClickTool())
        registry.register(BrowserTypeTool())

        # Register enhanced browser tools
        registry.register(FillFormTool())
        registry.register(SelectDropdownTool())
        registry.register(HandlePopupTool())
        registry.register(WaitForNavigationTool())
        registry.register(SwitchToIframeTool())
        registry.register(GetCookiesTool())
        registry.register(SetCookiesTool())
        registry.register(ExecuteScriptTool())

        logger.info("Browser automation tools (basic + enhanced) registered successfully")
    except ImportError as e:
        # Browser tools optional if Playwright not installed
        logger.debug(f"Browser tools not available: {e}")
        pass

    # Register system control tools
    try:
        from .system_tools import (
            FindFileTool,
            TakeScreenshotTool,
            GetSystemInfoTool,
            MinimizeWindowsTool,
            ListProcessesTool,
            CreateFolderTool,
            OpenFileLocationTool,
            LaunchAppTool,
            FileOperationTool,
            KillProcessTool
        )

        registry.register(FindFileTool())
        registry.register(TakeScreenshotTool())
        registry.register(GetSystemInfoTool())
        registry.register(MinimizeWindowsTool())
        registry.register(ListProcessesTool())
        registry.register(CreateFolderTool())
        registry.register(OpenFileLocationTool())
        registry.register(LaunchAppTool())
        registry.register(FileOperationTool())
        registry.register(KillProcessTool())
    except ImportError as e:
        # System tools optional
        pass

    # Register Gmail and Drive API tools
    try:
        from .gmail_drive_tools import (
            ListEmailsTool,
            ReadEmailTool,
            SearchEmailsTool,
            SendEmailTool,
            ListDriveFilesTool,
            SearchDriveFilesTool,
            DownloadDriveFileTool,
            UploadDriveFileTool
        )

        registry.register(ListEmailsTool())
        registry.register(ReadEmailTool())
        registry.register(SearchEmailsTool())
        registry.register(SendEmailTool())
        registry.register(ListDriveFilesTool())
        registry.register(SearchDriveFilesTool())
        registry.register(DownloadDriveFileTool())
        registry.register(UploadDriveFileTool())
    except ImportError as e:
        # Register Gmail/Drive tools optional if Google APIs not installed
        pass

    # Register Slack communication tools
    try:
        from .slack_tools import (
            SendSlackMessageTool,
            ListSlackChannelsTool,
            SearchSlackMessagesTool,
            GetSlackThreadTool,
            PostSlackFileTool
        )

        registry.register(SendSlackMessageTool())
        registry.register(ListSlackChannelsTool())
        registry.register(SearchSlackMessagesTool())
        registry.register(GetSlackThreadTool())
        registry.register(PostSlackFileTool())

        logger.info("Slack communication tools registered successfully")
    except ImportError as e:
        # Slack tools optional if slack-sdk not installed
        logger.debug(f"Slack tools not available: {e}")
        pass

    # Register Discord communication tools
    try:
        from .discord_tools import (
            SendDiscordMessageTool,
            ListDiscordServersTool,
            PostDiscordEmbedTool,
            PostDiscordFileTool,
            SendDiscordThreadMessageTool
        )

        registry.register(SendDiscordMessageTool())
        registry.register(ListDiscordServersTool())
        registry.register(PostDiscordEmbedTool())
        registry.register(PostDiscordFileTool())
        registry.register(SendDiscordThreadMessageTool())

        logger.info("Discord communication tools registered successfully")
    except ImportError as e:
        # Discord tools optional if discord.py not installed
        logger.debug(f"Discord tools not available: {e}")
        pass

    # Register Notion productivity tools
    try:
        from .notion_tools import (
            CreateNotionPageTool,
            QueryNotionDatabaseTool,
            UpdateNotionPageTool,
            SearchNotionTool,
            RetrieveNotionPageTool
        )

        registry.register(CreateNotionPageTool())
        registry.register(QueryNotionDatabaseTool())
        registry.register(UpdateNotionPageTool())
        registry.register(SearchNotionTool())
        registry.register(RetrieveNotionPageTool())

        logger.info("Notion productivity tools registered successfully")
    except ImportError as e:
        # Notion tools optional if notion-client not installed
        logger.debug(f"Notion tools not available: {e}")
        pass

    # Register Trello productivity tools
    try:
        from .trello_tools import (
            CreateTrelloCardTool,
            ListTrelloBoardsTool,
            MoveTrelloCardTool,
            AddTrelloCommentTool,
            SearchTrelloTool
        )

        registry.register(CreateTrelloCardTool())
        registry.register(ListTrelloBoardsTool())
        registry.register(MoveTrelloCardTool())
        registry.register(AddTrelloCommentTool())
        registry.register(SearchTrelloTool())

        logger.info("Trello productivity tools registered successfully")
    except ImportError as e:
        # Trello tools optional if requests not installed or API errors
        logger.debug(f"Trello tools not available: {e}")
        pass

    # Register Desktop Automation Tools
    try:
        from .desktop_tools import (
            VolumeControlTool,
            MediaControlTool,
            BrightnessControlTool,
            PowerControlTool,
            AppVolumeControlTool,
            WindowControlTool
        )
        registry.register(VolumeControlTool())
        registry.register(MediaControlTool())
        registry.register(BrightnessControlTool())
        registry.register(PowerControlTool())
        registry.register(AppVolumeControlTool())
        registry.register(WindowControlTool())
    except ImportError:
        pass

    # Register User Data Access Tools (conversation history, etc.)
    if sqlite_store:
        try:
            from .user_tools import (
                SearchConversationHistoryTool,
                GetRecentConversationsTool
            )
            registry.register(SearchConversationHistoryTool(sqlite_store))
            registry.register(GetRecentConversationsTool(sqlite_store))
        except ImportError as e:
            # User tools optional
            pass

    return registry
