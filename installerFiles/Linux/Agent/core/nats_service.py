"""
NATS Persistent Service Module
Integrates NATS messaging into the refactored Wegweiser agent
"""

import json
import asyncio
import logging
import time
import os
import psutil
from typing import Dict, Any, Optional, Callable
from datetime import datetime

try:
    import nats
    from nats.errors import TimeoutError as NATSTimeoutError
except ImportError:
    nats = None

logger = logging.getLogger(__name__)


class NATSService:
    """NATS messaging service for persistent agent connectivity"""
    
    def __init__(self, device_uuid: str, tenant_uuid: str, server_url: str):
        """Initialize NATS service"""
        self.device_uuid = device_uuid
        self.tenant_uuid = tenant_uuid
        self.server_url = server_url
        self.nc = None
        self.nats_server = None
        self.session_id = str(datetime.now().timestamp())
        
        # Command handlers registry
        self.command_handlers: Dict[str, Callable] = {}
        
        # Streaming state
        self.streaming_active = False
        self.streaming_task = None
        self.streaming_interval = 2.0
        
    def register_command_handler(self, command: str, handler: Callable):
        """Register a command handler"""
        self.command_handlers[command] = handler
        logger.info(f"Registered command handler: {command}")

    async def get_tenant_info(self, api_client) -> bool:
        """Get tenant information from server"""
        try:
            response = await api_client.get_async(f'/api/device/{self.device_uuid}/tenant')
            self.tenant_uuid = response.get('tenant_uuid')
            self.nats_server = response.get('nats_server', 'tls://nats.wegweiser.tech:443')

            logger.info(f"Device UUID: {self.device_uuid}")
            logger.info(f"Tenant UUID: {self.tenant_uuid}")
            logger.info(f"NATS Server: {self.nats_server}")

            return True
        except Exception as e:
            logger.error(f"Error getting tenant info: {str(e)}")
            return False

    async def connect(self, api_client) -> bool:
        """Connect to NATS server"""
        try:
            if not nats:
                logger.error("nats-py not installed")
                return False
            
            # Get tenant info from server
            tenant_info = await self._get_tenant_info(api_client)
            if not tenant_info:
                logger.error("Failed to get tenant info")
                return False
            
            self.nats_server = tenant_info.get('nats_server', 'tls://nats.wegweiser.tech:443')
            
            # Get NATS credentials
            credentials = await self._get_nats_credentials(api_client)
            if not credentials:
                logger.error("Failed to get NATS credentials")
                return False
            
            # Connect to NATS
            self.nc = await nats.connect(
                servers=[self.nats_server],
                user=credentials.get('username'),
                password=credentials.get('password'),
                name=f"wegweiser-agent-{self.device_uuid}",
                max_reconnect_attempts=10,
                reconnect_time_wait=2
            )
            
            logger.info(f"Connected to NATS server: {self.nats_server}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to NATS: {str(e)}")
            return False
    
    async def setup_subscriptions(self) -> bool:
        """Setup NATS subscriptions"""
        try:
            if not self.nc:
                logger.error("Not connected to NATS")
                return False

            # Command subscription
            cmd_subject = f"tenant.{self.tenant_uuid}.device.{self.device_uuid}.command"
            await self.nc.subscribe(cmd_subject, cb=self._handle_command)

            # Key rotation subscription - broadcast to all devices in tenant
            key_rotation_subject = f"tenant.{self.tenant_uuid}.keys.rotation"
            await self.nc.subscribe(key_rotation_subject, cb=self._handle_key_rotation)

            logger.info(f"Subscribed to: {cmd_subject}")
            logger.info(f"Subscribed to key rotation events: {key_rotation_subject}")
            return True

        except Exception as e:
            logger.error(f"Error setting up subscriptions: {str(e)}")
            return False
    
    async def _handle_key_rotation(self, msg):
        """Handle KEY_ROTATION events from server

        Receives new server public keys when rotation occurs
        """
        try:
            data = json.loads(msg.data.decode())

            if data.get('event') != 'KEY_ROTATION':
                logger.warning(f"Unexpected key event: {data.get('event')}")
                return

            rotation_id = data.get('rotation_id')
            timestamp = data.get('timestamp')
            keys = data.get('keys', {})

            current_key_pem = keys.get('current')
            old_key_pem = keys.get('old')

            logger.warning(f"KEY_ROTATION event received (ID: {rotation_id}) - updating crypto cache")

            if current_key_pem:
                try:
                    # Import crypto manager from agent (if available)
                    from .crypto import CryptoManager
                    crypto = CryptoManager()

                    # Update key cache with old key first
                    if old_key_pem:
                        crypto.update_server_key(old_key_pem, key_type='old')
                        logger.info("Updated old key in cache from NATS event")

                    # Update current key
                    crypto.update_server_key(current_key_pem, key_type='current')
                    logger.info(f"Updated current key in cache from NATS event (rotation_id: {rotation_id})")

                except Exception as e:
                    logger.error(f"Failed to update keys from NATS event: {e}")
            else:
                logger.error("No current key in KEY_ROTATION event")

        except Exception as e:
            logger.error(f"Error handling key rotation event: {e}")

    async def _handle_command(self, msg):
        """Handle incoming command messages"""
        try:
            data = json.loads(msg.data.decode())
            payload = data.get('payload', data)

            command = payload.get('command')
            command_id = payload.get('command_id')
            parameters = payload.get('parameters', {})
            
            logger.info(f"Received command: {command} (ID: {command_id})")
            
            # Execute command handler
            if command in self.command_handlers:
                result = await self.command_handlers[command](parameters)
                response = {
                    'command_id': command_id,
                    'status': 'success',
                    'result': result,
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
                    'available_commands': list(self.command_handlers.keys()) + ['start_metrics', 'stop_metrics']
                }
            
            await self._send_response(command_id, response)
            
        except Exception as e:
            logger.error(f"Error handling command: {str(e)}")
    
    async def _send_response(self, command_id: str, result: dict):
        """Send command response via NATS"""
        try:
            if not self.nc:
                logger.error("Not connected to NATS")
                return
            
            subject = f"tenant.{self.tenant_uuid}.device.{self.device_uuid}.response"
            payload = {
                "command_id": command_id,
                "device_uuid": self.device_uuid,
                "timestamp": int(time.time() * 1000),
                "result": result
            }
            
            await self.nc.publish(subject, json.dumps(payload).encode())
            logger.info(f"Sent response for command {command_id}")
            
        except Exception as e:
            logger.error(f"Error sending response: {str(e)}")
    
    async def _start_streaming(self, payload: dict):
        """Start metrics streaming"""
        try:
            metrics = payload.get('metrics', ['cpu_percent', 'memory_percent', 'disk_percent'])
            interval_ms = payload.get('interval_ms', 2000)
            ttl_s = payload.get('ttl_s', 300)

            self.streaming_interval = interval_ms / 1000.0

            if self.streaming_active:
                await self._stop_streaming()

            self.streaming_active = True
            self.streaming_task = asyncio.create_task(
                self._streaming_loop(metrics, ttl_s)
            )

            logger.info(f"Started streaming: {metrics} every {self.streaming_interval}s (TTL: {ttl_s}s)")
        except Exception as e:
            logger.error(f"Error starting streaming: {str(e)}")

    async def _stop_streaming(self):
        """Stop metrics streaming"""
        try:
            self.streaming_active = False
            if self.streaming_task:
                self.streaming_task.cancel()
                try:
                    await self.streaming_task
                except asyncio.CancelledError:
                    pass
                self.streaming_task = None

            logger.info("Stopped streaming")
        except Exception as e:
            logger.error(f"Error stopping streaming: {str(e)}")

    async def _streaming_loop(self, metrics: list, ttl_seconds: int):
        """Main streaming loop with TTL"""
        start_time = time.time()

        try:
            while self.streaming_active and (time.time() - start_time) < ttl_seconds:
                for metric in metrics:
                    try:
                        value = await self._get_metric_value(metric)
                        if value is not None:
                            await self._publish_metric(metric, value)
                    except Exception as e:
                        logger.error(f"Error getting metric {metric}: {str(e)}")

                await asyncio.sleep(self.streaming_interval)

        except asyncio.CancelledError:
            logger.info("Streaming loop cancelled")
        except Exception as e:
            logger.error(f"Error in streaming loop: {str(e)}")
        finally:
            self.streaming_active = False
            logger.info("Streaming loop ended (TTL expired or cancelled)")

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
                logger.warning(f"Unknown metric: {metric}")
                return None
        except Exception as e:
            logger.error(f"Error getting metric {metric}: {str(e)}")
            return None

    async def _publish_metric(self, metric_type: str, value: float):
        """Publish a metric value to NATS"""
        try:
            if not self.nc:
                return

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
            logger.error(f"Error publishing metric {metric_type}: {str(e)}")

    async def start_snippet_loop(self, api_client, executor, crypto, config):
        """Start background snippet execution loop"""
        logger.info("Starting snippet execution loop")
        while True:
            try:
                # Get pending snippets
                schedule_list = api_client.get_pending_snippets(config.device_uuid)

                if schedule_list:
                    logger.info(f"Found {len(schedule_list)} pending snippets")
                    for schedule_uuid in schedule_list:
                        try:
                            # Download snippet
                            response = api_client.get_snippet(schedule_uuid)

                            # Convert dict to JSON string for signature verification
                            response_json_str = json.dumps(response) if isinstance(response, dict) else response

                            snippet_code, snippet_name, parameters = executor.decode_snippet(response)

                            # Verify signature
                            server_pub_key = crypto.load_public_key(config.get('serverpubpem'))

                            if not crypto.verify_base64_payload_signature(response_json_str, server_pub_key):
                                logger.error(f"Signature verification failed: {snippet_name}")
                                api_client.report_snippet_execution(schedule_uuid, 'SIGFAIL')
                                continue

                            # Execute snippet asynchronously (non-blocking)
                            result = await executor.execute(snippet_code, snippet_name, schedule_uuid, parameters)

                            # Report result
                            status = 'SUCCESS' if result.status == 'success' else 'EXECFAIL'
                            api_client.report_snippet_execution(
                                schedule_uuid,
                                status,
                                result.duration_ms,
                                result.exit_code
                            )

                            logger.info(f"Snippet executed: {snippet_name} - {status}")

                        except Exception as e:
                            logger.error(f"Failed to execute snippet {schedule_uuid}: {e}")
                            try:
                                api_client.report_snippet_execution(schedule_uuid, 'EXECFAIL')
                            except:
                                pass

                # Sleep before next check
                await asyncio.sleep(60)

            except Exception as e:
                logger.error(f"Error in snippet loop: {e}")
                await asyncio.sleep(60)

    async def _get_tenant_info(self, api_client) -> Optional[Dict[str, Any]]:
        """Get tenant info from server"""
        try:
            response = await api_client.get_async(f"/api/device/{self.device_uuid}/tenant")
            return response
        except Exception as e:
            logger.error(f"Error getting tenant info: {str(e)}")
            return None
    
    async def _get_nats_credentials(self, api_client) -> Optional[Dict[str, Any]]:
        """Get NATS credentials from server"""
        try:
            response = await api_client.get_async(f"/api/nats/device/{self.device_uuid}/credentials")
            return response.get('credentials') if response else None
        except Exception as e:
            logger.error(f"Error getting NATS credentials: {str(e)}")
            return None

    async def start_heartbeat_loop(self, api_client, interval_seconds: int = 30):
        """Start periodic heartbeat to server"""
        logger.info(f"Starting heartbeat loop (interval: {interval_seconds}s)")

        while True:
            try:
                # Prepare heartbeat payload
                heartbeat_data = {
                    'device_uuid': self.device_uuid,
                    'tenant_uuid': self.tenant_uuid,
                    'agent_version': '3.0.0-poc',
                    'session_id': self.session_id,
                    'timestamp': int(time.time() * 1000),
                    'status': {
                        'nats_server': self.nats_server,
                        'connected': self.nc is not None and not self.nc.is_closed
                    },
                    'system_info': {
                        'uptime': time.time() - psutil.boot_time()
                    }
                }

                # Send heartbeat to server
                try:
                    logger.info(f"Sending heartbeat for device {self.device_uuid}")
                    response = await api_client.post_async(
                        f"/api/nats/device/{self.device_uuid}/heartbeat",
                        heartbeat_data
                    )
                    logger.info(f"Heartbeat sent successfully: {response}")
                except Exception as e:
                    logger.error(f"Failed to send heartbeat: {str(e)}")

                # Wait before next heartbeat
                await asyncio.sleep(interval_seconds)

            except asyncio.CancelledError:
                logger.info("Heartbeat loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {str(e)}")
                await asyncio.sleep(interval_seconds)

    async def disconnect(self):
        """Disconnect from NATS"""
        try:
            if self.nc:
                await self.nc.close()
                logger.info("Disconnected from NATS")
        except Exception as e:
            logger.error(f"Error disconnecting from NATS: {str(e)}")

