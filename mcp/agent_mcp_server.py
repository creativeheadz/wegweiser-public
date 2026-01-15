#!/usr/bin/env python3
"""
MCP Server for Wegweiser Agent - Standalone testing

This runs the MCP framework as a standalone server that can handle
tool execution requests (initially via local function calls, later via NATS)
"""

import asyncio
import logging
import sys
from pathlib import Path

# Setup path
sys.path.insert(0, str(Path(__file__).parent))

from framework.server import MCPServer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """Main entry point"""
    try:
        mcp_dir = Path(__file__).parent

        logger.info("=" * 70)
        logger.info("Wegweiser MCP Server Starting")
        logger.info("=" * 70)

        # Initialize MCP server
        server = MCPServer(
            tools_dir=mcp_dir / "tools",
            config_dir=mcp_dir / "config",
            device_uuid="local-test-device",
        )

        # Initialize server
        if not await server.initialize():
            logger.error("Failed to initialize MCP server")
            return 1

        logger.info(f"Initialized with {len(server.list_tools())} tools")
        logger.info(f"Available tools: {', '.join(server.list_tools())}")
        logger.info("")

        # Demo: Test the tools
        logger.info("=" * 70)
        logger.info("Running MCP Tool Demonstrations")
        logger.info("=" * 70)
        logger.info("")

        # Demo 1: Schema Discovery
        logger.info("Demo 1: osquery_schema (discover osquery tables)")
        logger.info("-" * 70)
        result = await server.execute_tool("osquery_schema", {})
        if result.get("success"):
            data = result.get("data", {})
            tables = data.get("tables", [])
            logger.info(f"✓ Success! Found {len(tables)} tables")
            logger.info(f"  First 10 tables: {tables[:10]}")
        else:
            logger.warning(f"✗ Failed: {result.get('error')}")
        logger.info("")

        # Demo 2: Query Executor
        logger.info("Demo 2: osquery_execute (run a simple query)")
        logger.info("-" * 70)
        result = await server.execute_tool(
            "osquery_execute",
            {
                "query": "SELECT name FROM sqlite_master WHERE type='table' LIMIT 5;",
                "timeout": 10,
            },
        )
        if result.get("success"):
            data = result.get("data", {})
            row_count = data.get("row_count", 0)
            logger.info(f"✓ Success! Retrieved {row_count} rows")
            if data.get("data"):
                logger.info(f"  First row: {data['data'][0]}")
        else:
            logger.warning(f"✗ Failed: {result.get('error')}")
        logger.info("")

        logger.info("=" * 70)
        logger.info("MCP Server Ready")
        logger.info("=" * 70)
        logger.info("")
        logger.info("Server running in standalone mode.")
        logger.info("To integrate with NATS, see: /opt/wegweiser/mcp/README.md")
        logger.info("")

        # Keep server running
        logger.info("Press Ctrl+C to stop...")
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("Shutting down...")

        return 0

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
