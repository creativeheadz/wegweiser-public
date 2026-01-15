"""
MCP Handler - Routes MCP requests to MCP framework tools
Integrates MCP server with agent NATS communication
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class MCPHandler:
    """Handles MCP tool execution requests"""

    def __init__(self, mcp_dir: Path = None):
        """
        Initialize MCP handler

        Args:
            mcp_dir: Path to MCP framework directory
        """
        if mcp_dir is None:
            # Try to find MCP directory relative to this file
            agent_dir = Path(__file__).parent.parent
            mcp_dir = agent_dir / "mcp"

        self.mcp_dir = Path(mcp_dir)
        self.mcp_server = None

        # Add MCP to path
        if str(self.mcp_dir) not in sys.path:
            sys.path.insert(0, str(self.mcp_dir))

    async def initialize(self) -> bool:
        """
        Initialize MCP server

        Returns:
            bool: True if initialized successfully
        """
        try:
            if not self.mcp_dir.exists():
                logger.warning(f"MCP directory not found: {self.mcp_dir}")
                return False

            logger.info(f"Loading MCP framework from: {self.mcp_dir}")

            # Import MCP framework
            from framework.server import MCPServer

            # Initialize MCP server
            self.mcp_server = MCPServer(
                tools_dir=self.mcp_dir / "tools",
                config_dir=self.mcp_dir / "config",
                device_uuid="agent-device",  # Will be updated by agent
            )

            # Initialize
            if not await self.mcp_server.initialize():
                logger.error("Failed to initialize MCP server")
                return False

            logger.info(f"MCP handler initialized with {len(self.mcp_server.list_tools())} tools")
            logger.info(f"Available tools: {', '.join(self.mcp_server.list_tools())}")

            return True

        except Exception as e:
            logger.error(f"Error initializing MCP handler: {e}", exc_info=True)
            return False

    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an MCP tool

        Args:
            tool_name: Name of the tool to execute
            parameters: Tool parameters

        Returns:
            dict: Execution result
        """
        try:
            if not self.mcp_server:
                return {"success": False, "error": "MCP server not initialized"}

            logger.info(f"Executing MCP tool: {tool_name} with params: {parameters}")

            # Execute tool
            result = await self.mcp_server.execute_tool(tool_name, parameters)

            logger.info(f"MCP tool {tool_name} result: {result.get('success')}")

            return result

        except Exception as e:
            logger.error(f"Error executing MCP tool {tool_name}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def handle_mcp_request(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle MCP request from NATS

        Expected parameters:
        {
            "tool": "tool_name",
            "parameters": {...}
        }

        Returns:
            dict: Execution result
        """
        try:
            tool_name = parameters.get("tool")
            tool_params = parameters.get("parameters", {})

            if not tool_name:
                return {"success": False, "error": "Missing 'tool' parameter"}

            # Execute the tool
            result = await self.execute_tool(tool_name, tool_params)

            return result

        except Exception as e:
            logger.error(f"Error handling MCP request: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def list_tools(self) -> Dict[str, Any]:
        """Get list of available tools"""
        if not self.mcp_server:
            return {}

        return self.mcp_server.get_tools()

    def get_tool_metadata(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific tool"""
        if not self.mcp_server:
            return None

        return self.mcp_server.get_tool_metadata(tool_name)
