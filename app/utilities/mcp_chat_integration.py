# Filepath: app/utilities/mcp_chat_integration.py

import asyncio
import json
import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.utilities.app_logging_helper import log_with_route
# WebSocket functionality temporarily disabled
# from app.routes.ws.agent_endpoint import (
#     mcp_handler,
#     connection_registry,
#     get_available_mcp_tools,
#     send_mcp_request_to_agent,
#     get_mcp_request_status
# )

class MCPChatIntegration:
    """Integration layer for using MCP tools in AI chat conversations"""
    
    def __init__(self):
        self.request_timeout = 30  # seconds
        self.max_retries = 3
    
    def is_osquery_request(self, message: str) -> bool:
        """Check if a chat message is requesting osquery functionality"""
        osquery_keywords = [
            'osquery', 'sql query', 'system query', 'database query',
            'processes', 'memory usage', 'disk usage', 'network connections',
            'running services', 'installed software', 'system information',
            'logged in users', 'file system', 'registry', 'hardware info'
        ]
        
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in osquery_keywords)
    
    def extract_device_preference(self, message: str, available_devices: List[str]) -> Optional[str]:
        """Extract device preference from chat message"""
        message_lower = message.lower()
        
        # Look for device UUID mentions
        for device_uuid in available_devices:
            if device_uuid.lower() in message_lower:
                return device_uuid
        
        # Look for device name patterns
        device_patterns = ['on device', 'from device', 'device:', 'machine:', 'server:', 'host:']
        for pattern in device_patterns:
            if pattern in message_lower:
                # Extract the text after the pattern
                parts = message_lower.split(pattern, 1)
                if len(parts) > 1:
                    device_hint = parts[1].strip().split()[0]
                    # Try to match with available devices
                    for device_uuid in available_devices:
                        if device_hint in device_uuid.lower():
                            return device_uuid
        
        return None
    
    def suggest_osquery_from_natural_language(self, message: str) -> Dict[str, Any]:
        """Suggest osquery queries based on natural language"""
        message_lower = message.lower()
        suggestions = []
        
        if any(word in message_lower for word in ['process', 'running', 'task', 'pid']):
            suggestions.append({
                'tool': 'osquery_execute',
                'description': 'Get running processes',
                'parameters': {'sql': "SELECT pid, name, cmdline, cpu_time FROM processes WHERE state='R' LIMIT 20"}
            })
        
        if any(word in message_lower for word in ['memory', 'ram', 'usage']):
            suggestions.append({
                'tool': 'system_info',
                'description': 'Get memory information',
                'parameters': {'category': 'hardware'}
            })
        
        if any(word in message_lower for word in ['network', 'connection', 'port', 'socket']):
            suggestions.append({
                'tool': 'osquery_execute',
                'description': 'Get network connections',
                'parameters': {'sql': "SELECT * FROM listening_ports"}
            })
        
        if any(word in message_lower for word in ['user', 'login', 'account']):
            suggestions.append({
                'tool': 'osquery_execute',
                'description': 'Get logged in users',
                'parameters': {'sql': "SELECT * FROM logged_in_users"}
            })
        
        if any(word in message_lower for word in ['service', 'daemon', 'systemd']):
            suggestions.append({
                'tool': 'osquery_execute',
                'description': 'Get running services',
                'parameters': {'sql': "SELECT * FROM services WHERE status='RUNNING'"}
            })
        
        if any(word in message_lower for word in ['software', 'program', 'application', 'installed']):
            suggestions.append({
                'tool': 'osquery_execute',
                'description': 'Get installed programs',
                'parameters': {'sql': "SELECT name, version, install_date FROM programs LIMIT 20"}
            })
        
        if any(word in message_lower for word in ['hardware', 'cpu', 'system info', 'specs']):
            suggestions.append({
                'tool': 'system_info',
                'description': 'Get comprehensive system information',
                'parameters': {'category': 'all'}
            })
        
        if not suggestions:
            # Default suggestion
            suggestions.append({
                'tool': 'osquery_suggest',
                'description': 'Get query suggestions based on your request',
                'parameters': {'description': message}
            })
        
        return {
            'suggestions': suggestions,
            'message': message
        }
    
    async def execute_mcp_tool_async(self, device_uuid: str, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an MCP tool asynchronously and wait for response"""
        try:
            # WebSocket functionality temporarily disabled
            return {
                'error': 'MCP functionality is currently disabled (WebSocket not available)',
                'device_uuid': device_uuid,
                'tool_name': tool_name
            }
        
        except Exception as e:
            log_with_route(logging.ERROR, f"Error executing MCP tool {tool_name} on {device_uuid}: {e}")
            return {
                'error': str(e),
                'device_uuid': device_uuid,
                'tool_name': tool_name
            }
    
    def execute_mcp_tool_sync(self, device_uuid: str, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an MCP tool synchronously (for use in non-async contexts)"""
        try:
            # Create new event loop if none exists
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Run the async function
            return loop.run_until_complete(
                self.execute_mcp_tool_async(device_uuid, tool_name, parameters)
            )
        
        except Exception as e:
            log_with_route(logging.ERROR, f"Error in sync MCP tool execution: {e}")
            return {
                'error': str(e),
                'device_uuid': device_uuid,
                'tool_name': tool_name
            }
    
    def get_connected_devices_with_mcp(self) -> List[Dict[str, Any]]:
        """Get list of connected devices that have MCP tools available"""
        try:
            # WebSocket functionality temporarily disabled
            log_with_route(logging.WARNING, "MCP functionality is currently disabled (WebSocket not available)")
            return []

        except Exception as e:
            log_with_route(logging.ERROR, f"Error getting connected devices with MCP: {e}")
            return []
    
    def format_mcp_response_for_chat(self, response: Dict[str, Any]) -> str:
        """Format MCP response for display in chat"""
        try:
            if response.get('error'):
                return f"❌ **Error**: {response['error']}"
            
            if not response.get('success'):
                return "❌ **Error**: Request failed"
            
            tool_name = response.get('tool_name', 'unknown')
            device_uuid = response.get('device_uuid', 'unknown')
            execution_time = response.get('execution_time', 0)
            
            result_data = response.get('response', {})
            
            # Format based on tool type
            if tool_name == 'osquery_execute':
                return self._format_osquery_result(result_data, device_uuid, execution_time)
            elif tool_name == 'system_info':
                return self._format_system_info_result(result_data, device_uuid, execution_time)
            elif tool_name == 'osquery_suggest':
                return self._format_osquery_suggestions(result_data, device_uuid)
            elif tool_name == 'osquery_schema':
                return self._format_schema_result(result_data, device_uuid)
            else:
                # Generic formatting
                return f"✅ **{tool_name}** completed on device `{device_uuid[:8]}...`\n\n```json\n{json.dumps(result_data, indent=2)}\n```"
        
        except Exception as e:
            log_with_route(logging.ERROR, f"Error formatting MCP response: {e}")
            return f"❌ **Error formatting response**: {str(e)}"
    
    def _format_osquery_result(self, result: Dict[str, Any], device_uuid: str, execution_time: float) -> str:
        """Format osquery execution result"""
        if result.get('error'):
            return f"❌ **osquery Error** on `{device_uuid[:8]}...`: {result['error']}"
        
        query = result.get('query', 'Unknown query')
        data = result.get('result', [])
        row_count = result.get('row_count', len(data) if isinstance(data, list) else 0)
        
        formatted = f"✅ **osquery Result** from device `{device_uuid[:8]}...`\n"
        formatted += f"**Query**: `{query}`\n"
        formatted += f"**Rows**: {row_count} | **Time**: {execution_time:.2f}s\n\n"
        
        if isinstance(data, list) and data:
            # Show first few rows in a table format
            if len(data) > 0:
                # Get column names from first row
                columns = list(data[0].keys()) if data[0] else []
                
                # Limit columns for readability
                if len(columns) > 5:
                    columns = columns[:5]
                    show_truncated = True
                else:
                    show_truncated = False
                
                # Create table header
                formatted += "| " + " | ".join(columns) + " |\n"
                formatted += "|" + "|".join([" --- " for _ in columns]) + "|\n"
                
                # Add rows (limit to first 10)
                for i, row in enumerate(data[:10]):
                    row_values = []
                    for col in columns:
                        value = str(row.get(col, ''))
                        # Truncate long values
                        if len(value) > 30:
                            value = value[:27] + "..."
                        row_values.append(value)
                    formatted += "| " + " | ".join(row_values) + " |\n"
                
                if len(data) > 10:
                    formatted += f"\n*... and {len(data) - 10} more rows*"
                
                if show_truncated:
                    formatted += f"\n*... and {len(list(data[0].keys())) - 5} more columns*"
        else:
            formatted += "*No results returned*"
        
        return formatted
    
    def _format_system_info_result(self, result: Dict[str, Any], device_uuid: str, execution_time: float) -> str:
        """Format system info result"""
        if result.get('error'):
            return f"❌ **System Info Error** on `{device_uuid[:8]}...`: {result['error']}"
        
        category = result.get('category', 'unknown')
        system_info = result.get('system_info', {})
        
        formatted = f"✅ **System Information** from device `{device_uuid[:8]}...`\n"
        formatted += f"**Category**: {category} | **Time**: {execution_time:.2f}s\n\n"
        
        for cat_name, cat_data in system_info.items():
            formatted += f"### {cat_name.title()}\n"
            for table_name, table_data in cat_data.items():
                if isinstance(table_data, list) and table_data:
                    formatted += f"**{table_name}**: {len(table_data)} entries\n"
                    # Show summary of first entry
                    if table_data[0]:
                        sample_keys = list(table_data[0].keys())[:3]
                        sample_values = [str(table_data[0].get(key, ''))[:20] for key in sample_keys]
                        formatted += f"  Sample: {', '.join([f'{k}: {v}' for k, v in zip(sample_keys, sample_values)])}\n"
                else:
                    formatted += f"**{table_name}**: No data\n"
            formatted += "\n"
        
        return formatted
    
    def _format_osquery_suggestions(self, result: Dict[str, Any], device_uuid: str) -> str:
        """Format osquery suggestions"""
        suggestions = result.get('suggestions', [])
        description = result.get('description', '')
        
        formatted = f"💡 **osquery Suggestions** for device `{device_uuid[:8]}...`\n"
        formatted += f"**Your request**: {description}\n\n"
        
        for i, suggestion in enumerate(suggestions, 1):
            query = suggestion.get('query', '')
            desc = suggestion.get('description', '')
            formatted += f"{i}. **{desc}**\n"
            formatted += f"   ```sql\n   {query}\n   ```\n\n"
        
        return formatted
    
    def _format_schema_result(self, result: Dict[str, Any], device_uuid: str) -> str:
        """Format schema result"""
        if result.get('error'):
            return f"❌ **Schema Error** on `{device_uuid[:8]}...`: {result['error']}"
        
        table_name = result.get('table_name', 'all tables')
        schema = result.get('schema', [])
        
        formatted = f"📋 **osquery Schema** from device `{device_uuid[:8]}...`\n"
        formatted += f"**Table**: {table_name}\n\n"
        
        if isinstance(schema, list) and schema:
            formatted += "| Column | Type | Description |\n"
            formatted += "|--------|------|-------------|\n"
            for col in schema[:20]:  # Limit to first 20 columns
                name = col.get('name', '')
                col_type = col.get('type', '')
                formatted += f"| {name} | {col_type} | - |\n"
            
            if len(schema) > 20:
                formatted += f"\n*... and {len(schema) - 20} more columns*"
        else:
            formatted += "*No schema information available*"
        
        return formatted

# Global instance
mcp_chat = MCPChatIntegration()
