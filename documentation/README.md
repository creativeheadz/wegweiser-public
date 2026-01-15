# Wegweiser MCP Framework

**Extensible Model Context Protocol (MCP) Server for Wegweiser Agents**

An intelligent, plugin-based framework that enables Wegweiser managed endpoints to expose system capabilities (osquery, system info, etc.) as MCP tools that can be accessed via AI chat and automated workflows.

## Overview

The MCP Framework transforms how MSPs interact with managed endpoints:

- **osquery Tool Suite**: Discover and execute osquery SQL queries dynamically
- **System Info Tools**: Collect CPU, memory, disk, and uptime information
- **Extensible Architecture**: Add new tools without modifying core framework
- **Configuration-Driven**: Enable/disable tools per environment via YAML
- **NATS-Ready**: Designed for NATS message bus integration

## Architecture

```
┌─────────────────────────────────────────────────┐
│         MCP Framework (Framework Agnostic)      │
├─────────────────────────────────────────────────┤
│ • Tool Registry (auto-discovery)                │
│ • Base Tool Interface                           │
│ • NATS Transport Layer                          │
│ • Configuration Management                      │
└─────────────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────────────┐
│              Tool Plugins                       │
├──────────────────┬──────────────────────────────┤
│   osquery/       │       system/                 │
│ • schema_...    │    • system_info              │
│ • query_exe...  │    (easily extend)            │
│   (2 tools)     │    (easily extend)            │
└──────────────────┴──────────────────────────────┘
```

## Project Structure

```
/opt/wegweiser/mcp/
├── framework/                  # Core framework (immutable)
│   ├── base_tool.py           # Abstract tool interface
│   ├── tool_registry.py       # Auto-discovery engine
│   ├── server.py              # MCP server orchestrator
│   ├── nats_transport.py      # NATS integration
│   └── config.py              # Configuration loader
│
├── tools/                      # Tool plugins (extensible)
│   ├── osquery/               # osquery tool suite
│   │   ├── manifest.json      # Tool definitions
│   │   ├── schema_discovery.py
│   │   ├── query_executor.py
│   │   └── osquery_client.py
│   └── system/                # System info tools
│       ├── manifest.json
│       └── system_info.py
│
├── config/                     # Configuration
│   ├── tools.yaml             # Tool settings
│   └── server.yaml            # Server settings
│
├── client/                     # C2-side client
│   └── mcp_client.py          # (Future)
│
├── tests/                      # Test suite
│   └── test_framework.py
│
├── agent_mcp_server.py        # Standalone server
└── README.md                   # This file
```

## Available Tools

### osquery Suite

**osquery_schema** - Discover available osquery tables and their schemas
- Parameters: `table_name` (optional, string)
- Returns: List of available tables or detailed schema for a specific table

**osquery_execute** - Execute osquery SQL queries
- Parameters: `query` (required, string), `timeout` (optional, int, 1-300)
- Returns: Query results as JSON array

### system Suite

**system_info** - Get system information
- Parameters: `category` (optional: 'cpu', 'memory', 'disk', 'uptime', 'all')
- Returns: System metrics (CPU percent, memory GB, disk usage, uptime)

## Quick Start

### 1. Run Standalone Server (Testing)

```bash
cd /opt/wegweiser/mcp
python3 agent_mcp_server.py
```

Output shows:
- Framework initialization
- Tools loaded
- Demo executions
- Ready message

### 2. Test Tools Programmatically

```python
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, '/opt/wegweiser/mcp')
from framework.server import MCPServer

async def test():
    server = MCPServer()
    await server.initialize()

    # Execute osquery tool
    result = await server.execute_tool('osquery_execute', {
        'query': 'SELECT pid, name FROM processes LIMIT 5'
    })
    print(result)

    # Execute system tool
    result = await server.execute_tool('system_info', {
        'category': 'memory'
    })
    print(result)

asyncio.run(test())
```

## Extending with New Tools

### Step 1: Create Tool Directory

```bash
mkdir -p /opt/wegweiser/mcp/tools/my_tool
```

### Step 2: Create manifest.json

```json
{
  "name": "my_tool",
  "version": "1.0.0",
  "description": "My custom tool",
  "tools": [
    {
      "module": "my_tool_impl:MyTool",
      "name": "my_tool_action",
      "description": "What this tool does",
      "parameters": {
        "type": "object",
        "properties": {
          "param1": {
            "type": "string",
            "description": "First parameter"
          }
        },
        "required": ["param1"]
      }
    }
  ],
  "platforms": ["linux", "windows", "darwin"]
}
```

### Step 3: Implement Tool Class

Create `/opt/wegweiser/mcp/tools/my_tool/my_tool_impl.py`:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from framework.base_tool import MCPTool

class MyTool(MCPTool):
    def get_metadata(self):
        return {
            "name": "my_tool_action",
            "description": "What this tool does",
            "parameters": {...}
        }

    async def execute(self, parameters):
        try:
            param1 = parameters.get('param1')
            # Do work here
            result = "some result"
            return {
                "success": True,
                "data": {"result": result}
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
```

### Step 4: Enable Tool

Edit `/opt/wegweiser/mcp/config/tools.yaml`:

```yaml
enabled_tools:
  - osquery
  - system
  - my_tool  # Add this
```

### Step 5: Test

```bash
python3 agent_mcp_server.py  # Should show 3 tools loaded
```

## Configuration

### tools.yaml

```yaml
enabled_tools:
  - osquery     # Enable/disable tools
  - system

osquery:
  timeout: 30
  max_results: 1000
```

### server.yaml

```yaml
logging:
  level: INFO

nats:
  enabled: true
  subject_prefix: "mcp"
  request_timeout: 30

execution:
  max_concurrent_tools: 10
  default_timeout: 30
  max_timeout: 300
```

## Integration Points

### With Wegweiser Agents

The MCP server can be integrated into Wegweiser agents by:

1. Copying `/opt/wegweiser/mcp/` to agent installer
2. Initializing MCPServer in agent startup
3. Registering NATS message handlers for MCP requests
4. Handling MCP responses and returning via NATS

### With AI Chat

The C2 server's AI chat system can:

1. Discover available tools via MCP server
2. Use tool metadata to understand capabilities
3. Invoke tools via NATS messaging
4. Display results to users

## How to Test Extensibility

The system info tool demonstrates extensibility:

1. **Without changing framework**: Added new tool directory and manifest
2. **Auto-discovery works**: Framework automatically found and loaded it
3. **Tool execution works**: Framework routes requests to new tool
4. **Configuration-driven**: Tool can be disabled by removing from `enabled_tools`

```bash
# Test all 3 tools (osquery_schema, osquery_execute, system_info)
python3 -c "
import sys, asyncio
sys.path.insert(0, '/opt/wegweiser/mcp')
from framework.server import MCPServer
from pathlib import Path

async def test():
    server = MCPServer()
    await server.initialize()
    print('Loaded tools:', server.list_tools())

    # Each tool works independently
    for tool in server.list_tools():
        print(f'  - {tool}')

asyncio.run(test())
"
```

## Benefits of This Architecture

### 1. **Zero Framework Coupling**
New tools don't require framework changes. Each tool is independent.

### 2. **Self-Contained Modules**
Each tool has its own:
- Implementation file(s)
- Manifest with metadata
- Dependencies declared
- Platform support declared

### 3. **Configuration-Driven**
Enable/disable tools without code changes. Perfect for:
- Different environments (dev/prod)
- Client-specific capabilities
- Performance tuning

### 4. **Easy to Test**
Each tool can be tested independently:

```bash
# Create test_my_tool.py
python3 -m pytest test_my_tool.py
```

### 5. **Versioning Support**
Tools can be versioned independently and upgraded separately.

### 6. **Platform-Specific**
Tools declare which platforms they support. Framework skips unavailable tools.

## Roadmap

**Phase 1** ✓ - osquery tools (query discovery & execution)
**Phase 2** ✓ - System info tools (CPU, memory, disk, uptime)
**Phase 3** - Event log tools (Windows Event Log, Linux audit)
**Phase 4** - Security tools (vulnerability scanning, patch status)
**Phase 5** - Remediation tools (service restart, process kill, file operations)
**Phase 6** - Custom scripting tool (execute PowerShell/Python snippets)

Each phase is just a new directory under `tools/` with a manifest and implementation.

## Future Enhancements

- [ ] Hot-reload: Add/update tools without restarting agent
- [ ] Tool versioning: Support multiple versions of same tool
- [ ] Dependency management: Auto-install missing Python packages
- [ ] Tool sandboxing: Run tools in isolated environments
- [ ] Performance monitoring: Track tool execution times
- [ ] Caching layer: Cache frequently executed queries
- [ ] Tool composition: Build complex workflows from simple tools

## Testing

Run the test suite:

```bash
cd /opt/wegweiser/mcp
python3 tests/test_framework.py
```

Output shows:
- Framework initialization
- Tool discovery
- Tool execution
- Results from osquery and system tools

## Troubleshooting

### Tools not loading

Check logs:
```bash
python3 agent_mcp_server.py 2>&1 | grep "ERROR\|WARN"
```

Common issues:
- Missing manifest.json
- Incorrect module:class in manifest
- Import errors in tool implementation
- Tool not in `enabled_tools` list

### Tool execution fails

Enable debug logging:
```yaml
# In config/server.yaml
logging:
  level: DEBUG
```

Check specific tool:
```python
server = MCPServer()
await server.initialize()
tool = server.get_tool('tool_name')
print(tool.get_metadata())
```

## References

- **MCP Specification**: https://modelcontextprotocol.io
- **NATS Documentation**: https://docs.nats.io
- **osquery Documentation**: https://osquery.io

## License

Part of Wegweiser MSP Platform
