# Filepath: app/routes/nats/device_api.py
"""
NATS Device API Routes

Handles device-related NATS operations including credential management,
tenant lookup, and device status updates.
"""

import json
import logging
import time
import uuid
from typing import Dict, Any

from flask import request, jsonify, current_app

from app import csrf
from app.models import db, Devices, Tenants, Groups, DeviceConnectivity
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


@nats_bp.route('/device/<uuid:device_uuid>/tenant', methods=['GET'])
@require_nats
def get_device_tenant(device_uuid):
    """Get tenant UUID for a device"""
    try:
        device_uuid_str = str(device_uuid)

        device = Devices.query.filter_by(deviceuuid=device_uuid_str).first()
        if not device:
            # Try to restore from backup before returning error
            from app.utilities.device_restore import find_device_backup, restore_device_from_backup

            backup_path = find_device_backup(device_uuid_str)
            if backup_path:
                log_with_route(logging.INFO, f"Device {device_uuid_str} not found, attempting restoration from backup")
                success, message = restore_device_from_backup(device_uuid_str, backup_path)
                if success:
                    log_with_route(logging.INFO, f"Successfully restored device {device_uuid_str} from backup")
                    # Re-query the device after restoration
                    device = Devices.query.filter_by(deviceuuid=device_uuid_str).first()
                else:
                    log_with_route(logging.ERROR, f"Failed to restore device {device_uuid_str}: {message}")

            if not device:
                log_with_route(logging.ERROR, f"Device not found: {device_uuid_str}")
                return jsonify({"error": "Device not found"}), 404
        
        return jsonify({
            "success": True,
            "device_uuid": device_uuid_str,
            "tenant_uuid": str(device.tenantuuid),
            "group_uuid": str(device.groupuuid),
            "org_uuid": str(device.orguuid)
        }), 200
        
    except Exception as e:
        log_with_route(logging.ERROR, f"Error getting device tenant: {str(e)}")
        return jsonify({"error": str(e)}), 500


@nats_bp.route('/device/<uuid:device_uuid>/credentials', methods=['GET'])
def get_device_nats_credentials(device_uuid):
    """Get NATS credentials for a device"""
    try:
        device_uuid_str = str(device_uuid)

        # Verify device exists and get tenant
        device = Devices.query.filter_by(deviceuuid=device_uuid_str).first()
        if not device:
            log_with_route(logging.ERROR, f"Device not found: {device_uuid_str}")
            return jsonify({"error": "Device not found"}), 404

        tenant_uuid = str(device.tenantuuid)

        # Get NATS credentials for the tenant (synchronous call for now)
        # TODO: Make this async when Flask supports async routes
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            credentials = loop.run_until_complete(nats_manager.get_tenant_credentials(tenant_uuid))
        finally:
            loop.close()

        return jsonify({
            "success": True,
            "device_uuid": device_uuid_str,
            "tenant_uuid": tenant_uuid,
            "credentials": {
                "username": credentials.username,
                "password": credentials.password,
                "nats_url": "tls://nats.wegweiser.tech:443"
            }
        }), 200

    except Exception as e:
        log_with_route(logging.ERROR, f"Error getting NATS credentials: {str(e)}")
        return jsonify({"error": str(e)}), 500


@nats_bp.route('/device/<string:device_uuid>/heartbeat', methods=['POST'])
@csrf.exempt
def process_device_heartbeat(device_uuid):
    """Process device heartbeat from NATS agent"""
    try:
        try:
            device_uuid_obj = uuid.UUID(str(device_uuid))
        except (ValueError, AttributeError, TypeError):
            log_with_route(logging.WARNING, f"Invalid device_uuid in heartbeat path: {device_uuid}")
            return jsonify({
                "error": "Invalid device_uuid",
                "detail": "device_uuid must be a valid UUID in the URL path"
            }), 400

        device_uuid_str = str(device_uuid_obj)
        log_with_route(logging.INFO, f"Received heartbeat from device {device_uuid_str}")

        # Get JSON data from request
        data = request.get_json()
        if not data:
            log_with_route(logging.ERROR, f"No JSON data in heartbeat from {device_uuid_str}")
            return jsonify({"error": "No JSON data provided"}), 400

        # Verify device exists (attempt on-demand restore from backup like other routes)
        device = Devices.query.filter_by(deviceuuid=device_uuid_str).first()
        if not device:
            try:
                from app.utilities.device_restore import find_device_backup, restore_device_from_backup
                backup_path = find_device_backup(device_uuid_str)
                if backup_path:
                    log_with_route(logging.INFO, f"Heartbeat for unknown device {device_uuid_str}; attempting restore from {backup_path}")
                    success, message = restore_device_from_backup(device_uuid_str, backup_path)
                    if success:
                        # Re-query after restore
                        device = Devices.query.filter_by(deviceuuid=device_uuid_str).first()
                        log_with_route(logging.INFO, f"Device {device_uuid_str} restored from backup; proceeding with heartbeat")
                    else:
                        log_with_route(logging.ERROR, f"Restore failed for device {device_uuid_str}: {message}")
            except Exception as re:
                log_with_route(logging.ERROR, f"Restore attempt errored for {device_uuid_str}: {re}")

        if not device:
            log_with_route(logging.ERROR, f"Device not found: {device_uuid_str}")
            return jsonify({"error": "Device not found"}), 404

        # Verify tenant matches
        if str(device.tenantuuid) != data.get('tenant_uuid'):
            log_with_route(logging.ERROR, f"Tenant mismatch for device {device_uuid_str}: expected {device.tenantuuid}, got {data.get('tenant_uuid')}")
            return jsonify({"error": "Tenant mismatch"}), 403
        
        # Update device connectivity
        current_time = int(time.time())
        
        # Get or create connectivity record
        connectivity = DeviceConnectivity.query.filter_by(deviceuuid=device_uuid_obj).first()
        
        if connectivity:
            # Update existing record
            connectivity.is_online = True
            connectivity.last_heartbeat = current_time
            connectivity.last_seen_online = current_time
            connectivity.connection_type = "nats"
            connectivity.agent_version = data.get('agent_version')
            
            # Update connection info
            status = data.get('status', {})
            if isinstance(status, str):
                try:
                    status = json.loads(status)
                except (json.JSONDecodeError, TypeError):
                    status = {}

            connection_info = {
                "nats_server": status.get('nats_server') if isinstance(status, dict) else None,
                "session_id": data.get('session_id'),
                "last_heartbeat": current_time,
                "system_info": data.get('system_info', {})
            }
            connectivity.connection_info = connection_info
            
            # Check if status changed
            if not connectivity.is_online:
                connectivity.last_online_change = current_time
        else:
            # Create new connectivity record
            status = data.get('status', {})
            if isinstance(status, str):
                try:
                    status = json.loads(status)
                except (json.JSONDecodeError, TypeError):
                    status = {}

            connection_info = {
                "nats_server": status.get('nats_server') if isinstance(status, dict) else None,
                "session_id": data.get('session_id'),
                "last_heartbeat": current_time,
                "system_info": data.get('system_info', {})
            }
            
            connectivity = DeviceConnectivity(
                deviceuuid=device_uuid_obj,
                is_online=True,
                last_online_change=current_time,
                last_seen_online=current_time,
                last_heartbeat=current_time,
                connection_type="nats",
                agent_version=data.get('agent_version'),
                connection_info=connection_info
            )
            db.session.add(connectivity)
        
        # Update device last_heartbeat field for backward compatibility
        device.last_heartbeat = current_time
        device.is_online = True
        
        db.session.commit()

        log_with_route(logging.INFO, f"✅ Processed NATS heartbeat for device {device_uuid_str} - is_online set to True")

        # Compute current server public key hash for key rotation detection
        from app.models import ServerCore
        import hashlib

        current_key_hash = None
        try:
            server_core = ServerCore.query.first()
            if server_core and server_core.server_public_key:
                current_key_hash = hashlib.sha256(
                    server_core.server_public_key.encode()
                ).hexdigest()
        except Exception as e:
            log_with_route(logging.WARNING, f"Failed to compute key hash: {e}")

        return jsonify({
            "success": True,
            "message": "Heartbeat processed",
            "device_uuid": device_uuid_str,
            "timestamp": current_time,
            "current_key_hash": current_key_hash
        }), 200
        
    except Exception as e:
        import traceback
        log_with_route(logging.ERROR, f"Error processing heartbeat: {str(e)}")
        log_with_route(logging.ERROR, f"Traceback: {traceback.format_exc()}")
        log_with_route(logging.ERROR, f"Request data: {request.get_json()}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@nats_bp.route('/device/<uuid:device_uuid>/command', methods=['POST'])
@csrf.exempt
def send_device_command(device_uuid):
    """Send command to device via NATS"""
    try:
        device_uuid_str = str(device_uuid)
        
        # Get JSON data from request
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        command = data.get('command')
        parameters = data.get('parameters', {})
        
        if not command:
            return jsonify({"error": "Command is required"}), 400
        
        # Verify device exists
        device = Devices.query.filter_by(deviceuuid=device_uuid_str).first()
        if not device:
            log_with_route(logging.ERROR, f"Device not found: {device_uuid_str}")
            return jsonify({"error": "Device not found"}), 404
        
        tenant_uuid = str(device.tenantuuid)
        
        # Generate command ID
        command_id = str(uuid.uuid4())
        
        # Publish command via NATS (synchronous call for now)
        publisher = NATSPublisher(nats_manager)

        command_payload = {
            "command": command,
            "command_id": command_id,
            "parameters": parameters,
            "timestamp": int(time.time()),
            "sender": "flask_api"
        }

        # TODO: Make this async when Flask supports async routes
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            success = loop.run_until_complete(publisher.publish_message(
                tenant_uuid=tenant_uuid,
                device_uuid=device_uuid_str,
                message_type="command",
                payload=command_payload,
                use_jetstream=True  # Use JetStream for reliable delivery
            ))
        finally:
            loop.close()
        
        if success:
            log_with_route(logging.INFO, f"Command sent to device {device_uuid_str}: {command}")
            return jsonify({
                "success": True,
                "command_id": command_id,
                "message": "Command sent successfully"
            }), 200
        else:
            return jsonify({"error": "Failed to send command"}), 500
        
    except Exception as e:
        log_with_route(logging.ERROR, f"Error sending command: {str(e)}")
        return jsonify({"error": str(e)}), 500


@nats_bp.route('/device/<uuid:device_uuid>/status', methods=['GET'])
def get_device_nats_status(device_uuid):
    """Get device status for NATS-connected devices"""
    try:
        device_uuid_str = str(device_uuid)
        
        # Get device and connectivity info
        device = Devices.query.filter_by(deviceuuid=device_uuid_str).first()
        if not device:
            return jsonify({"error": "Device not found"}), 404
        
        connectivity = DeviceConnectivity.query.filter_by(deviceuuid=device_uuid).first()
        
        if not connectivity:
            return jsonify({
                "success": True,
                "device_uuid": device_uuid_str,
                "is_online": False,
                "status": "Unknown",
                "connection_type": "unknown"
            }), 200
        
        # Check if device is stale (no heartbeat in last 2 minutes)
        current_time = int(time.time())
        is_stale = (current_time - connectivity.last_heartbeat) > 120 if connectivity.last_heartbeat else True
        
        status = "Online"
        if not connectivity.is_online:
            status = "Offline"
        elif is_stale:
            status = "Stale"
        
        return jsonify({
            "success": True,
            "device_uuid": device_uuid_str,
            "is_online": connectivity.is_online and not is_stale,
            "status": status,
            "connection_type": connectivity.connection_type,
            "last_heartbeat": connectivity.last_heartbeat,
            "last_seen_online": connectivity.last_seen_online,
            "agent_version": connectivity.agent_version,
            "connection_info": connectivity.connection_info
        }), 200
        
    except Exception as e:
        log_with_route(logging.ERROR, f"Error getting device status: {str(e)}")
        return jsonify({"error": str(e)}), 500


@nats_bp.route('/tenant/<uuid:tenant_uuid>/devices', methods=['GET'])
def get_tenant_devices(tenant_uuid):
    """Get all devices for a tenant with NATS status"""
    try:
        tenant_uuid_str = str(tenant_uuid)
        
        # Verify tenant exists
        tenant = Tenants.query.filter_by(tenantuuid=tenant_uuid_str).first()
        if not tenant:
            return jsonify({"error": "Tenant not found"}), 404
        
        # Get all devices for tenant
        devices = Devices.query.filter_by(tenantuuid=tenant_uuid_str).all()
        
        device_list = []
        for device in devices:
            connectivity = DeviceConnectivity.query.filter_by(deviceuuid=device.deviceuuid).first()
            
            device_info = {
                "device_uuid": str(device.deviceuuid),
                "device_name": device.devicename,
                "group_uuid": str(device.groupuuid),
                "org_uuid": str(device.orguuid),
                "created_at": device.created_at,
                "is_online": False,
                "status": "Unknown",
                "connection_type": "unknown",
                "last_heartbeat": None,
                "agent_version": None
            }
            
            if connectivity:
                current_time = int(time.time())
                is_stale = (current_time - connectivity.last_heartbeat) > 120 if connectivity.last_heartbeat else True
                
                device_info.update({
                    "is_online": connectivity.is_online and not is_stale,
                    "status": "Online" if (connectivity.is_online and not is_stale) else ("Stale" if connectivity.is_online else "Offline"),
                    "connection_type": connectivity.connection_type,
                    "last_heartbeat": connectivity.last_heartbeat,
                    "agent_version": connectivity.agent_version
                })
            
            device_list.append(device_info)
        
        return jsonify({
            "success": True,
            "tenant_uuid": tenant_uuid_str,
            "device_count": len(device_list),
            "devices": device_list
        }), 200
        
    except Exception as e:
        log_with_route(logging.ERROR, f"Error getting tenant devices: {str(e)}")
        return jsonify({"error": str(e)}), 500
