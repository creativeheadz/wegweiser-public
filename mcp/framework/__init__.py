"""
MCP Framework - Extensible Model Context Protocol Server for Wegweiser Agents
"""

from .base_tool import MCPTool
from .tool_registry import ToolRegistry
from .server import MCPServer
from .config import ConfigManager

__version__ = "1.0.0"
__all__ = ["MCPTool", "ToolRegistry", "MCPServer", "ConfigManager"]
