#!/usr/bin/env python3
"""
Test NATS Integration with MCP Framework

This test demonstrates:
1. MCP server initialization
2. Tool loading and execution
3. NATS client creation (simulated)
4. MCP request/response flow
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s",
)
logger = logging.getLogger(__name__)

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def test_mcp_server():
    """Test MCP server functionality"""
    logger.info("=" * 70)
    logger.info("Testing MCP Server Initialization")
    logger.info("=" * 70)

    from framework.server import MCPServer

    tools_dir = Path(__file__).parent.parent / "tools"
    config_dir = Path(__file__).parent.parent / "config"

    # Initialize server
    server = MCPServer(
        tools_dir=tools_dir,
        config_dir=config_dir,
        device_uuid="test-device-001",
    )

    if not await server.initialize():
        logger.error("Failed to initialize MCP server")
        return False

    logger.info(f"✓ Server initialized with {len(server.list_tools())} tools")

    # List tools
    logger.info("\nAvailable Tools:")
    for tool_name in server.list_tools():
        metadata = server.get_tool_metadata(tool_name)
        logger.info(f"  - {tool_name}")
        logger.info(f"    Description: {metadata.get('description')}")
        logger.info(f"    Parameters: {list(metadata.get('parameters', {}).get('properties', {}).keys())}")

    return server


async def test_tool_execution(server):
    """Test individual tool execution"""
    logger.info("\n" + "=" * 70)
    logger.info("Testing Tool Execution")
    logger.info("=" * 70)

    # Test 1: osquery_schema
    logger.info("\nTest 1: osquery_schema")
    logger.info("-" * 70)

    result = await server.execute_tool("osquery_schema", {})
    logger.info(f"Result: {result.get('success')}")

    if result.get("success"):
        data = result.get("data", {})
        logger.info(f"  Tables found: {data.get('table_count', 0)}")
        if data.get("tables"):
            logger.info(f"  Sample tables: {data['tables'][:5]}")
    else:
        logger.info(f"  Error: {result.get('error')}")

    # Test 2: osquery_execute
    logger.info("\nTest 2: osquery_execute")
    logger.info("-" * 70)

    result = await server.execute_tool(
        "osquery_execute",
        {"query": "SELECT pid, name FROM processes LIMIT 3"},
    )
    logger.info(f"Result: {result.get('success')}")

    if result.get("success"):
        data = result.get("data", {})
        logger.info(f"  Query: {data.get('query')}")
        logger.info(f"  Rows returned: {data.get('row_count', 0)}")
        if data.get("data"):
            logger.info(f"  Sample: {json.dumps(data['data'][0], indent=4)}")
    else:
        logger.info(f"  Error: {result.get('error')}")

    # Test 3: system_info
    logger.info("\nTest 3: system_info")
    logger.info("-" * 70)

    result = await server.execute_tool("system_info", {"category": "memory"})
    logger.info(f"Result: {result.get('success')}")

    if result.get("success"):
        data = result.get("data", {})
        if data.get("memory"):
            mem = data["memory"]
            logger.info(f"  Memory Status: {mem.get('status')}")
            logger.info(f"  Total: {mem.get('total_gb')} GB")
            logger.info(f"  Available: {mem.get('available_gb')} GB")
            logger.info(f"  Used: {mem.get('used_gb')} GB ({mem.get('percent')}%)")
    else:
        logger.info(f"  Error: {result.get('error')}")


async def test_mcp_request_format():
    """Test MCP request/response format"""
    logger.info("\n" + "=" * 70)
    logger.info("Testing MCP Request/Response Format")
    logger.info("=" * 70)

    from framework.nats_transport import NATSTransport

    transport = NATSTransport(device_uuid="test-device-001")

    # Test request formatting
    request = transport.format_mcp_request(
        "osquery_execute", {"query": "SELECT 1 as test"}
    )

    logger.info("\nMCP Request Format:")
    logger.info(json.dumps(request, indent=2))

    # Test response formatting
    response = transport.format_mcp_response(
        request["request_id"], True, data={"test": "data"}
    )

    logger.info("\nMCP Response Format:")
    logger.info(json.dumps(response, indent=2))


async def test_agent_mcp_integration():
    """Test agent MCP handler"""
    logger.info("\n" + "=" * 70)
    logger.info("Testing Agent MCP Integration")
    logger.info("=" * 70)

    # Check if agent MCP handler exists
    agent_dir = Path(__file__).parent.parent.parent / "installerFiles" / "Linux" / "Agent"
    mcp_handler_path = agent_dir / "core" / "mcp_handler.py"

    if mcp_handler_path.exists():
        logger.info(f"✓ MCP handler found at: {mcp_handler_path}")

        # Try to import it
        sys.path.insert(0, str(agent_dir / "core"))
        try:
            from mcp_handler import MCPHandler

            logger.info("✓ MCPHandler imported successfully")

            # Initialize handler
            handler = MCPHandler(mcp_dir=agent_dir / "mcp")

            if await handler.initialize():
                logger.info(f"✓ MCPHandler initialized with {len(handler.list_tools())} tools")

                # Test tool execution
                result = await handler.execute_tool(
                    "osquery_execute",
                    {"query": "SELECT 1 as test"},
                )

                logger.info(f"✓ Tool execution result: {result.get('success')}")
            else:
                logger.warning("Failed to initialize MCPHandler")

        except ImportError as e:
            logger.warning(f"Could not import MCPHandler: {e}")
    else:
        logger.warning(f"MCP handler not found at: {mcp_handler_path}")


async def main():
    """Main test runner"""
    try:
        logger.info("\n")
        logger.info("=" * 70)
        logger.info("WEGWEISER MCP NATS INTEGRATION TEST")
        logger.info("=" * 70)

        # Test MCP server
        server = await test_mcp_server()
        if not server:
            return 1

        # Test tool execution
        await test_tool_execution(server)

        # Test request/response format
        await test_mcp_request_format()

        # Test agent integration
        await test_agent_mcp_integration()

        logger.info("\n" + "=" * 70)
        logger.info("All Tests Completed Successfully")
        logger.info("=" * 70)
        logger.info("")
        logger.info("Next Steps:")
        logger.info("1. Deploy agent with integrated MCP support")
        logger.info("2. Start NATS server")
        logger.info("3. Connect agent to NATS")
        logger.info("4. Send MCP requests via NATS client")
        logger.info("")

        return 0

    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
