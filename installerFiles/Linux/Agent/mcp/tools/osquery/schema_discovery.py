"""
osquery Schema Discovery Tool
Discovers available osquery tables and their schemas
"""

import logging
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from framework.base_tool import MCPTool
from osquery_client import OSQueryClient

logger = logging.getLogger(__name__)


class SchemaDiscovery(MCPTool):
    """Tool for discovering osquery schema information"""

    def __init__(self):
        """Initialize schema discovery tool"""
        super().__init__()
        self.osquery = OSQueryClient()

    def get_metadata(self) -> Dict[str, Any]:
        """Get tool metadata"""
        return {
            "name": "osquery_schema",
            "description": "Discover available osquery tables and their column schemas",
            "parameters": {
                "type": "object",
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": "Optional specific table name to get detailed schema (leave empty to list all tables)",
                    }
                },
                "required": [],
            },
        }

    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute schema discovery

        Args:
            parameters: Parameters dict with optional 'table_name'

        Returns:
            dict: Schema information
        """
        try:
            if not self.osquery.is_available():
                return {
                    "success": False,
                    "error": "osquery is not available on this system",
                }

            table_name = parameters.get("table_name", "").strip() or None

            logger.info(f"Discovering osquery schema (table: {table_name or 'ALL'})")

            # Get schema
            result = await self.osquery.get_schema(table_name)

            if result.get("success"):
                logger.info(
                    f"Schema discovery successful: {result.get('table_count') or result.get('column_count')} items"
                )

                return {
                    "success": True,
                    "data": {
                        "table_name": result.get("table_name"),
                        "tables": result.get("tables"),
                        "table_count": result.get("table_count"),
                        "columns": result.get("columns"),
                        "column_count": result.get("column_count"),
                    },
                }
            else:
                error_msg = result.get("error", "Unknown error")
                logger.error(f"Schema discovery failed: {error_msg}")
                return {"success": False, "error": error_msg}

        except Exception as e:
            logger.error(f"Error in schema discovery: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
