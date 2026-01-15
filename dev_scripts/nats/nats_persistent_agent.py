#!/usr/bin/env python3
"""
NATS-based Persistent Agent for Wegweiser

Replaces the WebSocket-based persistent agent with NATS communication
while maintaining the same registration flow and functionality.
"""

import asyncio
import json
import logging
import os
import platform
import psutil
import socket
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

import nats
from nats.aio.client import Client as NATS
from nats.js import JetStreamContext
from nats.errors import TimeoutError, ConnectionClosedError

# Configuration
NATS_SERVER = "tls://nats.wegweiser.tech:443"
FLASK_SERVER = "app.wegweiser.tech"

# Determine application paths
if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
else:
    application_path = os.path.dirname(os.path.abspath(__file__))

base_dir = Path(application_path).parent
config_dir = base_dir / "Config"
logs_dir = base_dir / "Logs"

# Ensure directories exist
config_dir.mkdir(exist_ok=True)
logs_dir.mkdir(exist_ok=True)

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(logs_dir / 'nats_persistent_agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class NATSWegweiserAgent:
    """NATS-based Wegweiser Agent"""
    
    def __init__(self):
        self.running = False
        self.device_uuid = None
        self.tenant_uuid = None
        self.server_url = FLASK_SERVER
        self.nats_url = NATS_SERVER
        self.nc: Optional[NATS] = None
        self.js: Optional[JetStreamContext] = None
        self.stop_requested = False
        self.session_id = str(uuid.uuid4())
        
        # Initialize logging
        logger.info(f"NATS Agent initialized at {datetime.now()}")
        logger.info(f"Agent session ID: {self.session_id}")
        logger.info(f"Running from {application_path}")
        logger.info(f"Base directory: {base_dir}")
        logger.info(f"Config directory: {config_dir}")
        
        # Load configuration
        self.load_configuration()
        
        # Collect system information
        self.system_info = self._collect_system_info()
        
        logger.info(f"Device UUID: {self.device_uuid}")
        logger.info(f"Tenant UUID: {self.tenant_uuid}")
        logger.info(f"NATS Server: {self.nats_url}")
    
    def load_configuration(self):
        """Load configuration from agent.config file"""
        config_path = config_dir / 'agent.config'
        
        if not config_path.exists():
            logger.error(f"Configuration file not found: {config_path}")
            logger.error("Please run the agent registration process first")
            sys.exit(1)
        
        try:
            with open(config_path, 'r') as f:
                self.config = json.load(f)

            self.device_uuid = self.config.get('deviceuuid')
            self.server_url = self.config.get('serverAddr', FLASK_SERVER)
            
            if not self.device_uuid:
                logger.error("Device UUID not found in configuration")
                sys.exit(1)
            
            # Get tenant UUID from device registration
            self.tenant_uuid = self._get_tenant_uuid()
            
            logger.info(f"Configuration loaded successfully")
            logger.info(f"Device UUID: {self.device_uuid}")
            logger.info(f"Server URL: {self.server_url}")
            
        except Exception as e:
            logger.error(f"Error loading configuration: {str(e)}")
            sys.exit(1)
    
    def _get_tenant_uuid(self) -> str:
        """Get tenant UUID for this device from Flask API or config file"""
        import requests

        # First try to get from config file
        config_tenant_uuid = self.config.get('tenantuuid')

        try:
            url = f"https://{self.server_url}/api/nats/device/{self.device_uuid}/tenant"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                return data.get('tenant_uuid')
            else:
                logger.warning(f"Failed to get tenant UUID from API: {response.status_code}")
                if config_tenant_uuid:
                    logger.info(f"Using tenant UUID from config file: {config_tenant_uuid}")
                    return config_tenant_uuid
                return None

        except Exception as e:
            logger.warning(f"Error getting tenant UUID from API: {str(e)}")
            if config_tenant_uuid:
                logger.info(f"Using tenant UUID from config file: {config_tenant_uuid}")
                return config_tenant_uuid
            return None
    
    def _collect_system_info(self) -> Dict[str, Any]:
        """Collect system information"""
        try:
            return {
                "hostname": socket.gethostname(),
                "platform": platform.system(),
                "platform_version": platform.version(),
                "architecture": platform.machine(),
                "python_version": platform.python_version(),
                "processor": platform.processor(),
                "ip_addresses": self._get_ip_addresses(),
                "memory_total": psutil.virtual_memory().total,
                "memory_available": psutil.virtual_memory().available,
                "cpu_count": psutil.cpu_count(),
                "boot_time": int(psutil.boot_time()),
                "network_interfaces": list(psutil.net_if_addrs().keys()),
                "users": [user.name for user in psutil.users()]
            }
        except Exception as e:
            logger.error(f"Error collecting system info: {str(e)}")
            return {}
    
    def _get_ip_addresses(self) -> list:
        """Get all IP addresses for this machine"""
        try:
            addresses = []
            for interface, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    if addr.family == socket.AF_INET:
                        addresses.append(addr.address)
            return addresses
        except Exception:
            return []
    
    async def start(self):
        """Start the NATS agent"""
        self.running = True
        logger.info("Starting NATS Wegweiser Agent...")
        
        if not self.tenant_uuid:
            logger.error("Cannot start agent without tenant UUID")
            return
        
        try:
            await self._connect_to_nats()
            await self._setup_subscriptions()
            await self._start_heartbeat()

            # Start system metrics streaming (demo)
            await self._start_system_monitoring()

            logger.info("NATS Wegweiser Agent started successfully")

            # Main loop
            while self.running and not self.stop_requested:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Agent error: {str(e)}")
        finally:
            await self._cleanup()
    
    async def _connect_to_nats(self):
        """Connect to NATS server"""
        try:
            # Get NATS credentials from Flask API
            credentials = await self._get_nats_credentials()

            # Prefer server URL returned by Flask credentials if present
            server_url = credentials.get('nats_url', self.nats_url)
            self.nats_url = server_url

            self.nc = NATS()
            await self.nc.connect(
                servers=[server_url],
                user=credentials['username'],
                password=credentials['password'],
                name=f"wegweiser_agent_{self.device_uuid}",
                reconnect_time_wait=2,
                max_reconnect_attempts=10,
                error_cb=self._error_callback,
                disconnected_cb=self._disconnected_callback,
                reconnected_cb=self._reconnected_callback
            )
            
            # Set up JetStream
            self.js = self.nc.jetstream()
            
            logger.info("Connected to NATS server")
            
        except Exception as e:
            logger.error(f"Failed to connect to NATS: {str(e)}")
            raise
    
    async def _get_nats_credentials(self) -> Dict[str, str]:
        """Get NATS credentials from Flask API"""
        import aiohttp
        
        try:
            url = f"https://{self.server_url}/api/nats/device/{self.device_uuid}/credentials"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data['credentials']
                    else:
                        raise Exception(f"Failed to get credentials: {response.status}")
                        
        except Exception as e:
            logger.error(f"Error getting NATS credentials: {str(e)}")
            raise
    
    async def _setup_subscriptions(self):
        """Set up NATS subscriptions for commands"""
        try:
            # Subscribe to commands for this device
            command_subject = f"tenant.{self.tenant_uuid}.device.{self.device_uuid}.command"
            await self.nc.subscribe(command_subject, cb=self._handle_command)
            
            logger.info(f"Subscribed to commands: {command_subject}")
            
        except Exception as e:
            logger.error(f"Failed to set up subscriptions: {str(e)}")
            raise
    
    async def _start_heartbeat(self):
        """Start heartbeat task"""
        asyncio.create_task(self._heartbeat_loop())

    async def _start_system_monitoring(self):
        """Start system metrics streaming (demo only)"""
        # Only enable if explicitly configured
        if not self.config.get('enable_demo_streaming', True):  # Default to True for demo
            logger.info("Demo streaming disabled in config")
            return

        logger.info("Starting system metrics streaming for NATS demo")
        asyncio.create_task(self._system_metrics_loop())
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeat messages"""
        while self.running and not self.stop_requested:
            try:
                await self._send_heartbeat()
                await asyncio.sleep(30)  # Send heartbeat every 30 seconds
                
            except Exception as e:
                logger.error(f"Heartbeat error: {str(e)}")
                await asyncio.sleep(5)
    
    async def _send_heartbeat(self):
        """Send heartbeat message via NATS and HTTP"""
        try:
            # Send via NATS (for future message service)
            subject = f"tenant.{self.tenant_uuid}.device.{self.device_uuid}.heartbeat"

            payload = {
                "device_uuid": self.device_uuid,
                "tenant_uuid": self.tenant_uuid,
                "session_id": self.session_id,
                "timestamp": int(time.time()),
                "system_info": self.system_info,
                "status": {
                    "is_connected": True,
                    "connection_type": "nats",
                    "nats_server": self.nats_url,
                    "uptime": int(time.time()) - self.system_info.get("boot_time", int(time.time()))
                }
            }

            message_data = json.dumps(payload).encode()
            await self.nc.publish(subject, message_data)

            # Also send via HTTP to Flask endpoint for immediate processing
            await self._send_heartbeat_http(payload)

            logger.debug("Heartbeat sent via NATS and HTTP")

        except Exception as e:
            logger.error(f"Failed to send heartbeat: {str(e)}")

    async def _send_heartbeat_http(self, payload):
        """Send heartbeat via HTTP POST to Flask"""
        try:
            import aiohttp

            url = f"https://{self.server_url}/api/nats/device/{self.device_uuid}/heartbeat"

            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        logger.debug("HTTP heartbeat sent successfully")
                    else:
                        logger.warning(f"HTTP heartbeat failed: {response.status}")

        except Exception as e:
            logger.debug(f"HTTP heartbeat error (non-critical): {str(e)}")

    async def _system_metrics_loop(self):
        """Stream system metrics every 2 seconds for NATS demo"""
        try:
            import psutil
        except ImportError:
            logger.warning("psutil not available - system metrics disabled")
            return

        if not self.nc or not self.nc.is_connected:
            logger.warning("NATS not connected - system metrics disabled")
            return

        logger.info("System metrics streaming started")
        last_network_in = 0
        last_network_out = 0

        while self.running and not self.stop_requested:
            try:
                # Get current network stats
                try:
                    net_io = psutil.net_io_counters()
                    current_network_in = net_io.bytes_recv
                    current_network_out = net_io.bytes_sent
                except Exception:
                    # Fallback if network stats not available
                    current_network_in = 0
                    current_network_out = 0

                # Calculate network rates (first iteration will be 0)
                network_in_rate = current_network_in - last_network_in if last_network_in > 0 else 0
                network_out_rate = current_network_out - last_network_out if last_network_out > 0 else 0

                # Collect system metrics with error handling
                try:
                    cpu_percent = psutil.cpu_percent(interval=0.1)
                except Exception:
                    cpu_percent = 0.0

                try:
                    memory_percent = psutil.virtual_memory().percent
                except Exception:
                    memory_percent = 0.0

                try:
                    # Use C: drive on Windows, / on Unix
                    disk_path = 'C:\\' if os.name == 'nt' else '/'
                    disk_percent = psutil.disk_usage(disk_path).percent
                except Exception:
                    disk_percent = 0.0

                try:
                    uptime = int(time.time() - psutil.boot_time())
                except Exception:
                    uptime = 0

                try:
                    load_average = psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0.0
                except Exception:
                    load_average = 0.0

                metrics = {
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory_percent,
                    'disk_percent': disk_percent,
                    'network_bytes_in': current_network_in,
                    'network_bytes_out': current_network_out,
                    'network_in_rate': network_in_rate,
                    'network_out_rate': network_out_rate,
                    'uptime': uptime,
                    'load_average': load_average
                }

                timestamp = int(time.time() * 1000)  # milliseconds

                # Send each metric to its own NATS subject
                for metric_type, value in metrics.items():
                    subject = f"demo.system.{self.device_uuid}.{metric_type}"
                    payload = {
                        'device_uuid': self.device_uuid,
                        'tenant_uuid': self.tenant_uuid,
                        'metric_type': metric_type,
                        'value': value,
                        'timestamp': timestamp
                    }

                    await self.nc.publish(subject, json.dumps(payload).encode())

                # Update last network values
                last_network_in = current_network_in
                last_network_out = current_network_out

                # Log every 30 iterations (1 minute) to avoid spam
                if hasattr(self, '_metrics_count'):
                    self._metrics_count += 1
                else:
                    self._metrics_count = 1

                if self._metrics_count % 30 == 0:
                    logger.debug(f"Sent {len(metrics)} system metrics (iteration {self._metrics_count})")

                await asyncio.sleep(2)  # 2-second intervals

            except Exception as e:
                logger.error(f"Error in system metrics loop: {str(e)}")
                await asyncio.sleep(5)  # Wait longer on error

        logger.info("System metrics streaming stopped")
    
    async def _handle_command(self, msg):
        """Handle incoming command messages"""
        try:
            data = json.loads(msg.data.decode())

            # Extract payload from NATS message wrapper
            if 'payload' in data:
                payload = data['payload']
            else:
                payload = data

            command = payload.get('command')
            command_id = payload.get('command_id')
            parameters = payload.get('parameters', {})
            
            logger.info(f"Received command: {command} (ID: {command_id})")
            
            # Execute command
            result = await self._execute_command(command, parameters)
            
            # Send response
            await self._send_command_response(command_id, result)
            
        except Exception as e:
            logger.error(f"Error handling command: {str(e)}")
    
    async def _execute_command(self, command: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a command and return result"""
        try:
            if command == "ping":
                return {"status": "success", "result": "pong", "timestamp": int(time.time())}
            
            elif command == "system_info":
                return {
                    "status": "success",
                    "result": self.system_info,
                    "timestamp": int(time.time())
                }
            
            elif command == "restart":
                logger.info("Restart command received")
                asyncio.create_task(self._restart_agent())
                return {"status": "success", "result": "Restarting agent", "timestamp": int(time.time())}
            
            else:
                return {
                    "status": "error",
                    "result": f"Unknown command: {command}",
                    "timestamp": int(time.time())
                }
                
        except Exception as e:
            return {
                "status": "error",
                "result": str(e),
                "timestamp": int(time.time())
            }
    
    async def _send_command_response(self, command_id: str, result: Dict[str, Any]):
        """Send command response via NATS"""
        try:
            subject = f"tenant.{self.tenant_uuid}.device.{self.device_uuid}.response"
            
            payload = {
                "command_id": command_id,
                "device_uuid": self.device_uuid,
                "tenant_uuid": self.tenant_uuid,
                "result": result,
                "timestamp": int(time.time())
            }
            
            message_data = json.dumps(payload).encode()
            await self.nc.publish(subject, message_data)
            
            logger.debug(f"Command response sent for {command_id}")
            
        except Exception as e:
            logger.error(f"Failed to send command response: {str(e)}")
    
    async def _restart_agent(self):
        """Restart the agent"""
        await asyncio.sleep(1)  # Give time for response to be sent
        self.stop_requested = True
        self.running = False
    
    async def _error_callback(self, error):
        """Handle NATS connection errors"""
        logger.error(f"NATS error: {error}")
    
    async def _disconnected_callback(self):
        """Handle NATS disconnection"""
        logger.warning("NATS connection lost")
    
    async def _reconnected_callback(self):
        """Handle NATS reconnection"""
        logger.info("NATS connection restored")
    
    async def _cleanup(self):
        """Clean up resources"""
        try:
            if self.nc and self.nc.is_connected:
                await self.nc.close()
            logger.info("Agent stopped")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
    
    def stop(self):
        """Stop the agent"""
        self.stop_requested = True
        self.running = False


async def main():
    """Main entry point"""
    agent = NATSWegweiserAgent()
    
    try:
        await agent.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
