# Filepath: app/handlers/nats/message_handlers.py
"""
NATS Message Handlers

Processes incoming NATS messages with strict tenant isolation and validation.
Handles heartbeats, system information updates, command responses, and monitoring data.
"""

import asyncio
import asyncio
import json
import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime

from app.models import db, Devices, DeviceConnectivity, DeviceStatus, DeviceRealtimeData, Tenants
from app.utilities.app_logging_helper import log_with_route
try:
    from app.utilities.nats_manager import NATSMessage, NATSSubjectValidator, NATS_AVAILABLE
except ImportError:
    NATS_AVAILABLE = False
    NATSMessage = None
    NATSSubjectValidator = None


class NATSMessageHandler:
    """Base class for NATS message handlers with tenant validation"""
    
    def __init__(self):
        self.processed_messages = 0
        self.error_count = 0
        self.last_processed = None
    
    def validate_tenant_context(self, message: NATSMessage) -> bool:
        """Validate that the message tenant context is valid"""
        try:
            # Verify tenant exists
            tenant = Tenants.query.filter_by(tenantuuid=message.tenant_uuid).first()
            if not tenant:
                log_with_route(logging.ERROR, f"Invalid tenant UUID in message: {message.tenant_uuid}")
                return False
            
            # Verify device belongs to tenant
            device = Devices.query.filter_by(
                deviceuuid=message.device_uuid,
                tenantuuid=message.tenant_uuid
            ).first()
            
            if not device:
                log_with_route(logging.ERROR, f"Device {message.device_uuid} not found in tenant {message.tenant_uuid}")
                return False
            
            return True
            
        except Exception as e:
            log_with_route(logging.ERROR, f"Error validating tenant context: {str(e)}")
            return False
    
    async def handle_message(self, message: NATSMessage) -> bool:
        """Handle a NATS message with validation"""
        try:
            # Validate tenant context first
            if not self.validate_tenant_context(message):
                self.error_count += 1
                return False
            
            # Process the message
            result = await self.process_message(message)
            
            if result:
                self.processed_messages += 1
                self.last_processed = int(time.time())
            else:
                self.error_count += 1
            
            return result
            
        except Exception as e:
            log_with_route(logging.ERROR, f"Error handling message: {str(e)}")
            self.error_count += 1
            return False
    
    async def process_message(self, message: NATSMessage) -> bool:
        """Override this method in subclasses"""
        raise NotImplementedError("Subclasses must implement process_message")


class HeartbeatHandler(NATSMessageHandler):
    """Handles device heartbeat messages"""
    
    async def process_message(self, message: NATSMessage) -> bool:
        """Process heartbeat message"""
        try:
            payload = message.payload
            current_time = int(time.time())
            
            # Get device
            device = Devices.query.filter_by(deviceuuid=message.device_uuid).first()
            if not device:
                return False
            
            # Update device connectivity
            connectivity = DeviceConnectivity.query.filter_by(deviceuuid=message.device_uuid).first()
            
            if connectivity:
                # Update existing record
                was_offline = not connectivity.is_online
                connectivity.is_online = True
                connectivity.last_heartbeat = current_time
                connectivity.last_seen_online = current_time
                connectivity.connection_type = "nats"
                
                # Update connection info
                connection_info = {
                    "nats_server": payload.get('status', {}).get('nats_server'),
                    "session_id": payload.get('session_id'),
                    "last_heartbeat": current_time,
                    "system_info": payload.get('system_info', {}),
                    "uptime": payload.get('status', {}).get('uptime')
                }
                connectivity.connection_info = connection_info
                
                # Track status changes
                if was_offline:
                    connectivity.last_online_change = current_time
                    log_with_route(logging.INFO, f"Device {message.device_uuid} came online via NATS")
            else:
                # Create new connectivity record
                connection_info = {
                    "nats_server": payload.get('status', {}).get('nats_server'),
                    "session_id": payload.get('session_id'),
                    "last_heartbeat": current_time,
                    "system_info": payload.get('system_info', {}),
                    "uptime": payload.get('status', {}).get('uptime')
                }
                
                connectivity = DeviceConnectivity(
                    deviceuuid=message.device_uuid,
                    is_online=True,
                    last_online_change=current_time,
                    last_seen_online=current_time,
                    last_heartbeat=current_time,
                    connection_type="nats",
                    connection_info=connection_info
                )
                db.session.add(connectivity)
                log_with_route(logging.INFO, f"Created NATS connectivity record for device {message.device_uuid}")
            
            # Update device fields for backward compatibility
            device.last_heartbeat = current_time
            device.is_online = True
            
            # Update system information if provided
            system_info = payload.get('system_info')
            if system_info:
                await self._update_system_info(message.device_uuid, system_info)
            
            db.session.commit()
            
            log_with_route(logging.DEBUG, f"Processed heartbeat for device {message.device_uuid}")
            return True
            
        except Exception as e:
            log_with_route(logging.ERROR, f"Error processing heartbeat: {str(e)}")
            db.session.rollback()
            return False
    
    async def _update_system_info(self, device_uuid: str, system_info: Dict[str, Any]):
        """Update device system information"""
        try:
            # Update DeviceStatus if it exists
            device_status = DeviceStatus.query.filter_by(deviceuuid=device_uuid).first()
            
            if device_status:
                # Update relevant fields
                if 'hostname' in system_info:
                    device_status.system_name = system_info['hostname']
                if 'platform' in system_info:
                    device_status.agent_platform = system_info['platform']
                if 'cpu_count' in system_info:
                    device_status.cpu_count = system_info['cpu_count']
                if 'boot_time' in system_info:
                    device_status.boot_time = system_info['boot_time']
                
                device_status.last_update = int(time.time())
            
            # Store detailed system info in realtime data
            realtime_data = DeviceRealtimeData.query.filter_by(
                deviceuuid=device_uuid,
                data_type='system_info'
            ).first()
            
            if realtime_data:
                realtime_data.data_value = json.dumps(system_info)
                realtime_data.last_updated = int(time.time())
            else:
                realtime_data = DeviceRealtimeData(
                    deviceuuid=device_uuid,
                    data_type='system_info',
                    data_value=json.dumps(system_info),
                    last_updated=int(time.time())
                )
                db.session.add(realtime_data)
            
        except Exception as e:
            log_with_route(logging.ERROR, f"Error updating system info: {str(e)}")


class CommandResponseHandler(NATSMessageHandler):
    """Handles command response messages from agents"""
    
    async def process_message(self, message: NATSMessage) -> bool:
        """Process command response message"""
        try:
            payload = message.payload
            command_id = payload.get('command_id')
            result = payload.get('result', {})
            
            if not command_id:
                log_with_route(logging.ERROR, "Command response missing command_id")
                return False
            
            # Store command response in realtime data
            response_data = {
                'command_id': command_id,
                'device_uuid': message.device_uuid,
                'tenant_uuid': message.tenant_uuid,
                'result': result,
                'timestamp': payload.get('timestamp', int(time.time())),
                'message_timestamp': message.timestamp
            }
            
            realtime_data = DeviceRealtimeData(
                deviceuuid=message.device_uuid,
                data_type=f'command_response_{command_id}',
                data_value=json.dumps(response_data),
                last_updated=int(time.time())
            )
            
            db.session.add(realtime_data)
            db.session.commit()
            
            log_with_route(logging.INFO, f"Processed command response {command_id} from device {message.device_uuid}")
            return True
            
        except Exception as e:
            log_with_route(logging.ERROR, f"Error processing command response: {str(e)}")
            db.session.rollback()
            return False


class StatusUpdateHandler(NATSMessageHandler):
    """Handles device status update messages"""
    
    async def process_message(self, message: NATSMessage) -> bool:
        """Process status update message"""
        try:
            payload = message.payload
            
            # Store status update in realtime data
            status_data = {
                'device_uuid': message.device_uuid,
                'tenant_uuid': message.tenant_uuid,
                'status_data': payload,
                'timestamp': message.timestamp
            }
            
            # Check if this is a specific type of status update
            data_type = 'status_update'
            if 'cpu_usage' in payload:
                data_type = 'performance_metrics'
            elif 'memory_usage' in payload:
                data_type = 'memory_metrics'
            elif 'disk_usage' in payload:
                data_type = 'disk_metrics'
            
            realtime_data = DeviceRealtimeData.query.filter_by(
                deviceuuid=message.device_uuid,
                data_type=data_type
            ).first()
            
            if realtime_data:
                realtime_data.data_value = json.dumps(status_data)
                realtime_data.last_updated = int(time.time())
            else:
                realtime_data = DeviceRealtimeData(
                    deviceuuid=message.device_uuid,
                    data_type=data_type,
                    data_value=json.dumps(status_data),
                    last_updated=int(time.time())
                )
                db.session.add(realtime_data)
            
            db.session.commit()
            
            log_with_route(logging.DEBUG, f"Processed status update from device {message.device_uuid}")
            return True
            
        except Exception as e:
            log_with_route(logging.ERROR, f"Error processing status update: {str(e)}")
            db.session.rollback()
            return False


class MonitoringDataHandler(NATSMessageHandler):
    """Handles monitoring data messages from agents"""
    
    async def process_message(self, message: NATSMessage) -> bool:
        """Process monitoring data message"""
        try:
            payload = message.payload
            
            # Store monitoring data
            monitoring_data = {
                'device_uuid': message.device_uuid,
                'tenant_uuid': message.tenant_uuid,
                'monitoring_data': payload,
                'timestamp': message.timestamp,
                'data_type': payload.get('monitoring_type', 'general')
            }
            
            data_type = f"monitoring_{payload.get('monitoring_type', 'general')}"
            
            realtime_data = DeviceRealtimeData(
                deviceuuid=message.device_uuid,
                data_type=data_type,
                data_value=json.dumps(monitoring_data),
                last_updated=int(time.time())
            )
            
            db.session.add(realtime_data)
            db.session.commit()
            
            log_with_route(logging.DEBUG, f"Processed monitoring data from device {message.device_uuid}")
            return True
            
        except Exception as e:
            log_with_route(logging.ERROR, f"Error processing monitoring data: {str(e)}")
            db.session.rollback()
            return False


class NATSMessageRouter:
    """Routes NATS messages to appropriate handlers"""
    
    def __init__(self):
        self.handlers = {
            'heartbeat': HeartbeatHandler(),
            'response': CommandResponseHandler(),
            'status': StatusUpdateHandler(),
            'monitoring': MonitoringDataHandler()
        }
        self.total_messages = 0
        self.routing_errors = 0
    
    async def route_message(self, message: NATSMessage) -> bool:
        """Route message to appropriate handler"""
        try:
            self.total_messages += 1
            
            # Determine handler based on message type
            handler = self.handlers.get(message.message_type)
            
            if not handler:
                log_with_route(logging.WARNING, f"No handler for message type: {message.message_type}")
                self.routing_errors += 1
                return False
            
            # Process message with handler
            result = await handler.handle_message(message)
            
            if not result:
                self.routing_errors += 1
            
            return result
            
        except Exception as e:
            log_with_route(logging.ERROR, f"Error routing message: {str(e)}")
            self.routing_errors += 1
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get routing statistics"""
        handler_stats = {}
        for msg_type, handler in self.handlers.items():
            handler_stats[msg_type] = {
                'processed_messages': handler.processed_messages,
                'error_count': handler.error_count,
                'last_processed': handler.last_processed
            }
        
        return {
            'total_messages': self.total_messages,
            'routing_errors': self.routing_errors,
            'handler_stats': handler_stats
        }


# Global message router instance
message_router = NATSMessageRouter()


class NATSMessageService:
    """Service for processing NATS messages in Flask application"""

    def __init__(self):
        self.running = False
        self.subscribers = {}
        self.router = message_router

    async def start_message_processing(self):
        """Start processing NATS messages for all tenants"""
        try:
            self.running = True
            log_with_route(logging.INFO, "Starting NATS message processing service")

            # Get all tenants and set up subscriptions
            from app.utilities.nats_manager import nats_manager, NATSSubscriber

            tenants = Tenants.query.all()
            log_with_route(logging.INFO, f"Found {len(tenants)} tenants to subscribe to")

            subscriber = NATSSubscriber(nats_manager)

            for tenant in tenants:
                tenant_uuid = str(tenant.tenantuuid)

                try:
                    log_with_route(logging.INFO, f"Subscribing to tenant {tenant_uuid}...")

                    # Subscribe to all messages for this tenant
                    subscription_id = await subscriber.subscribe_to_tenant(
                        tenant_uuid=tenant_uuid,
                        message_handler=self._handle_tenant_message,
                        message_types=['heartbeat', 'response', 'status', 'monitoring']
                    )

                    self.subscribers[tenant_uuid] = subscription_id
                    log_with_route(logging.INFO, f"✓ Subscribed to NATS messages for tenant {tenant_uuid}")

                except Exception as e:
                    log_with_route(logging.ERROR, f"✗ Failed to subscribe to tenant {tenant_uuid}: {str(e)}")
                    import traceback
                    log_with_route(logging.ERROR, f"Traceback: {traceback.format_exc()}")

            log_with_route(logging.INFO, f"NATS message processing started for {len(self.subscribers)} tenants")

            # Keep the service running
            while self.running:
                await asyncio.sleep(1)

        except Exception as e:
            self.running = False
            log_with_route(logging.ERROR, f"Failed to start NATS message processing: {str(e)}")
            import traceback
            log_with_route(logging.ERROR, f"Traceback: {traceback.format_exc()}")
            raise

    async def _handle_tenant_message(self, message: NATSMessage):
        """Handle incoming tenant message"""
        try:
            await self.router.route_message(message)
        except Exception as e:
            log_with_route(logging.ERROR, f"Error handling tenant message: {str(e)}")

    def get_service_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        return {
            'running': self.running,
            'active_subscriptions': len(self.subscribers),
            'subscribed_tenants': list(self.subscribers.keys()),
            'router_stats': self.router.get_stats()
        }


# Global message service instance
nats_message_service = NATSMessageService()
