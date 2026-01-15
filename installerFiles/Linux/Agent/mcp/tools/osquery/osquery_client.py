"""
osquery client wrapper
"""

import subprocess
import json
import logging
import platform
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class OSQueryClient:
    """Wrapper for osquery command-line interface"""

    def __init__(self):
        """Initialize osquery client"""
        self.osquery_path = self._find_osquery_executable()
        self.platform = platform.system()

    def _find_osquery_executable(self) -> Optional[str]:
        """Find osquery executable on the system"""
        possible_paths = [
            "osqueryi",  # In PATH
            "/usr/bin/osqueryi",  # Linux
            "/usr/local/bin/osqueryi",  # macOS
            "/opt/osquery/bin/osqueryi",  # Custom location
            "C:\\Program Files\\osquery\\osqueryi.exe",  # Windows
            "C:\\Program Files (x86)\\osquery\\osqueryi.exe",  # Windows alt
        ]

        for path in possible_paths:
            try:
                result = subprocess.run(
                    [path, "--version"],
                    capture_output=True,
                    timeout=5,
                    text=True,
                )
                if result.returncode == 0:
                    logger.info(f"Found osquery at: {path}")
                    return path
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                continue

        logger.warning("osquery executable not found")
        return None

    def is_available(self) -> bool:
        """Check if osquery is available"""
        return self.osquery_path is not None

    async def execute_query(
        self, query: str, timeout: int = 30
    ) -> Dict[str, Any]:
        """
        Execute an osquery SQL query

        Args:
            query: SQL query string
            timeout: Query timeout in seconds

        Returns:
            dict: Query result with success flag and data
        """
        if not self.osquery_path:
            return {
                "success": False,
                "error": "osquery not available on this system",
            }

        if not query.strip():
            return {"success": False, "error": "Empty query"}

        try:
            # Build command
            cmd = [self.osquery_path, "--json", query]

            logger.debug(f"Executing osquery: {query}")

            # Execute command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            if result.returncode != 0:
                error_msg = result.stderr or f"osquery failed with code {result.returncode}"
                logger.error(f"osquery error: {error_msg}")
                return {"success": False, "error": error_msg, "query": query}

            # Parse JSON output
            try:
                data = json.loads(result.stdout)
                row_count = len(data) if isinstance(data, list) else 1

                logger.debug(f"osquery returned {row_count} rows")

                return {
                    "success": True,
                    "query": query,
                    "data": data,
                    "row_count": row_count,
                }

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse osquery output: {e}")
                return {
                    "success": False,
                    "error": f"Failed to parse osquery output: {str(e)}",
                    "query": query,
                    "raw_output": result.stdout[:500],  # First 500 chars
                }

        except subprocess.TimeoutExpired:
            logger.error(f"osquery query timed out after {timeout}s")
            return {
                "success": False,
                "error": f"osquery query timed out after {timeout}s",
                "query": query,
            }

        except Exception as e:
            logger.error(f"Error executing osquery: {e}", exc_info=True)
            return {"success": False, "error": str(e), "query": query}

    async def get_schema(
        self, table_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get osquery schema information

        Args:
            table_name: Optional specific table name

        Returns:
            dict: Schema information with success flag and data
        """
        try:
            if table_name:
                # Get schema for specific table
                query = f"PRAGMA table_info({table_name});"
            else:
                # Get all tables
                query = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"

            logger.debug(f"Getting schema: {query}")

            result = await self.execute_query(query, timeout=10)

            if not result.get("success"):
                return result

            if table_name:
                # Format column info
                columns = []
                for row in result.get("data", []):
                    columns.append(
                        {
                            "name": row.get("name"),
                            "type": row.get("type"),
                            "cid": row.get("cid"),
                        }
                    )
                return {
                    "success": True,
                    "table_name": table_name,
                    "columns": columns,
                    "column_count": len(columns),
                }
            else:
                # List all tables
                tables = [row.get("name") for row in result.get("data", [])]
                return {
                    "success": True,
                    "tables": tables,
                    "table_count": len(tables),
                }

        except Exception as e:
            logger.error(f"Error getting schema: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def validate_query(self, query: str) -> Dict[str, Any]:
        """
        Validate an osquery SQL query by executing it with LIMIT 1

        Args:
            query: SQL query to validate

        Returns:
            dict: Validation result
        """
        try:
            if not query.strip().upper().startswith("SELECT"):
                return {
                    "success": False,
                    "error": "Only SELECT queries are supported",
                }

            # Add LIMIT if not present
            if "LIMIT" not in query.upper():
                test_query = query.rstrip(";") + " LIMIT 1;"
            else:
                test_query = query

            logger.debug(f"Validating query: {test_query}")

            result = await self.execute_query(test_query, timeout=5)

            return {
                "success": result.get("success"),
                "error": result.get("error") if not result.get("success") else None,
                "query": query,
            }

        except Exception as e:
            logger.error(f"Error validating query: {e}")
            return {"success": False, "error": str(e), "query": query}
