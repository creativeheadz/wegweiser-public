"""
osquery tools for MCP framework
"""

from .schema_discovery import SchemaDiscovery
from .query_executor import QueryExecutor

__all__ = ["SchemaDiscovery", "QueryExecutor"]
