"""
osquery Query Executor Tool
Executes osquery SQL queries
"""

import logging
import sys
from pathlib import Path
from typing import Dict, Any

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from framework.base_tool import MCPTool
from osquery_client import OSQueryClient

logger = logging.getLogger(__name__)


class QueryExecutor(MCPTool):
    """Tool for executing osquery SQL queries"""

    def __init__(self):
        """Initialize query executor tool"""
        super().__init__()
        self.osquery = OSQueryClient()

    def get_metadata(self) -> Dict[str, Any]:
        """Get tool metadata"""
        return {
            "name": "osquery_execute",
            "description": "Execute an osquery SQL query and return results",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "SQL query to execute (SELECT statements only)",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Query timeout in seconds (default: 30, max: 300)",
                    },
                },
                "required": ["query"],
            },
        }

    def validate_parameters(self, parameters: Dict[str, Any]) -> tuple[bool, str]:
        """Validate query parameters"""
        try:
            query = parameters.get("query", "").strip()

            if not query:
                return False, "Query is required"

            if not query.upper().startswith("SELECT"):
                return False, "Only SELECT queries are supported"

            timeout = parameters.get("timeout", 30)
            if not isinstance(timeout, (int, float)):
                return False, "Timeout must be a number"

            if timeout < 1 or timeout > 300:
                return False, "Timeout must be between 1 and 300 seconds"

            return True, None

        except Exception as e:
            return False, f"Validation error: {str(e)}"

    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an osquery query

        Args:
            parameters: Parameters dict with 'query' and optional 'timeout'

        Returns:
            dict: Query execution result
        """
        try:
            if not self.osquery.is_available():
                return {
                    "success": False,
                    "error": "osquery is not available on this system",
                }

            query = parameters.get("query", "").strip()
            timeout = parameters.get("timeout", 30)

            logger.info(f"Executing osquery: {query[:100]}...")

            # Execute query
            result = await self.osquery.execute_query(query, timeout=timeout)

            if result.get("success"):
                logger.info(
                    f"Query successful: {result.get('row_count', 0)} rows returned"
                )

                return {
                    "success": True,
                    "data": {
                        "query": query,
                        "data": result.get("data", []),
                        "row_count": result.get("row_count", 0),
                    },
                }
            else:
                error_msg = result.get("error", "Unknown error")
                logger.error(f"Query execution failed: {error_msg}")
                return {"success": False, "error": error_msg}

        except Exception as e:
            logger.error(f"Error executing query: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
