"""
MCP Server - Main orchestrator for tool execution
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path

from .tool_registry import ToolRegistry
from .config import ConfigManager
from .nats_transport import NATSTransport

logger = logging.getLogger(__name__)


class MCPServer:
    """Main MCP Server - orchestrates tool execution"""

    def __init__(
        self,
        tools_dir: Path = None,
        config_dir: Path = None,
        nats_client=None,
        device_uuid: str = None,
    ):
        """
        Initialize MCP Server

        Args:
            tools_dir: Path to tools directory (defaults to ../tools/)
            config_dir: Path to config directory (defaults to ../config/)
            nats_client: Connected NATS client
            device_uuid: Device UUID for NATS routing
        """
        if tools_dir is None:
            tools_dir = Path(__file__).parent.parent / "tools"
        if config_dir is None:
            config_dir = Path(__file__).parent.parent / "config"

        self.tools_dir = Path(tools_dir)
        self.config_dir = Path(config_dir)
        self.nats_client = nats_client
        self.device_uuid = device_uuid

        # Initialize components
        self.config = ConfigManager(config_dir)
        self.registry = ToolRegistry(tools_dir, self.config.config)
        self.transport = NATSTransport(nats_client, device_uuid)

        self.is_running = False

    async def initialize(self) -> bool:
        """
        Initialize the MCP server

        Returns:
            bool: True if initialization successful
        """
        try:
            logger.info("Initializing MCP Server...")

            # Discover and load tools
            if not self.registry.discover_and_load():
                logger.warning("No tools loaded, but server can still function")

            logger.info(
                f"MCP Server initialized with {len(self.registry.tools)} tools"
            )
            return True

        except Exception as e:
            logger.error(f"Error initializing MCP Server: {e}", exc_info=True)
            return False

    async def start(self) -> bool:
        """
        Start the MCP server

        Returns:
            bool: True if started successfully
        """
        try:
            logger.info("Starting MCP Server...")

            if self.nats_client:
                # Subscribe to NATS MCP requests
                if not await self.transport.subscribe_to_mcp_requests(
                    self._handle_mcp_request
                ):
                    logger.warning("Failed to subscribe to MCP requests")
            else:
                logger.warning("NATS client not available, standalone mode only")

            self.is_running = True
            logger.info("MCP Server started")
            return True

        except Exception as e:
            logger.error(f"Error starting MCP Server: {e}", exc_info=True)
            return False

    async def _handle_mcp_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle an MCP request

        Args:
            request: MCP request dict

        Returns:
            dict: MCP response
        """
        try:
            request_id = request.get("request_id", "unknown")
            tool_name = request.get("tool")
            parameters = request.get("parameters", {})

            logger.info(
                f"Handling MCP request {request_id}: tool={tool_name}, params={parameters}"
            )

            # Validate tool exists
            if not self.registry.has_tool(tool_name):
                error_msg = f"Tool not found: {tool_name}"
                logger.warning(error_msg)
                return self.transport.format_mcp_response(
                    request_id, False, error=error_msg
                )

            # Get tool instance
            tool = self.registry.get_tool(tool_name)

            # Validate parameters
            is_valid, validation_error = tool.validate_parameters(parameters)
            if not is_valid:
                logger.warning(f"Parameter validation failed: {validation_error}")
                return self.transport.format_mcp_response(
                    request_id, False, error=validation_error
                )

            # Execute tool
            logger.debug(f"Executing tool {tool_name}")
            result = await tool.execute(parameters)

            # Format response
            if result.get("success"):
                return self.transport.format_mcp_response(
                    request_id, True, data=result.get("data")
                )
            else:
                return self.transport.format_mcp_response(
                    request_id, False, error=result.get("error", "Unknown error")
                )

        except Exception as e:
            logger.error(f"Error handling MCP request: {e}", exc_info=True)
            return self.transport.format_mcp_response(
                request.get("request_id", "unknown"),
                False,
                error=f"Internal server error: {str(e)}",
            )

    async def execute_tool(
        self, tool_name: str, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a tool directly (local mode)

        Args:
            tool_name: Name of tool to execute
            parameters: Tool parameters

        Returns:
            dict: Tool execution result
        """
        try:
            if not self.registry.has_tool(tool_name):
                return {"success": False, "error": f"Tool not found: {tool_name}"}

            tool = self.registry.get_tool(tool_name)

            # Validate parameters
            is_valid, validation_error = tool.validate_parameters(parameters)
            if not is_valid:
                return {"success": False, "error": validation_error}

            # Execute
            result = await tool.execute(parameters)
            return result

        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def get_tools(self) -> Dict[str, Any]:
        """Get metadata for all available tools"""
        return self.registry.list_tools()

    def get_tool_metadata(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific tool"""
        return self.registry.get_tool_metadata(tool_name)

    def list_tools(self) -> list:
        """Get list of tool names"""
        return list(self.registry.tools.keys())

    def __repr__(self) -> str:
        return f"<MCPServer: {len(self.registry.tools)} tools>"
