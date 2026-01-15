# Filepath: nats_persistent_agent.py
"""
Wegweiser NATS Persistent Agent
Secure, tenant-aware agent with RPC capabilities and on-demand streaming
"""

import os
import sys
import json
import asyncio
import logging
import platform
import time
import subprocess
import shutil
import psutil
from datetime import datetime
from typing import Dict, Any, Optional, List
import uuid

# Third-party imports (installed via bundled pip)
try:
    import nats
    from nats.errors import TimeoutError as NATSTimeoutError
    import aiohttp
except ImportError as e:
    print(f"Required library not found: {e}")
    print("Please ensure all dependencies are installed via requirements.txt")
    sys.exit(1)

class WegweiserNATSAgent:
    """Secure NATS-based Wegweiser agent with RPC and streaming capabilities"""
    
    def __init__(self):
        self.config = None
        self.nc = None  # NATS connection
        self.device_uuid = None
        self.tenant_uuid = None
        self.server_url = None
        self.nats_server = None
        self.session_id = str(uuid.uuid4())
        
        # Tool registry
        self.tools = {
            'osquery': self._handle_osquery,
            'psutil_info': self._handle_psutil_info,
            'system_info': self._handle_system_info,
            'ping': self._handle_ping
        }
        
        # Streaming state
        self.streaming_active = False
        self.streaming_metrics = []
        self.streaming_interval = 2.0
        self.streaming_task = None
        
        # Setup paths and logging
        self._setup_paths()
        self._setup_logging()
        
    def _setup_paths(self):
        """Setup directory paths with fallbacks"""
        if hasattr(sys, 'frozen'):
            application_path = os.path.dirname(sys.executable)
        else:
            application_path = os.path.dirname(os.path.abspath(__file__))
        
        # Check if we're in Scripts directory
        base_dir = None
        if os.path.basename(os.path.dirname(application_path)).lower() == 'scripts':
            base_dir = os.path.dirname(os.path.dirname(application_path))
        else:
            base_dir = os.path.dirname(application_path)
        
        # Fallback to Program Files paths
        if not os.path.exists(os.path.join(base_dir, 'Config')):
            potential_paths = [
                r'C:\Program Files (x86)\Wegweiser',
                r'C:\Program Files\Wegweiser',
                r'C:\Wegweiser'
            ]
            for path in potential_paths:
                if os.path.exists(os.path.join(path, 'Config')):
                    base_dir = path
                    break
        
        self.base_dir = base_dir
        self.log_dir = os.path.join(base_dir, 'Logs')
        self.config_dir = os.path.join(base_dir, 'Config')
        
        # Ensure directories exist
        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(self.config_dir, exist_ok=True)
        
    def _setup_logging(self):
        """Setup logging configuration"""
        log_file = os.path.join(self.log_dir, 'nats_agent.log')
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        self.logger.info(f"NATS Agent initialized at {datetime.now()}")
        self.logger.info(f"Agent session ID: {self.session_id}")
        self.logger.info(f"Running from {os.path.dirname(os.path.abspath(__file__))}")
        self.logger.info(f"Base directory: {self.base_dir}")
        self.logger.info(f"Config directory: {self.config_dir}")
        
    def load_config(self):
        """Load agent configuration from JSON file"""
        config_file = os.path.join(self.config_dir, 'agent.config')
        
        if not os.path.exists(config_file):
            self.logger.error(f"Configuration file not found: {config_file}")
            raise FileNotFoundError(f"Configuration file not found: {config_file}")
        
        try:
            with open(config_file, 'r') as f:
                self.config = json.load(f)
            
            # Extract required fields
            self.device_uuid = self.config.get('deviceuuid')
            self.server_url = self.config.get('server_url', 'app.wegweiser.tech')
            
            if not self.device_uuid:
                raise ValueError("Device UUID not found in configuration")
            
            self.logger.info("Configuration loaded successfully")
            self.logger.info(f"Device UUID: {self.device_uuid}")
            self.logger.info(f"Server URL: {self.server_url}")
            
        except Exception as e:
            self.logger.error(f"Error loading configuration: {str(e)}")
            raise
            
    async def get_tenant_info(self):
        """Get tenant information from server"""
        try:
            url = f"https://{self.server_url}/api/device/{self.device_uuid}/tenant"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.tenant_uuid = data.get('tenant_uuid')
                        self.nats_server = data.get('nats_server', 'tls://nats.wegweiser.tech:443')
                        
                        self.logger.info(f"Device UUID: {self.device_uuid}")
                        self.logger.info(f"Tenant UUID: {self.tenant_uuid}")
                        self.logger.info(f"NATS Server: {self.nats_server}")
                        
                        return True
                    else:
                        self.logger.error(f"Failed to get tenant info: HTTP {response.status}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"Error getting tenant info: {str(e)}")
            return False
            
    async def get_nats_credentials(self):
        """Get NATS credentials from server"""
        try:
            url = f"https://{self.server_url}/api/nats/device/{self.device_uuid}/credentials"

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data['credentials']
                    else:
                        self.logger.error(f"Failed to get NATS credentials: HTTP {response.status}")
                        return None

        except Exception as e:
            self.logger.error(f"Error getting NATS credentials: {str(e)}")
            return None

    async def connect_nats(self):
        """Connect to NATS server with TLS and authentication"""
        try:
            # Get NATS credentials
            credentials = await self.get_nats_credentials()
            if not credentials:
                self.logger.error("Failed to get NATS credentials")
                return False

            # Connect with credentials
            self.nc = await nats.connect(
                servers=[self.nats_server],
                user=credentials['username'],
                password=credentials['password'],
                name=f"wegweiser-agent-{self.device_uuid}",
                max_reconnect_attempts=10,
                reconnect_time_wait=2
            )

            self.logger.info("Connected to NATS server with credentials")
            return True

        except Exception as e:
            self.logger.error(f"Failed to connect to NATS: {str(e)}")
            return False
            
    async def setup_subscriptions(self):
        """Setup NATS subscriptions for commands (matching existing pattern)"""
        try:
            # Command subscription (matches existing agent pattern)
            cmd_subject = f"tenant.{self.tenant_uuid}.device.{self.device_uuid}.command"
            await self.nc.subscribe(cmd_subject, cb=self._handle_command)

            self.logger.info(f"Subscribed to commands: {cmd_subject}")

        except Exception as e:
            self.logger.error(f"Error setting up subscriptions: {str(e)}")
            raise
            
    async def _handle_command(self, msg):
        """Handle incoming command messages (matching existing agent pattern)"""
        try:
            data = json.loads(msg.data.decode())

            # Extract payload from NATS message wrapper (matching existing pattern)
            if 'payload' in data:
                payload = data['payload']
            else:
                payload = data

            command = payload.get('command')
            command_id = payload.get('command_id')
            parameters = payload.get('parameters', {})

            self.logger.info(f"Received command: {command} (ID: {command_id})")

            # Execute command
            if command in self.tools:
                self.logger.info(f"Executing tool: {command} with parameters: {parameters}")
                result = await self.tools[command](parameters)
                self.logger.info(f"Tool {command} completed successfully")
                response = {
                    'command_id': command_id,
                    'status': 'success',
                    'result': result,
                    'agent_version': '2.0.0-nats',
                    'timestamp': int(time.time() * 1000)
                }
            elif command == 'start_metrics':
                await self._start_streaming(payload)
                response = {
                    'command_id': command_id,
                    'status': 'success',
                    'result': {'message': 'Streaming started'}
                }
            elif command == 'stop_metrics':
                await self._stop_streaming()
                response = {
                    'command_id': command_id,
                    'status': 'success',
                    'result': {'message': 'Streaming stopped'}
                }
            else:
                response = {
                    'command_id': command_id,
                    'status': 'error',
                    'error': f'Unknown command: {command}',
                    'available_commands': list(self.tools.keys()) + ['start_metrics', 'stop_metrics']
                }

            # Send response via NATS (matching existing pattern)
            await self._send_command_response(command_id, response)

        except Exception as e:
            self.logger.error(f"Error handling command: {str(e)}")
            if 'command_id' in locals():
                error_response = {
                    'command_id': command_id,
                    'status': 'error',
                    'error': str(e)
                }
                await self._send_command_response(command_id, error_response)

    async def _send_command_response(self, command_id: str, result: dict):
        """Send command response via NATS (matching existing pattern)"""
        try:
            subject = f"tenant.{self.tenant_uuid}.device.{self.device_uuid}.response"

            payload = {
                "command_id": command_id,
                "device_uuid": self.device_uuid,
                "timestamp": int(time.time() * 1000),
                "result": result
            }

            await self.nc.publish(subject, json.dumps(payload).encode())
            self.logger.info(f"Sent response for command {command_id} to {subject}")

        except Exception as e:
            self.logger.error(f"Error sending command response: {str(e)}")

    # Tool implementations
    async def _handle_osquery(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle osquery requests"""
        try:
            self.logger.info(f"Processing osquery request with args: {args}")

            # Check if osquery is available
            osqueryi_path = self._find_osqueryi()
            if not osqueryi_path:
                self.logger.warning("osquery not found on this system")
                return {
                    'error': 'osquery not found on this system',
                    'available': False,
                    'searched_paths': [
                        os.path.join(self.base_dir, 'osquery', 'osqueryi.exe'),
                        r'C:\Program Files\osquery\osqueryi.exe',
                        r'C:\Program Files (x86)\osquery\osqueryi.exe',
                        'osqueryi.exe (in PATH)'
                    ]
                }

            # Get query from args
            query = args.get('query', '.tables')
            self.logger.info(f"Executing osquery: {query}")

            # Validate query (basic safety)
            if not self._is_safe_query(query):
                self.logger.warning(f"Query blocked by security policy: {query}")
                return {
                    'error': 'Query not allowed by security policy',
                    'query': query,
                    'allowed_queries': ['.tables', '.schema', 'SELECT statements (limited)']
                }

            # Execute osquery
            start_time = time.time()
            result = subprocess.run(
                [osqueryi_path, query],
                capture_output=True,
                text=True,
                timeout=30  # 30 second timeout
            )
            execution_time = int((time.time() - start_time) * 1000)

            if result.returncode == 0:
                self.logger.info(f"osquery completed successfully in {execution_time}ms")
                return {
                    'available': True,
                    'query': query,
                    'output': result.stdout,
                    'execution_time_ms': execution_time,
                    'osqueryi_path': osqueryi_path
                }
            else:
                self.logger.error(f"osquery failed with return code {result.returncode}: {result.stderr}")
                return {
                    'error': 'osquery execution failed',
                    'stderr': result.stderr,
                    'returncode': result.returncode,
                    'query': query
                }

        except subprocess.TimeoutExpired:
            self.logger.error("osquery query timed out after 30 seconds")
            return {'error': 'osquery query timed out (30s limit)', 'query': args.get('query', 'unknown')}
        except Exception as e:
            self.logger.error(f"osquery execution error: {str(e)}")
            return {'error': f'osquery execution error: {str(e)}', 'query': args.get('query', 'unknown')}

    def _find_osqueryi(self) -> Optional[str]:
        """Find osqueryi executable"""
        # Common paths for osqueryi
        possible_paths = [
            os.path.join(self.base_dir, 'osquery', 'osqueryi.exe'),
            r'C:\Program Files\osquery\osqueryi.exe',
            r'C:\Program Files (x86)\osquery\osqueryi.exe',
            'osqueryi.exe'  # In PATH
        ]

        for path in possible_paths:
            if os.path.isfile(path):
                return path
            # Also check if it's in PATH
            if shutil.which(path):
                return shutil.which(path)

        return None

    def _is_safe_query(self, query: str) -> bool:
        """Basic query safety validation"""
        query_lower = query.lower().strip()

        # Allow specific safe queries
        safe_queries = [
            '.tables',
            '.schema',
            'select name from sqlite_master where type="table"'
        ]

        if query_lower in safe_queries:
            return True

        # Allow SELECT queries with basic validation
        if query_lower.startswith('select '):
            # Disallow dangerous keywords
            dangerous = ['drop', 'delete', 'insert', 'update', 'create', 'alter', 'exec']
            if any(keyword in query_lower for keyword in dangerous):
                return False
            return True

        return False

    async def _handle_psutil_info(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle psutil system information requests"""
        try:
            info_type = args.get('type', 'summary')

            if info_type == 'summary':
                return {
                    'cpu_percent': psutil.cpu_percent(interval=1),
                    'memory': dict(psutil.virtual_memory()._asdict()),
                    'disk': dict(psutil.disk_usage('/')._asdict()) if os.name != 'nt' else dict(psutil.disk_usage('C:')._asdict()),
                    'boot_time': psutil.boot_time(),
                    'load_avg': psutil.getloadavg() if hasattr(psutil, 'getloadavg') else [0, 0, 0]
                }
            elif info_type == 'processes':
                processes = []
                for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                    try:
                        processes.append(proc.info)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                return {'processes': processes[:50]}  # Limit to 50 processes
            else:
                return {'error': f'Unknown info type: {info_type}'}

        except Exception as e:
            return {'error': f'psutil error: {str(e)}'}

    async def _handle_system_info(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle basic system information requests"""
        try:
            return {
                'platform': platform.platform(),
                'system': platform.system(),
                'release': platform.release(),
                'version': platform.version(),
                'machine': platform.machine(),
                'processor': platform.processor(),
                'hostname': platform.node(),
                'python_version': platform.python_version(),
                'agent_version': '2.0.0-nats',
                'device_uuid': self.device_uuid,
                'tenant_uuid': self.tenant_uuid
            }
        except Exception as e:
            return {'error': f'system info error: {str(e)}'}

    async def _handle_ping(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle ping requests"""
        return {
            'pong': True,
            'timestamp': int(time.time() * 1000),
            'session_id': self.session_id
        }

    # Streaming functionality
    async def _start_streaming(self, command: Dict[str, Any]):
        """Start streaming metrics"""
        try:
            self.streaming_metrics = command.get('metrics', ['cpu_percent', 'memory_percent'])
            self.streaming_interval = command.get('interval_ms', 2000) / 1000.0
            ttl_seconds = command.get('ttl_s', 300)  # 5 minute default TTL

            if self.streaming_active:
                await self._stop_streaming()

            self.streaming_active = True
            self.streaming_task = asyncio.create_task(self._streaming_loop(ttl_seconds))

            self.logger.info(f"Started streaming: {self.streaming_metrics} every {self.streaming_interval}s (TTL: {ttl_seconds}s)")

        except Exception as e:
            self.logger.error(f"Error starting streaming: {str(e)}")

    async def _stop_streaming(self):
        """Stop streaming metrics"""
        try:
            self.streaming_active = False
            if self.streaming_task:
                self.streaming_task.cancel()
                try:
                    await self.streaming_task
                except asyncio.CancelledError:
                    pass
                self.streaming_task = None

            self.logger.info("Stopped streaming")

        except Exception as e:
            self.logger.error(f"Error stopping streaming: {str(e)}")

    async def _streaming_loop(self, ttl_seconds: int):
        """Main streaming loop with TTL"""
        start_time = time.time()

        try:
            while self.streaming_active and (time.time() - start_time) < ttl_seconds:
                for metric in self.streaming_metrics:
                    try:
                        value = await self._get_metric_value(metric)
                        if value is not None:
                            await self._publish_metric(metric, value)
                    except Exception as e:
                        self.logger.error(f"Error getting metric {metric}: {str(e)}")

                await asyncio.sleep(self.streaming_interval)

        except asyncio.CancelledError:
            self.logger.info("Streaming loop cancelled")
        except Exception as e:
            self.logger.error(f"Error in streaming loop: {str(e)}")
        finally:
            self.streaming_active = False
            self.logger.info("Streaming loop ended (TTL expired or cancelled)")

    async def _get_metric_value(self, metric: str) -> Optional[float]:
        """Get current value for a metric"""
        try:
            if metric == 'cpu_percent':
                return psutil.cpu_percent(interval=0.1)
            elif metric == 'memory_percent':
                return psutil.virtual_memory().percent
            elif metric == 'disk_percent':
                disk_path = 'C:' if os.name == 'nt' else '/'
                return psutil.disk_usage(disk_path).percent
            elif metric == 'network_bytes_in':
                return psutil.net_io_counters().bytes_recv
            elif metric == 'network_bytes_out':
                return psutil.net_io_counters().bytes_sent
            elif metric == 'uptime':
                return time.time() - psutil.boot_time()
            else:
                self.logger.warning(f"Unknown metric: {metric}")
                return None

        except Exception as e:
            self.logger.error(f"Error getting metric {metric}: {str(e)}")
            return None

    async def _publish_metric(self, metric_type: str, value: float):
        """Publish a metric value to NATS"""
        try:
            # Use demo.system subject pattern (matches working agent and dashboard expectations)
            subject = f"demo.system.{self.device_uuid}.{metric_type}"

            message = {
                'device_uuid': self.device_uuid,
                'tenant_uuid': self.tenant_uuid,
                'metric_type': metric_type,
                'value': value,
                'timestamp': int(time.time() * 1000)
            }

            await self.nc.publish(subject, json.dumps(message).encode())

        except Exception as e:
            self.logger.error(f"Error publishing metric {metric_type}: {str(e)}")

    async def send_heartbeat(self):
        """Send periodic heartbeat with capabilities"""
        try:
            subject = f"tenant.{self.tenant_uuid}.device.{self.device_uuid}.status.heartbeat"

            message = {
                'device_uuid': self.device_uuid,
                'tenant_uuid': self.tenant_uuid,
                'timestamp': int(time.time() * 1000),
                'agent_version': '2.0.0-nats',
                'session_id': self.session_id,
                'capabilities': {
                    'tools': list(self.tools.keys()),
                    'osquery_available': self._find_osqueryi() is not None,
                    'streaming_metrics': ['cpu_percent', 'memory_percent', 'disk_percent', 'network_bytes_in', 'network_bytes_out', 'uptime']
                },
                'system_info': {
                    'platform': platform.system(),
                    'hostname': platform.node()
                }
            }

            await self.nc.publish(subject, json.dumps(message).encode())
            self.logger.debug("Heartbeat sent")

        except Exception as e:
            self.logger.error(f"Error sending heartbeat: {str(e)}")

    async def _start_automatic_streaming(self):
        """Start automatic system metrics streaming for dashboard"""
        try:
            self.logger.info("Starting automatic system metrics streaming")

            # Start streaming with default metrics (like working agent)
            streaming_config = {
                'metrics': ['cpu_percent', 'memory_percent', 'disk_percent', 'network_bytes_in', 'network_bytes_out', 'uptime'],
                'interval_ms': 2000,
                'ttl_s': 86400  # 24 hours
            }

            await self._start_streaming(streaming_config)

        except Exception as e:
            self.logger.error(f"Error starting automatic streaming: {str(e)}")

    async def run(self):
        """Main agent loop"""
        try:
            self.logger.info("Starting Wegweiser NATS Agent...")

            # Load configuration
            self.load_config()

            # Get tenant information
            if not await self.get_tenant_info():
                self.logger.error("Failed to get tenant information")
                return

            # Connect to NATS
            if not await self.connect_nats():
                self.logger.error("Failed to connect to NATS")
                return

            # Setup subscriptions
            await self.setup_subscriptions()

            # Send initial heartbeat
            await self.send_heartbeat()

            self.logger.info("Agent is running and ready for commands")

            # Start automatic system metrics streaming (like working agent)
            await self._start_automatic_streaming()

            # Main loop with periodic heartbeat
            while True:
                await asyncio.sleep(60)  # Heartbeat every minute
                await self.send_heartbeat()

        except KeyboardInterrupt:
            self.logger.info("Agent stopped by user")
        except Exception as e:
            self.logger.error(f"Agent error: {str(e)}")
        finally:
            await self.cleanup()

    async def cleanup(self):
        """Cleanup resources"""
        try:
            if self.streaming_active:
                await self._stop_streaming()

            if self.nc:
                await self.nc.close()

            self.logger.info("Agent cleanup completed")

        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")


# Main execution
async def main():
    """Main entry point"""
    agent = WegweiserNATSAgent()
    await agent.run()


if __name__ == "__main__":
    # Run the agent
    asyncio.run(main())
