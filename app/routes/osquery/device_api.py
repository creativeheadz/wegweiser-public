# Filepath: app/routes/osquery/device_api.py
"""
Osquery Device API Routes
Handles osquery command execution and device-specific operations via NATS
"""

from flask import jsonify, request, session
from flask_principal import Permission, RoleNeed
import logging

from app import csrf
from app.utilities.app_logging_helper import log_with_route
from app.utilities.app_get_current_user import get_current_user
from app.utilities.app_access_login_required import login_required
from app.models import Devices, Tenants
from . import osquery_bp
from .nats_utils import send_nats_command, execute_async_command

# Permissions
admin_permission = Permission(RoleNeed('admin'))

def get_device_tenant_uuid(device_uuid: str) -> str:
    """Get the tenant UUID for a device"""
    device = Devices.query.filter_by(deviceuuid=device_uuid).first()
    if not device:
        raise ValueError(f"Device not found: {device_uuid}")
    return str(device.tenantuuid)

@osquery_bp.route('/api/device/<uuid:device_uuid>/tenant', methods=['GET'])
def get_device_tenant_info(device_uuid):
    """Get tenant information for a device (for agent initialization)"""
    try:
        device_uuid_str = str(device_uuid)
        
        # Get device with tenant info
        device = Devices.query.filter_by(deviceuuid=device_uuid_str).first()
        if not device:
            log_with_route(logging.ERROR, f"Device not found: {device_uuid_str}")
            return jsonify({'error': 'Device not found'}), 404

        # Get tenant info
        tenant = Tenants.query.filter_by(tenantuuid=device.tenantuuid).first()
        if not tenant:
            log_with_route(logging.ERROR, f"Tenant not found for device: {device_uuid_str}")
            return jsonify({'error': 'Tenant not found'}), 404

        return jsonify({
            'success': True,
            'device_uuid': device_uuid_str,
            'tenant_uuid': str(device.tenantuuid),
            'tenant_name': tenant.tenantname,
            'nats_server': 'tls://nats.wegweiser.tech:443',
            'group_uuid': str(device.groupuuid),
            'org_uuid': str(device.orguuid)
        })

    except Exception as e:
        log_with_route(logging.ERROR, f"Error getting tenant info for device {device_uuid}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@osquery_bp.route('/api/device/<uuid:device_uuid>/status', methods=['GET'])
@login_required
def get_device_status(device_uuid):
    """Get device online status"""
    try:
        device_uuid_str = str(device_uuid)

        # Get device directly from database
        device = Devices.query.filter_by(deviceuuid=device_uuid_str).first()
        if not device:
            return jsonify({'error': 'Device not found'}), 404
        
        status = device.get_online_status()
        
        return jsonify({
            'success': True,
            'device_uuid': device_uuid_str,
            'status': status,
            'is_online': device.is_online,
            'last_heartbeat': device.last_heartbeat,
            'last_seen_online': device.last_seen_online
        })
        
    except Exception as e:
        log_with_route(logging.ERROR, f"Error getting device status: {str(e)}")
        return jsonify({'error': str(e)}), 500

@osquery_bp.route('/api/device/<uuid:device_uuid>/command', methods=['POST'])
@csrf.exempt
@login_required
def send_device_command(device_uuid):
    """Send command to device via NATS"""
    try:
        device_uuid_str = str(device_uuid)
        user = get_current_user()
        user_email = user.companyemail if user else 'unknown'

        # Get device and its tenant UUID directly from database
        device = Devices.query.filter_by(deviceuuid=device_uuid_str).first()
        if not device:
            return jsonify({'error': 'Device not found'}), 404

        # Use the device's actual tenant UUID
        tenantuuid = str(device.tenantuuid)
        
        data = request.get_json()
        action = data.get('action')
        args = data.get('args', {})
        
        if not action:
            return jsonify({'error': 'action is required'}), 400
        
        # Send command via NATS using shared function
        command_coro = send_nats_command(
            tenantuuid=tenantuuid,
            device_uuid=device_uuid_str,
            action=action,
            args=args,
            user_email=user_email
        )

        result = execute_async_command(command_coro)
        
        log_with_route(logging.INFO, f"Device command {action} to {device_uuid_str} by {user_email}")
        return jsonify(result)
        
    except Exception as e:
        log_with_route(logging.ERROR, f"Device command error: {str(e)}")
        return jsonify({'error': str(e)}), 500
