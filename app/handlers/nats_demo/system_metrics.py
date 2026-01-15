# Filepath: app/handlers/nats_demo/system_metrics.py
"""
NATS Demo System Metrics Handler
Handles real-time system metrics streaming from NATS
"""

import asyncio
import json
import logging
from collections import defaultdict, deque
from datetime import datetime
from typing import Dict, Any, Set

import os
import redis
from app.utilities.app_logging_helper import log_with_route

class SystemMetricsHandler:
    """Handles real-time system metrics from NATS with shared Redis backing"""

    def __init__(self):
        # In-memory storage - keeps last 100 data points per metric (fallback)
        self.metrics_buffer: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))

        # WebSocket connections for real-time updates
        self.active_connections: Set = set()

        # Monitoring state
        self.running = False
        self.subscription_id = None

        # Redis client (lazy init)
        self._redis_client = None
        self._redis_db = int(os.environ.get('METRICS_REDIS_DB', '3'))
        self._redis_host = os.environ.get('METRICS_REDIS_HOST', 'localhost')
        self._redis_port = int(os.environ.get('METRICS_REDIS_PORT', '6379'))
        self._redis_prefix = os.environ.get('METRICS_REDIS_PREFIX', 'wegweiser:metrics')
        self._max_points = int(os.environ.get('METRICS_MAX_POINTS', '300'))
        self._ttl_seconds = int(os.environ.get('METRICS_TTL_SECONDS', '900'))  # 15 minutes

    def _get_redis(self):
        if self._redis_client is None:
            try:
                self._redis_client = redis.Redis(
                    host=self._redis_host,
                    port=self._redis_port,
                    db=self._redis_db,
                    decode_responses=True,
                    socket_timeout=3,
                    socket_connect_timeout=3,
                    health_check_interval=30,
                )
                # test connection
                self._redis_client.ping()
                log_with_route(logging.INFO, f"SystemMetricsHandler connected to Redis at {self._redis_host}:{self._redis_port} db={self._redis_db}")
            except Exception as e:
                # Keep None to use in-memory fallback
                self._redis_client = None
                log_with_route(logging.WARNING, f"SystemMetricsHandler Redis unavailable, using in-memory buffer only: {str(e)}")
        return self._redis_client

    def _redis_key(self, device_uuid: str, metric_type: str) -> str:
        return f"{self._redis_prefix}:{device_uuid}:{metric_type}"

    async def start_monitoring(self):
        """Start NATS subscription for demo metrics"""
        if self.running:
            log_with_route(logging.WARNING, "NATS demo monitoring already running")
            return

        try:
            from app.utilities.nats_manager import nats_manager
            from app.models import Tenants

            self.running = True

            # Get a NATS connection to subscribe to demo subjects
            # Demo subjects use pattern: demo.system.{device_uuid}.{metric_type}
            tenants = Tenants.query.all()

            if not tenants:
                log_with_route(logging.WARNING, "No tenants found - cannot subscribe to demo metrics")
                return

            # Use the first tenant's connection to subscribe to demo subjects
            tenant_uuid = str(tenants[0].tenantuuid)
            nc = await nats_manager.get_connection(tenant_uuid)

            # Subscribe to all demo system metrics using wildcard
            # Pattern: demo.system.*.* matches demo.system.{device_uuid}.{metric_type}
            demo_subject = "demo.system.*.*"

            subscription = await nc.subscribe(demo_subject, cb=self._handle_system_metric)
            self.subscription_id = subscription

            log_with_route(logging.INFO, f"✓ Subscribed to demo metrics: {demo_subject}")
            log_with_route(logging.INFO, "Started NATS demo system metrics monitoring")

            # Keep the monitoring running
            while self.running:
                await asyncio.sleep(1)

        except Exception as e:
            self.running = False
            log_with_route(logging.ERROR, f"Error starting NATS demo monitoring: {str(e)}")
            raise

    async def _handle_system_metric(self, msg):
        """Process incoming system metric from NATS"""
        try:
            # Parse the NATS message
            data = json.loads(msg.data.decode())

            # Extract metric information
            device_uuid = data.get('device_uuid')
            metric_type = data.get('metric_type')
            value = data.get('value')
            timestamp = data.get('timestamp')

            if not all([device_uuid, metric_type, value is not None, timestamp]):
                log_with_route(logging.WARNING, f"Incomplete metric data: {data}")
                return

            # Store in memory buffer (ephemeral fallback)
            metric_key = f"{device_uuid}.{metric_type}"
            self.metrics_buffer[metric_key].append({
                'timestamp': timestamp,
                'value': value
            })

            # Also store in Redis shared buffer if available
            r = self._get_redis()
            if r is not None:
                try:
                    key = self._redis_key(device_uuid, metric_type)
                    payload = json.dumps({'timestamp': timestamp, 'value': value})
                    with r.pipeline() as pipe:
                        pipe.lpush(key, payload)
                        pipe.ltrim(key, 0, self._max_points - 1)
                        pipe.expire(key, self._ttl_seconds)
                        pipe.execute()
                except Exception as re:
                    log_with_route(logging.WARNING, f"Redis write failed, continuing with in-memory buffer: {str(re)}")

            # Broadcast to WebSocket connections
            await self._broadcast_to_websockets({
                'device_uuid': device_uuid,
                'metric_type': metric_type,
                'value': value,
                'timestamp': timestamp
            })

            # Log every 100th metric to reduce spam (only for monitoring)
            if len(self.metrics_buffer[metric_key]) % 100 == 0:
                log_with_route(logging.INFO,
                    f"Processed {len(self.metrics_buffer[metric_key])} metrics for {metric_key}")

        except Exception as e:
            log_with_route(logging.ERROR, f"Error handling system metric: {str(e)}")

    async def _broadcast_to_websockets(self, data):
        """Send data to all connected WebSocket clients"""
        if not self.active_connections:
            return

        message = json.dumps(data)
        disconnected = set()

        for websocket in self.active_connections:
            try:
                await websocket.send(message)
            except Exception:
                disconnected.add(websocket)

        # Clean up disconnected clients
        self.active_connections -= disconnected

    def get_recent_metrics(self, device_uuid: str, metric_type: str, limit: int = 50) -> list:
        """Get recent metrics for a device and metric type"""
        # First try Redis shared buffer
        r = self._get_redis()
        if r is not None:
            try:
                key = self._redis_key(device_uuid, metric_type)
                # Redis list is newest-first; fetch and reverse to oldest-first
                items = r.lrange(key, 0, max(0, limit - 1))
                if items:
                    result = [json.loads(x) for x in reversed(items)]
                    return result
            except Exception as re:
                log_with_route(logging.WARNING, f"Redis read failed, falling back to in-memory: {str(re)}")

        # Fallback to in-memory buffer in this process
        metric_key = f"{device_uuid}.{metric_type}"
        buffer = self.metrics_buffer.get(metric_key, deque())
        return list(buffer)[-limit:] if buffer else []

    def get_all_device_metrics(self, device_uuid: str) -> Dict[str, list]:
        """Get all recent metrics for a device"""
        device_metrics = {}
        
        for metric_key, buffer in self.metrics_buffer.items():
            if metric_key.startswith(f"{device_uuid}."):
                metric_type = metric_key.split('.', 1)[1]
                device_metrics[metric_type] = list(buffer)
        
        return device_metrics
    
    def get_monitored_devices(self) -> list:
        """Get list of devices currently being monitored"""
        devices = set()
        for metric_key in self.metrics_buffer.keys():
            device_uuid = metric_key.split('.')[0]
            devices.add(device_uuid)
        
        return list(devices)
    
    def add_websocket_connection(self, websocket):
        """Add WebSocket connection for real-time updates"""
        self.active_connections.add(websocket)
        log_with_route(logging.DEBUG, f"Added WebSocket connection. Total: {len(self.active_connections)}")
    
    def remove_websocket_connection(self, websocket):
        """Remove WebSocket connection"""
        self.active_connections.discard(websocket)
        log_with_route(logging.DEBUG, f"Removed WebSocket connection. Total: {len(self.active_connections)}")
    
    def stop_monitoring(self):
        """Stop NATS monitoring"""
        self.running = False
        log_with_route(logging.INFO, "Stopped NATS demo system metrics monitoring")
    
    def clear_metrics(self, device_uuid: str = None):
        """Clear metrics buffer (for testing/cleanup)"""
        if device_uuid:
            # Clear metrics for specific device
            keys_to_remove = [key for key in self.metrics_buffer.keys() if key.startswith(f"{device_uuid}.")]
            for key in keys_to_remove:
                del self.metrics_buffer[key]
            log_with_route(logging.INFO, f"Cleared metrics for device {device_uuid}")
        else:
            # Clear all metrics
            self.metrics_buffer.clear()
            log_with_route(logging.INFO, "Cleared all metrics")

# Global instance for the demo
system_metrics_handler = SystemMetricsHandler()
