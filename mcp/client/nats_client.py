"""
NATS MCP Client - Sends MCP requests to agents via NATS

Usage:
    client = NATSMCPClient(nats_server="nats://localhost:4222")
    await client.connect(username="user", password="pass")

    result = await client.execute_tool(
        device_uuid="device-id",
        tenant_uuid="tenant-id",
        tool_name="osquery_execute",
        parameters={"query": "SELECT * FROM processes LIMIT 5"}
    )
"""

import asyncio
import json
import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime

try:
    import nats
except ImportError:
    nats = None

logger = logging.getLogger(__name__)


class NATSMCPClient:
    """Client for sending MCP requests to agents via NATS"""

    def __init__(self, nats_server: str = "nats://localhost:4222"):
        """
        Initialize NATS MCP client

        Args:
            nats_server: NATS server URL
        """
        self.nats_server = nats_server
        self.nc = None
        self.request_timeout = 60  # seconds

    async def connect(
        self,
        username: str = None,
        password: str = None,
        name: str = "mcp-c2-client",
    ) -> bool:
        """
        Connect to NATS server

        Args:
            username: NATS username
            password: NATS password
            name: Client name for NATS

        Returns:
            bool: True if connection successful
        """
        try:
            if not nats:
                logger.error("nats-py not installed")
                return False

            logger.info(f"Connecting to NATS server: {self.nats_server}")

            # Build connection options
            kwargs = {"name": name, "max_reconnect_attempts": 10}

            if username and password:
                kwargs["user"] = username
                kwargs["password"] = password

            self.nc = await nats.connect(self.nats_server, **kwargs)

            logger.info("Connected to NATS server")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to NATS: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from NATS server"""
        if self.nc:
            await self.nc.close()
            logger.info("Disconnected from NATS")

    async def execute_tool(
        self,
        device_uuid: str,
        tenant_uuid: str,
        tool_name: str,
        parameters: Dict[str, Any] = None,
        timeout: int = None,
    ) -> Dict[str, Any]:
        """
        Execute a tool on a remote agent

        Args:
            device_uuid: Device UUID
            tenant_uuid: Tenant UUID
            tool_name: Name of tool to execute
            parameters: Tool parameters
            timeout: Request timeout in seconds

        Returns:
            dict: Tool execution result
        """
        try:
            if not self.nc:
                return {"success": False, "error": "Not connected to NATS"}

            timeout = timeout or self.request_timeout
            parameters = parameters or {}

            # Build MCP request
            request_id = str(uuid.uuid4())
            command_id = str(uuid.uuid4())

            request = {
                "request_id": request_id,
                "command": "mcp_execute",
                "command_id": command_id,
                "parameters": {"tool": tool_name, "parameters": parameters},
                "timestamp": int(datetime.now().timestamp() * 1000),
            }

            # Send to device command subject
            subject = f"tenant.{tenant_uuid}.device.{device_uuid}.command"

            logger.info(f"Sending MCP request to {subject}")
            logger.debug(f"Request: {json.dumps(request, indent=2)}")

            # Send request and wait for response
            response = await asyncio.wait_for(
                self.nc.request(subject, json.dumps(request).encode()),
                timeout=timeout,
            )

            response_data = json.loads(response.data.decode())

            logger.info(f"Received MCP response")
            logger.debug(f"Response: {json.dumps(response_data, indent=2)}")

            return response_data

        except asyncio.TimeoutError:
            logger.error(f"MCP request timed out after {timeout}s")
            return {
                "success": False,
                "error": f"Request timed out after {timeout}s",
            }
        except Exception as e:
            logger.error(f"Error executing MCP tool: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def get_available_tools(
        self,
        device_uuid: str,
        tenant_uuid: str,
        timeout: int = 30,
    ) -> Dict[str, Any]:
        """
        Get list of available tools on a device

        This is a utility that could be implemented on the agent side

        Args:
            device_uuid: Device UUID
            tenant_uuid: Tenant UUID
            timeout: Request timeout

        Returns:
            dict: Available tools metadata
        """
        # This would need to be implemented on the agent side
        logger.info(f"Getting available tools from device {device_uuid}")
        logger.warning(
            "Tool discovery not yet implemented on agent side"
        )
        return {"success": False, "error": "Not yet implemented"}
