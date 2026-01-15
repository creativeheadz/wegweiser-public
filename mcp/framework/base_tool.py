"""
Abstract base class for MCP tools - all tools must inherit from this
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import json


class MCPTool(ABC):
    """Abstract base class for Model Context Protocol tools"""

    def __init__(self):
        """Initialize tool"""
        self._metadata = None

    @abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get tool metadata including name, description, and parameters

        Returns:
            dict: Tool metadata with structure:
            {
                "name": "tool_name",
                "description": "Tool description",
                "parameters": {
                    "type": "object",
                    "properties": {...},
                    "required": [...]
                }
            }
        """
        pass

    @abstractmethod
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the tool with given parameters

        Args:
            parameters: Tool parameters from MCP request

        Returns:
            dict: Execution result with 'success' boolean and 'data' or 'error'
        """
        pass

    def validate_parameters(self, parameters: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate input parameters against tool's schema

        Args:
            parameters: Parameters to validate

        Returns:
            tuple: (is_valid, error_message)
        """
        try:
            metadata = self.get_metadata()
            required = metadata.get("parameters", {}).get("required", [])

            # Check required parameters
            for req_param in required:
                if req_param not in parameters:
                    return False, f"Missing required parameter: {req_param}"

            return True, None
        except Exception as e:
            return False, f"Validation error: {str(e)}"

    def __repr__(self) -> str:
        metadata = self.get_metadata()
        return f"<MCPTool: {metadata.get('name', 'Unknown')}>"
