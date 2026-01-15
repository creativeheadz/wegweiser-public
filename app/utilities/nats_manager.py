# Filepath: app/utilities/nats_manager.py
"""
NATS Connection Manager for Wegweiser Agent Communication

Provides tenant-aware NATS connection management with strict isolation,
authentication, and subject validation.
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, Optional, Any, Callable, List
from dataclasses import dataclass
from contextlib import asynccontextmanager

try:
    import nats
    from nats.aio.client import Client as NATS
    from nats.js import JetStreamContext
    from nats.errors import TimeoutError, ConnectionClosedError
    NATS_AVAILABLE = True
except ImportError as e:
    # NATS not available, create dummy classes
    NATS_AVAILABLE = False
    NATS = None
    JetStreamContext = None
    TimeoutError = Exception
    ConnectionClosedError = Exception
    import logging
    logging.warning(f"NATS not available: {e}. NATS functionality will be disabled.")

from app.utilities.app_logging_helper import log_with_route
from app.models import Tenants, Devices


@dataclass
class TenantNATSCredentials:
    """NATS credentials for a specific tenant"""
    tenant_uuid: str
    username: str
    password: str
    permissions: Dict[str, List[str]]


@dataclass
class NATSMessage:
    """Structured NATS message with tenant context"""
    tenant_uuid: str
    device_uuid: str
    message_type: str
    payload: Dict[str, Any]
    timestamp: int
    message_id: str


class NATSSubjectValidator:
    """Validates and constructs NATS subjects with tenant isolation"""
    
    @staticmethod
    def validate_tenant_uuid(tenant_uuid: str) -> bool:
        """Validate tenant UUID format"""
        try:
            uuid.UUID(tenant_uuid)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def validate_device_uuid(device_uuid: str) -> bool:
        """Validate device UUID format"""
        try:
            uuid.UUID(device_uuid)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def construct_subject(tenant_uuid: str, device_uuid: str, message_type: str) -> str:
        """Construct a valid NATS subject with tenant isolation"""
        if not NATSSubjectValidator.validate_tenant_uuid(tenant_uuid):
            raise ValueError(f"Invalid tenant UUID: {tenant_uuid}")
        
        if not NATSSubjectValidator.validate_device_uuid(device_uuid):
            raise ValueError(f"Invalid device UUID: {device_uuid}")
        
        # Sanitize message type
        message_type = message_type.replace(".", "_").replace(" ", "_").lower()
        
        return f"tenant.{tenant_uuid}.device.{device_uuid}.{message_type}"
    
    @staticmethod
    def parse_subject(subject: str) -> Dict[str, str]:
        """Parse a NATS subject to extract components"""
        parts = subject.split(".")
        if len(parts) < 5 or parts[0] != "tenant" or parts[2] != "device":
            raise ValueError(f"Invalid subject format: {subject}")
        
        return {
            "tenant_uuid": parts[1],
            "device_uuid": parts[3],
            "message_type": ".".join(parts[4:])
        }
    
    @staticmethod
    def get_tenant_wildcard(tenant_uuid: str) -> str:
        """Get wildcard subject for all tenant messages"""
        if not NATSSubjectValidator.validate_tenant_uuid(tenant_uuid):
            raise ValueError(f"Invalid tenant UUID: {tenant_uuid}")
        return f"tenant.{tenant_uuid}.>"


class NATSConnectionManager:
    """Manages NATS connections with tenant isolation"""

    def __init__(self, nats_url: str = "tls://nats.wegweiser.tech:443"):
        if not NATS_AVAILABLE:
            raise ImportError("NATS library not available. Please install nats-py.")

        self.nats_url = nats_url
        self.connections: Dict[str, NATS] = {}
        self.jetstream_contexts: Dict[str, JetStreamContext] = {}
        self.tenant_credentials: Dict[str, TenantNATSCredentials] = {}
        self._lock = asyncio.Lock()
        
    async def get_tenant_credentials(self, tenant_uuid: str) -> TenantNATSCredentials:
        """Get or generate NATS credentials for a tenant"""
        # Check memory cache first
        if tenant_uuid in self.tenant_credentials:
            return self.tenant_credentials[tenant_uuid]

        # TODO: Check database for existing credentials
        # existing_creds = NATSTenantCredentials.query.filter_by(tenant_uuid=tenant_uuid).first()
        # if existing_creds:
        #     return self._load_credentials_from_db(existing_creds)

        # Generate new credentials for tenant
        username = f"tenant_{tenant_uuid}"
        password = self._generate_password()

        permissions = {
            "publish": [f"tenant.{tenant_uuid}.>"],
            "subscribe": [f"tenant.{tenant_uuid}.>"]
        }

        credentials = TenantNATSCredentials(
            tenant_uuid=tenant_uuid,
            username=username,
            password=password,
            permissions=permissions
        )

        # TODO: Save to database
        # self._save_credentials_to_db(credentials)

        # Cache in memory
        self.tenant_credentials[tenant_uuid] = credentials
        return credentials
    
    def _generate_password(self) -> str:
        """Generate a secure password for NATS authentication"""
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(32))
    
    async def get_connection(self, tenant_uuid: str) -> NATS:
        """Get or create a NATS connection for a tenant"""
        async with self._lock:
            if tenant_uuid in self.connections:
                connection = self.connections[tenant_uuid]
                if connection.is_connected:
                    return connection
                else:
                    # Connection lost, remove and recreate
                    del self.connections[tenant_uuid]
            
            # Create new connection
            credentials = await self.get_tenant_credentials(tenant_uuid)
            
            nc = NATS()
            await nc.connect(
                servers=[self.nats_url],
                user=credentials.username,
                password=credentials.password,
                name=f"wegweiser_tenant_{tenant_uuid}",
                reconnect_time_wait=2,
                max_reconnect_attempts=10,
                error_cb=self._error_callback,
                disconnected_cb=self._disconnected_callback,
                reconnected_cb=self._reconnected_callback
            )
            
            self.connections[tenant_uuid] = nc
            log_with_route(logging.INFO, f"NATS connection established for tenant {tenant_uuid}")
            
            return nc
    
    async def get_jetstream(self, tenant_uuid: str) -> JetStreamContext:
        """Get JetStream context for a tenant"""
        if tenant_uuid not in self.jetstream_contexts:
            nc = await self.get_connection(tenant_uuid)
            js = nc.jetstream()
            
            # Ensure tenant stream exists
            await self._ensure_tenant_stream(js, tenant_uuid)
            
            self.jetstream_contexts[tenant_uuid] = js
        
        return self.jetstream_contexts[tenant_uuid]
    
    async def _ensure_tenant_stream(self, js: JetStreamContext, tenant_uuid: str):
        """Ensure JetStream stream exists for tenant"""
        stream_name = f"TENANT_{tenant_uuid.replace('-', '_')}_DEVICES"
        
        try:
            await js.stream_info(stream_name)
            log_with_route(logging.DEBUG, f"Stream {stream_name} already exists")
        except Exception:
            # Stream doesn't exist, create it
            from nats.js.api import StreamConfig
            
            config = StreamConfig(
                name=stream_name,
                subjects=[f"tenant.{tenant_uuid}.device.>"],
                retention="limits",
                max_age=86400,  # 24 hours in seconds
                max_msgs=10000,
                storage="file"
            )
            
            await js.add_stream(config)
            log_with_route(logging.INFO, f"Created JetStream stream {stream_name}")
    
    async def _error_callback(self, error):
        """Handle NATS connection errors"""
        log_with_route(logging.ERROR, f"NATS error: {error}")
    
    async def _disconnected_callback(self):
        """Handle NATS disconnection"""
        log_with_route(logging.WARNING, "NATS connection lost")
    
    async def _reconnected_callback(self):
        """Handle NATS reconnection"""
        log_with_route(logging.INFO, "NATS connection restored")
    
    async def close_connection(self, tenant_uuid: str):
        """Close NATS connection for a tenant"""
        async with self._lock:
            if tenant_uuid in self.connections:
                await self.connections[tenant_uuid].close()
                del self.connections[tenant_uuid]
                
            if tenant_uuid in self.jetstream_contexts:
                del self.jetstream_contexts[tenant_uuid]
    
    async def close_all_connections(self):
        """Close all NATS connections"""
        async with self._lock:
            for tenant_uuid in list(self.connections.keys()):
                await self.close_connection(tenant_uuid)


class NATSPublisher:
    """Publishes messages to NATS with tenant isolation"""
    
    def __init__(self, connection_manager: NATSConnectionManager):
        self.connection_manager = connection_manager
    
    async def publish_message(self, tenant_uuid: str, device_uuid: str, 
                            message_type: str, payload: Dict[str, Any],
                            use_jetstream: bool = False) -> bool:
        """Publish a message to NATS"""
        try:
            subject = NATSSubjectValidator.construct_subject(tenant_uuid, device_uuid, message_type)
            
            message = NATSMessage(
                tenant_uuid=tenant_uuid,
                device_uuid=device_uuid,
                message_type=message_type,
                payload=payload,
                timestamp=int(time.time()),
                message_id=str(uuid.uuid4())
            )
            
            message_data = json.dumps({
                "tenant_uuid": message.tenant_uuid,
                "device_uuid": message.device_uuid,
                "message_type": message.message_type,
                "payload": message.payload,
                "timestamp": message.timestamp,
                "message_id": message.message_id
            }).encode()
            
            if use_jetstream:
                js = await self.connection_manager.get_jetstream(tenant_uuid)
                await js.publish(subject, message_data)
            else:
                nc = await self.connection_manager.get_connection(tenant_uuid)
                await nc.publish(subject, message_data)
            
            log_with_route(logging.DEBUG, f"Published message to {subject}")
            return True
            
        except Exception as e:
            log_with_route(logging.ERROR, f"Failed to publish message: {str(e)}")
            return False


class NATSSubscriber:
    """Subscribes to NATS messages with tenant isolation"""
    
    def __init__(self, connection_manager: NATSConnectionManager):
        self.connection_manager = connection_manager
        self.subscriptions: Dict[str, Any] = {}
    
    async def subscribe_to_tenant(self, tenant_uuid: str, 
                                 message_handler: Callable[[NATSMessage], None],
                                 message_types: Optional[List[str]] = None) -> str:
        """Subscribe to all messages for a tenant"""
        try:
            nc = await self.connection_manager.get_connection(tenant_uuid)
            
            if message_types:
                # Subscribe to specific message types using wildcards
                subjects = [
                    f"tenant.{tenant_uuid}.device.*.{msg_type}"
                    for msg_type in message_types
                ]
            else:
                # Subscribe to all tenant messages
                subjects = [NATSSubjectValidator.get_tenant_wildcard(tenant_uuid)]
            
            async def wrapped_handler(msg):
                try:
                    data = json.loads(msg.data.decode())

                    # Validate required fields for tenant messages
                    required_fields = ["tenant_uuid", "device_uuid", "message_type", "payload", "timestamp", "message_id"]
                    missing_fields = [field for field in required_fields if field not in data]

                    if missing_fields:
                        log_with_route(logging.DEBUG, f"Skipping message with missing fields {missing_fields}. Subject: {msg.subject}, Data: {data}")
                        return

                    nats_message = NATSMessage(
                        tenant_uuid=data["tenant_uuid"],
                        device_uuid=data["device_uuid"],
                        message_type=data["message_type"],
                        payload=data["payload"],
                        timestamp=data["timestamp"],
                        message_id=data["message_id"]
                    )
                    await message_handler(nats_message)
                except json.JSONDecodeError as e:
                    log_with_route(logging.WARNING, f"Failed to parse JSON message: {str(e)}")
                except Exception as e:
                    log_with_route(logging.ERROR, f"Error handling message: {str(e)}")
            
            subscription_id = str(uuid.uuid4())
            
            for subject in subjects:
                sub = await nc.subscribe(subject, cb=wrapped_handler)
                self.subscriptions[f"{subscription_id}_{subject}"] = sub
            
            log_with_route(logging.INFO, f"Subscribed to tenant {tenant_uuid} messages")
            return subscription_id
            
        except Exception as e:
            log_with_route(logging.ERROR, f"Failed to subscribe: {str(e)}")
            raise
    
    async def unsubscribe(self, subscription_id: str):
        """Unsubscribe from messages"""
        keys_to_remove = [key for key in self.subscriptions.keys() if key.startswith(subscription_id)]
        
        for key in keys_to_remove:
            sub = self.subscriptions[key]
            await sub.unsubscribe()
            del self.subscriptions[key]


# Global connection manager instance
nats_manager = NATSConnectionManager()
