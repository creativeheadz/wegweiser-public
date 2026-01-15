# Filepath: app/routes/nats/agent_management.py
"""
NATS Agent Management Routes

Handles agent lifecycle management, registration, and administrative operations
for NATS-based agents.
"""

import json
import logging
import time
import uuid
from typing import Dict, Any

from flask import request, jsonify, current_app

from app import csrf
from app.models import db, Devices, Tenants, Groups, Organisations, Messages, Conversations
from app.utilities.app_logging_helper import log_with_route
try:
    from app.utilities.nats_manager import nats_manager, NATSPublisher, NATS_AVAILABLE
except ImportError:
    NATS_AVAILABLE = False
    nats_manager = None
    NATSPublisher = None

from . import nats_bp


def require_nats(f):
    """Decorator to check if NATS is available"""
    def wrapper(*args, **kwargs):
        if not NATS_AVAILABLE:
            return jsonify({"error": "NATS functionality not available"}), 503
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper


@nats_bp.route('/agent/register', methods=['POST'])
@csrf.exempt
def register_nats_agent():
    """Register a new NATS-based agent (parallel to existing registration)"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        groupuuid = data.get('groupuuid')
        devicename = data.get('devicename')
        hardwareinfo = data.get('hardwareinfo')
        agentpubpem = data.get('agentpubpem')
        
        if not groupuuid:
            log_with_route(logging.ERROR, "No groupuuid specified for NATS agent registration")
            return jsonify({'error': 'groupuuid is required'}), 400
        
        if not devicename:
            return jsonify({'error': 'devicename is required'}), 400
        
        log_with_route(logging.INFO, f"Request to register new NATS agent ({devicename}) in group {groupuuid}")
        
        # Verify group exists
        group = Groups.query.filter_by(groupuuid=groupuuid).first()
        if not group:
            log_with_route(logging.ERROR, f'Group {groupuuid} not found for NATS agent registration')
            return jsonify({'error': 'Group does not exist'}), 400
        
        # Create new device
        device_uuid = str(uuid.uuid4())
        new_device = Devices(
            deviceuuid=device_uuid,
            devicename=devicename,
            hardwareinfo=hardwareinfo,
            agent_public_key=agentpubpem,
            groupuuid=groupuuid,
            orguuid=group.orguuid,
            tenantuuid=group.tenantuuid,
            created_at=int(time.time())
        )
        
        db.session.add(new_device)
        
        # Create conversation for the device (for compatibility)
        system_useruuid = "00000000-0000-0000-0000-000000000000"
        
        from app.routes.ai.ai import get_or_create_conversation
        conversation = get_or_create_conversation(device_uuid, 'device')
        
        # Create registration message
        message = Messages(
            messageuuid=str(uuid.uuid4()),
            conversationuuid=conversation.conversationuuid,
            useruuid=system_useruuid,
            tenantuuid=group.tenantuuid,
            entityuuid=device_uuid,
            entity_type='device',
            title="New NATS Agent Registered",
            content=f"A new NATS-based agent '{devicename}' has registered in group '{group.groupname}'",
            is_read=False,
            created_at=int(time.time()),
            message_type='chat'
        )
        
        db.session.add(message)
        db.session.commit()
        
        # Generate NATS credentials for the tenant
        tenant_uuid = str(group.tenantuuid)
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            credentials = loop.run_until_complete(nats_manager.get_tenant_credentials(tenant_uuid))
        finally:
            loop.close()
        
        log_with_route(logging.INFO, f"NATS agent registered successfully: {device_uuid}")
        
        return jsonify({
            'success': 'NATS agent registered',
            'deviceuuid': device_uuid,
            'tenant_uuid': tenant_uuid,
            'nats_credentials': {
                'username': credentials.username,
                'password': credentials.password,
                'nats_url': 'tls://nats.wegweiser.tech:443'
            }
        }), 201
        
    except Exception as e:
        log_with_route(logging.ERROR, f'Failed to register NATS agent: {str(e)}')
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@nats_bp.route('/agent/<uuid:device_uuid>/upgrade', methods=['POST'])
@csrf.exempt
def upgrade_agent_to_nats(device_uuid):
    """Upgrade existing agent to NATS communication"""
    try:
        device_uuid_str = str(device_uuid)
        
        # Verify device exists
        device = Devices.query.filter_by(deviceuuid=device_uuid_str).first()
        if not device:
            return jsonify({"error": "Device not found"}), 404
        
        tenant_uuid = str(device.tenantuuid)
        
        # Generate NATS credentials for the tenant
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            credentials = loop.run_until_complete(nats_manager.get_tenant_credentials(tenant_uuid))
        finally:
            loop.close()
        
        # Mark device as NATS-enabled (could add a flag to device model)
        # For now, we'll just return the credentials
        
        log_with_route(logging.INFO, f"Agent upgraded to NATS: {device_uuid_str}")
        
        return jsonify({
            'success': True,
            'message': 'Agent upgraded to NATS',
            'device_uuid': device_uuid_str,
            'tenant_uuid': tenant_uuid,
            'nats_credentials': {
                'username': credentials.username,
                'password': credentials.password,
                'nats_url': 'tls://nats.wegweiser.tech:443'
            }
        }), 200
        
    except Exception as e:
        log_with_route(logging.ERROR, f'Failed to upgrade agent to NATS: {str(e)}')
        return jsonify({'error': str(e)}), 500


@nats_bp.route('/agent/<uuid:device_uuid>/config', methods=['GET'])
def get_agent_nats_config(device_uuid):
    """Get NATS configuration for an agent"""
    try:
        device_uuid_str = str(device_uuid)
        
        # Verify device exists
        device = Devices.query.filter_by(deviceuuid=device_uuid_str).first()
        if not device:
            return jsonify({"error": "Device not found"}), 404
        
        tenant_uuid = str(device.tenantuuid)
        
        # Get NATS credentials
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            credentials = loop.run_until_complete(nats_manager.get_tenant_credentials(tenant_uuid))
        finally:
            loop.close()
        
        # Build configuration
        config = {
            'device_uuid': device_uuid_str,
            'tenant_uuid': tenant_uuid,
            'device_name': device.devicename,
            'group_uuid': str(device.groupuuid),
            'org_uuid': str(device.orguuid),
            'nats_config': {
                'server_url': 'tls://nats.wegweiser.tech:443',
                'username': credentials.username,
                'password': credentials.password,
                'subjects': {
                    'heartbeat': f'tenant.{tenant_uuid}.device.{device_uuid_str}.heartbeat',
                    'commands': f'tenant.{tenant_uuid}.device.{device_uuid_str}.command',
                    'responses': f'tenant.{tenant_uuid}.device.{device_uuid_str}.response',
                    'status': f'tenant.{tenant_uuid}.device.{device_uuid_str}.status',
                    'monitoring': f'tenant.{tenant_uuid}.device.{device_uuid_str}.monitoring'
                }
            },
            'flask_endpoints': {
                'heartbeat': f'/api/nats/device/{device_uuid_str}/heartbeat',
                'status': f'/api/nats/device/{device_uuid_str}/status'
            }
        }
        
        return jsonify({
            'success': True,
            'config': config
        }), 200
        
    except Exception as e:
        log_with_route(logging.ERROR, f'Failed to get agent config: {str(e)}')
        return jsonify({'error': str(e)}), 500


@nats_bp.route('/tenant/<uuid:tenant_uuid>/agents/broadcast', methods=['POST'])
@csrf.exempt
def broadcast_to_tenant_agents(tenant_uuid):
    """Broadcast message to all agents in a tenant"""
    try:
        tenant_uuid_str = str(tenant_uuid)
        
        # Verify tenant exists
        tenant = Tenants.query.filter_by(tenantuuid=tenant_uuid_str).first()
        if not tenant:
            return jsonify({"error": "Tenant not found"}), 404
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        message_type = data.get('message_type', 'broadcast')
        payload = data.get('payload', {})
        
        # Get all devices for tenant
        devices = Devices.query.filter_by(tenantuuid=tenant_uuid_str).all()
        
        if not devices:
            return jsonify({
                'success': True,
                'message': 'No devices found for tenant',
                'devices_count': 0
            }), 200
        
        # Publish to all devices
        publisher = NATSPublisher(nats_manager)
        successful_sends = 0
        
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            for device in devices:
                device_uuid_str = str(device.deviceuuid)
                
                broadcast_payload = {
                    'broadcast_id': str(uuid.uuid4()),
                    'message_type': message_type,
                    'payload': payload,
                    'timestamp': int(time.time()),
                    'sender': 'flask_api'
                }
                
                success = loop.run_until_complete(publisher.publish_message(
                    tenant_uuid=tenant_uuid_str,
                    device_uuid=device_uuid_str,
                    message_type=message_type,
                    payload=broadcast_payload,
                    use_jetstream=True
                ))
                
                if success:
                    successful_sends += 1
        finally:
            loop.close()
        
        log_with_route(logging.INFO, f"Broadcast sent to {successful_sends}/{len(devices)} devices in tenant {tenant_uuid_str}")
        
        return jsonify({
            'success': True,
            'message': 'Broadcast completed',
            'tenant_uuid': tenant_uuid_str,
            'total_devices': len(devices),
            'successful_sends': successful_sends
        }), 200
        
    except Exception as e:
        log_with_route(logging.ERROR, f'Failed to broadcast to tenant agents: {str(e)}')
        return jsonify({'error': str(e)}), 500


@nats_bp.route('/agent/<uuid:device_uuid>/restart', methods=['POST'])
@csrf.exempt
def restart_agent(device_uuid):
    """Send restart command to a specific agent"""
    try:
        device_uuid_str = str(device_uuid)
        
        # Verify device exists
        device = Devices.query.filter_by(deviceuuid=device_uuid_str).first()
        if not device:
            return jsonify({"error": "Device not found"}), 404
        
        tenant_uuid = str(device.tenantuuid)
        
        # Send restart command
        publisher = NATSPublisher(nats_manager)
        command_id = str(uuid.uuid4())
        
        command_payload = {
            "command": "restart",
            "command_id": command_id,
            "parameters": {},
            "timestamp": int(time.time()),
            "sender": "flask_api"
        }
        
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            success = loop.run_until_complete(publisher.publish_message(
                tenant_uuid=tenant_uuid,
                device_uuid=device_uuid_str,
                message_type="command",
                payload=command_payload,
                use_jetstream=True
            ))
        finally:
            loop.close()
        
        if success:
            log_with_route(logging.INFO, f"Restart command sent to agent {device_uuid_str}")
            return jsonify({
                "success": True,
                "command_id": command_id,
                "message": "Restart command sent"
            }), 200
        else:
            return jsonify({"error": "Failed to send restart command"}), 500
        
    except Exception as e:
        log_with_route(logging.ERROR, f"Error sending restart command: {str(e)}")
        return jsonify({"error": str(e)}), 500
