#!/usr/bin/env python3
"""
Wegweiser NATS Persistent Agent - Entry Point
Runs the agent with NATS messaging enabled for persistent connectivity
"""

import sys
import os
import asyncio
import logging
import signal
from pathlib import Path

# Add current directory to path so core module can be imported
agent_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, agent_dir)

from core.agent import WegweiserAgent
from core.config import ConfigManager
import subprocess
import json

logger = logging.getLogger(__name__)


async def handle_osquery(parameters: dict) -> dict:
    """Handle osquery command"""
    try:
        query = parameters.get('query', '.tables')
        logger.info(f"Executing osquery: {query}")

        # Find osqueryi
        osqueryi_path = None
        possible_paths = [
            r'C:\Program Files\osquery\osqueryi.exe',
            r'C:\Program Files (x86)\osquery\osqueryi.exe',
            'osqueryi.exe'
        ]

        for path in possible_paths:
            try:
                result = subprocess.run([path, '--version'], capture_output=True, timeout=5)
                if result.returncode == 0:
                    osqueryi_path = path
                    break
            except:
                pass

        if not osqueryi_path:
            logger.warning("osqueryi not found")
            return {
                'error': 'osquery not found on this system',
                'available': False
            }

        # Execute query
        cmd = [osqueryi_path]
        if query.lower().strip().startswith('select '):
            cmd.append('--json')
        cmd.append(query)

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            logger.info(f"osquery executed successfully")

            # Try to parse JSON for SELECT queries
            json_data = None
            if query.lower().strip().startswith('select ') and result.stdout.strip():
                try:
                    json_data = json.loads(result.stdout)
                except:
                    pass

            return {
                'available': True,
                'query': query,
                'output': result.stdout,
                'data': json_data,
                'format': 'json' if json_data else 'text'
            }
        else:
            logger.error(f"osquery failed: {result.stderr}")
            return {
                'error': 'osquery execution failed',
                'stderr': result.stderr,
                'query': query
            }

    except subprocess.TimeoutExpired:
        logger.error("osquery query timed out")
        return {'error': 'osquery query timed out (30s limit)', 'query': parameters.get('query')}
    except Exception as e:
        logger.error(f"osquery error: {str(e)}")
        return {'error': f'osquery error: {str(e)}', 'query': parameters.get('query')}

# Global flag for graceful shutdown
_shutdown_event = None


def setup_signal_handlers(loop):
    """Setup signal handlers for graceful shutdown"""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating shutdown...")
        if _shutdown_event:
            _shutdown_event.set()

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)


async def main():
    """Main entry point for NATS agent"""
    global _shutdown_event
    _shutdown_event = asyncio.Event()

    try:
        # Initialize agent with NATS enabled
        logger.info("Initializing Wegweiser NATS Agent...")
        agent = WegweiserAgent(enable_nats=True, debug=False)

        # Initialize agent
        if not await agent.initialize():
            logger.error("Failed to initialize agent")
            return 1

        # Connect to NATS
        if agent.nats:
            logger.info("Connecting to NATS server...")
            if not await agent.nats.connect(agent.api):
                logger.error("Failed to connect to NATS")
                return 1

            # Register command handlers
            agent.nats.register_command_handler('osquery', handle_osquery)
            logger.info("Command handlers registered")

            # Setup subscriptions
            if not await agent.nats.setup_subscriptions():
                logger.error("Failed to setup NATS subscriptions")
                return 1

            logger.info("NATS agent running. Waiting for messages...")

            # Start background tasks
            snippet_task = asyncio.create_task(
                agent.nats.start_snippet_loop(agent.api, agent.executor, agent.crypto, agent.config)
            )
            logger.info("Snippet loop task created")

            # Start heartbeat loop (30 second interval)
            heartbeat_task = asyncio.create_task(
                agent.nats.start_heartbeat_loop(agent.api, interval_seconds=30)
            )
            logger.info("Heartbeat loop task created")

            # Start automatic metrics streaming
            streaming_config = {
                'metrics': ['cpu_percent', 'memory_percent', 'disk_percent', 'network_bytes_in', 'network_bytes_out', 'uptime'],
                'interval_ms': 2000,
                'ttl_s': 86400  # 24 hours
            }
            await agent.nats._start_streaming(streaming_config)
            logger.info("Automatic metrics streaming started")

            # Keep agent running until shutdown signal
            try:
                await _shutdown_event.wait()
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received")
            finally:
                logger.info("Disconnecting from NATS...")
                await agent.nats._stop_streaming()
                snippet_task.cancel()
                heartbeat_task.cancel()
                try:
                    await snippet_task
                except asyncio.CancelledError:
                    pass
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass
                await agent.nats.disconnect()
        else:
            logger.error("NATS service not initialized")
            return 1

        logger.info("NATS agent shutdown complete")
        return 0

    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        return 1


def run_sync():
    """Synchronous wrapper for async main - compatible with WinSW"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        setup_signal_handlers(loop)
        return loop.run_until_complete(main())
    except Exception as e:
        logger.error(f"Failed to run agent: {e}", exc_info=True)
        return 1
    finally:
        loop.close()


if __name__ == '__main__':
    sys.exit(run_sync())

