
import os
import sys
import json
import asyncio
import logging
import platform
import time
from typing import Dict, Any

# Third-party imports
import nats
from nats.errors import TimeoutError as NATSTimeoutError
import aiohttp

# Internal imports
from core.tool_manager import ToolManager

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WegweiserNATSAgent:
    """Secure NATS-based Wegweiser agent with RPC and on-demand tool execution."""
    
    def __init__(self):
        self.nc = None  # NATS connection
        self.device_uuid = None
        self.tenant_uuid = None
        self.server_url = None
        self.nats_server = None
        self.tool_manager = None
        self._setup_paths()
        self.load_config()

    def _setup_paths(self):
        """Setup directory paths."""
        self.base_dir = "/opt/Wegweiser" if platform.system() != "Windows" else os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), "Wegweiser")
        self.log_dir = os.path.join(self.base_dir, 'Logs')
        self.config_dir = os.path.join(self.base_dir, 'Config')
        os.makedirs(self.log_dir, exist_ok=True)

    def load_config(self):
        """Load agent configuration from JSON file."""
        config_file = os.path.join(self.config_dir, 'agent.config')
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Configuration file not found: {config_file}")
        
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        self.device_uuid = config.get('deviceuuid')
        self.server_url = config.get('server_url', 'app.wegweiser.tech')
        if not self.device_uuid:
            raise ValueError("Device UUID not found in configuration")

    async def get_tenant_info(self):
        """Get tenant information from the server."""
        url = f"https://{self.server_url}/api/device/{self.device_uuid}/tenant"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    self.tenant_uuid = data.get('tenant_uuid')
                    self.nats_server = data.get('nats_server', 'tls://nats.wegweiser.tech:443')
                    return True
                return False

    async def get_nats_credentials(self):
        """Get NATS credentials from the server."""
        url = f"https://{self.server_url}/api/nats/device/{self.device_uuid}/credentials"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return (await response.json()).get('credentials')
                return None

    async def connect_nats(self):
        """Connect to NATS server with TLS and authentication."""
        credentials = await self.get_nats_credentials()
        if not credentials:
            logger.error("Failed to get NATS credentials")
            return False

        self.nc = await nats.connect(
            servers=[self.nats_server],
            user=credentials['username'],
            password=credentials['password'],
            name=f"wegweiser-agent-{self.device_uuid}",
            max_reconnect_attempts=10,
            reconnect_time_wait=2
        )
        logger.info("Connected to NATS server")
        return True

    async def setup_subscriptions(self):
        """Setup NATS subscriptions for commands."""
        cmd_subject = f"tenant.{self.tenant_uuid}.device.{self.device_uuid}.command"
        await self.nc.subscribe(cmd_subject, cb=self._handle_command)
        logger.info(f"Subscribed to commands: {cmd_subject}")

    async def _handle_command(self, msg):
        """Handle incoming command messages."""
        try:
            data = json.loads(msg.data.decode())
            payload = data.get('payload', data)
            command = payload.get('command')
            command_id = payload.get('command_id')
            parameters = payload.get('parameters', {})

            logger.info(f"Received command: {command} (ID: {command_id})")

            if command == 'ping':
                response = {'status': 'success', 'result': 'pong'}
            elif self.tool_manager and command in self.tool_manager.registered_tools:
                result = await self.tool_manager.run_tool(command, parameters)
                response = {'status': 'success', 'result': result}
            else:
                response = {'status': 'error', 'error': f'Unknown command: {command}'}

            await self._send_command_response(command_id, response)

        except Exception as e:
            logger.error(f"Error handling command: {e}", exc_info=True)
            if 'command_id' in locals():
                await self._send_command_response(command_id, {'status': 'error', 'error': str(e)})

    async def _send_command_response(self, command_id: str, result: dict):
        """Send command response via NATS."""
        subject = f"tenant.{self.tenant_uuid}.device.{self.device_uuid}.response"
        response_payload = {
            "command_id": command_id,
            "device_uuid": self.device_uuid,
            "timestamp": int(time.time() * 1000),
            "result": result
        }
        await self.nc.publish(subject, json.dumps(response_payload).encode())
        logger.info(f"Sent response for command {command_id}")

    async def run(self):
        """Main agent loop."""
        if not await self.get_tenant_info():
            logger.error("Failed to get tenant information, shutting down.")
            return

        self.tool_manager = ToolManager(self.base_dir, self.server_url)

        if not await self.connect_nats():
            logger.error("Failed to connect to NATS, shutting down.")
            return

        await self.setup_subscriptions()
        logger.info("Agent is running and ready for commands.")
        try:
            while True:
                await asyncio.sleep(3600)  # Keep alive
        except asyncio.CancelledError:
            logger.info("Agent run cancelled.")
        finally:
            if self.nc:
                await self.nc.close()
                logger.info("NATS connection closed.")

async def main():
    agent = WegweiserNATSAgent()
    try:
        await agent.run()
    except (FileNotFoundError, ValueError) as e:
        logger.error(f"Configuration error: {e}")
    except Exception as e:
        logger.error(f"A fatal error occurred: {e}", exc_info=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Agent stopped by user.")
