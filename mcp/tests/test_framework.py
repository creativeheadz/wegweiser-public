"""
Tests for MCP Framework core functionality
"""

import pytest
import asyncio
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from framework.config import ConfigManager
from framework.tool_registry import ToolRegistry
from framework.server import MCPServer
from framework.base_tool import MCPTool


class DummyTool(MCPTool):
    """Dummy tool for testing"""

    def get_metadata(self):
        return {
            "name": "dummy_tool",
            "description": "A dummy tool for testing",
            "parameters": {
                "type": "object",
                "properties": {"test_param": {"type": "string"}},
                "required": ["test_param"],
            },
        }

    async def execute(self, parameters):
        return {
            "success": True,
            "data": {"echo": parameters.get("test_param")},
        }


def test_config_manager():
    """Test configuration manager"""
    config_dir = Path(__file__).parent.parent / "config"
    config = ConfigManager(config_dir)

    assert config.get("enabled_tools") is not None
    print("✓ Config manager loads configuration")


def test_tool_registry():
    """Test tool registry"""
    tools_dir = Path(__file__).parent.parent / "tools"
    config_dir = Path(__file__).parent.parent / "config"

    config = ConfigManager(config_dir)
    registry = ToolRegistry(tools_dir, config.config)

    # Discover tools
    success = registry.discover_and_load()
    assert success, "Tool discovery should succeed"
    assert len(registry.tools) > 0, "Should have loaded at least one tool"

    print(f"✓ Tool registry discovered {len(registry.tools)} tools")
    print(f"  Loaded tools: {list(registry.tools.keys())}")


@pytest.mark.asyncio
async def test_mcp_server_init():
    """Test MCP server initialization"""
    tools_dir = Path(__file__).parent.parent / "tools"
    config_dir = Path(__file__).parent.parent / "config"

    server = MCPServer(tools_dir=tools_dir, config_dir=config_dir)
    success = await server.initialize()

    assert success, "Server initialization should succeed"
    assert len(server.list_tools()) > 0, "Should have loaded tools"

    print(f"✓ MCP server initialized with {len(server.list_tools())} tools")


@pytest.mark.asyncio
async def test_osquery_schema_tool():
    """Test osquery schema discovery tool"""
    tools_dir = Path(__file__).parent.parent / "tools"
    config_dir = Path(__file__).parent.parent / "config"

    server = MCPServer(tools_dir=tools_dir, config_dir=config_dir)
    await server.initialize()

    # Execute schema discovery
    result = await server.execute_tool("osquery_schema", {})

    print(f"✓ osquery_schema tool executed")
    print(f"  Result: {result.get('success')}")

    if result.get("success"):
        data = result.get("data", {})
        table_count = data.get("table_count", 0)
        print(f"  Tables discovered: {table_count}")


@pytest.mark.asyncio
async def test_osquery_query_tool():
    """Test osquery query executor tool"""
    tools_dir = Path(__file__).parent.parent / "tools"
    config_dir = Path(__file__).parent.parent / "config"

    server = MCPServer(tools_dir=tools_dir, config_dir=config_dir)
    await server.initialize()

    # Execute a simple query
    result = await server.execute_tool(
        "osquery_execute",
        {"query": "SELECT name FROM sqlite_master WHERE type='table' LIMIT 5;"},
    )

    print(f"✓ osquery_execute tool executed")
    print(f"  Result: {result.get('success')}")

    if result.get("success"):
        data = result.get("data", {})
        row_count = data.get("row_count", 0)
        print(f"  Rows returned: {row_count}")


def test_tool_metadata():
    """Test that tools expose proper metadata"""
    tools_dir = Path(__file__).parent.parent / "tools"
    config_dir = Path(__file__).parent.parent / "config"

    config = ConfigManager(config_dir)
    registry = ToolRegistry(tools_dir, config.config)
    registry.discover_and_load()

    for tool_name, metadata in registry.list_tools().items():
        print(f"✓ Tool: {tool_name}")
        print(f"  Description: {metadata.get('description')}")
        print(f"  Parameters: {list(metadata.get('parameters', {}).get('properties', {}).keys())}")


if __name__ == "__main__":
    print("\n=== MCP Framework Tests ===\n")

    print("1. Testing Configuration Manager...")
    test_config_manager()

    print("\n2. Testing Tool Registry...")
    test_tool_registry()

    print("\n3. Testing MCP Server Initialization...")
    asyncio.run(test_mcp_server_init())

    print("\n4. Testing osquery Schema Tool...")
    asyncio.run(test_osquery_schema_tool())

    print("\n5. Testing osquery Query Tool...")
    asyncio.run(test_osquery_query_tool())

    print("\n6. Testing Tool Metadata...")
    test_tool_metadata()

    print("\n=== Tests Complete ===\n")
