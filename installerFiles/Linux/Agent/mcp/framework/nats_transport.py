"""
NATS Transport Layer for MCP Framework
Handles NATS messaging for MCP protocol
"""

import asyncio
import json
import logging
import uuid
from typing import Dict, Any, Callable, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class NATSTransport:
    """NATS transport for MCP framework"""

    def __init__(self, nats_client=None, device_uuid: str = None):
        """
        Initialize NATS transport

        Args:
            nats_client: Connected NATS client (from nats_service)
            device_uuid: Device UUID for subject routing
        """
        self.nats = nats_client
        self.device_uuid = device_uuid
        self.request_handlers: Dict[str, Callable] = {}
        self.pending_requests: Dict[str, asyncio.Event] = {}
        self.pending_responses: Dict[str, Dict[str, Any]] = {}

    async def subscribe_to_mcp_requests(self, handler: Callable) -> bool:
        """
        Subscribe to MCP request subject

        Args:
            handler: Async function(request_dict) -> response_dict

        Returns:
            bool: True if subscription successful
        """
        if not self.nats:
            logger.error("NATS client not available")
            return False

        try:
            subject = f"mcp.{self.device_uuid}.request"

            async def message_handler(msg):
                try:
                    request_data = json.loads(msg.data.decode())
                    logger.debug(f"Received MCP request: {request_data}")

                    # Handle the request
                    response = await handler(request_data)

                    # Send response
                    response_subject = msg.reply
                    if response_subject:
                        await self.nats.publish(
                            response_subject, json.dumps(response).encode()
                        )

                except Exception as e:
                    logger.error(f"Error handling MCP request: {e}", exc_info=True)

            await self.nats.subscribe(subject, cb=message_handler)
            logger.info(f"Subscribed to MCP requests on {subject}")
            return True

        except Exception as e:
            logger.error(f"Error subscribing to MCP requests: {e}")
            return False

    async def send_mcp_response(
        self, request_id: str, success: bool, data: Any = None, error: str = None
    ) -> bool:
        """
        Send MCP response

        Args:
            request_id: ID of the original request
            success: Whether request succeeded
            data: Response data (if success=True)
            error: Error message (if success=False)

        Returns:
            bool: True if sent successfully
        """
        if not self.nats:
            logger.error("NATS client not available")
            return False

        try:
            response = {
                "request_id": request_id,
                "success": success,
                "timestamp": datetime.now().isoformat(),
            }

            if success and data:
                response["data"] = data
            elif not success and error:
                response["error"] = error

            # Response goes to the reply subject that was in the request
            # This is handled automatically by the request-reply pattern
            logger.debug(f"MCP response prepared: {response}")
            return True

        except Exception as e:
            logger.error(f"Error preparing MCP response: {e}")
            return False

    async def request_tool_execution(
        self, tool_name: str, parameters: Dict[str, Any], timeout: int = 30
    ) -> Dict[str, Any]:
        """
        Send a tool execution request via NATS

        Args:
            tool_name: Name of tool to execute
            parameters: Tool parameters
            timeout: Request timeout in seconds

        Returns:
            dict: Response from tool execution
        """
        if not self.nats:
            logger.error("NATS client not available")
            return {"success": False, "error": "NATS not available"}

        try:
            request_id = str(uuid.uuid4())
            subject = f"mcp.{self.device_uuid}.request"

            request_data = {
                "request_id": request_id,
                "tool": tool_name,
                "parameters": parameters,
                "timestamp": datetime.now().isoformat(),
            }

            logger.debug(f"Sending MCP request: {request_data}")

            # Use NATS request-reply pattern
            response = await asyncio.wait_for(
                self.nats.request(subject, json.dumps(request_data).encode()),
                timeout=timeout,
            )

            response_data = json.loads(response.data.decode())
            logger.debug(f"Received MCP response: {response_data}")
            return response_data

        except asyncio.TimeoutError:
            logger.error(f"MCP request timeout for tool: {tool_name}")
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            logger.error(f"Error sending MCP request: {e}")
            return {"success": False, "error": str(e)}

    def format_mcp_request(
        self, tool_name: str, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Format a request in MCP protocol"""
        return {
            "request_id": str(uuid.uuid4()),
            "tool": tool_name,
            "parameters": parameters,
            "timestamp": datetime.now().isoformat(),
        }

    def format_mcp_response(
        self, request_id: str, success: bool, data: Any = None, error: str = None
    ) -> Dict[str, Any]:
        """Format a response in MCP protocol"""
        response = {
            "request_id": request_id,
            "success": success,
            "timestamp": datetime.now().isoformat(),
        }

        if success and data is not None:
            response["data"] = data
        elif not success and error:
            response["error"] = error

        return response
