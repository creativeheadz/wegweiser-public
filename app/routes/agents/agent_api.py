# Filepath: app/routes/agents/agent_api.py

from flask import Blueprint, request, jsonify, current_app
from app.utilities.app_logging_helper import log_with_route
from app.utilities.app_access_login_required import login_required
from app.models import db, Devices, DeviceStatus, DeviceConnectivity
import logging
import json
import uuid
import time

# WebSocket functionality temporarily disabled
# from app.routes.ws.agent_endpoint import send_command_to_agent, get_connected_devices, is_device_connected, connection_registry

agents_api_bp = Blueprint('agents_api_bp', __name__)

@agents_api_bp.route('/api/agents/connected', methods=['GET'])
@login_required
def get_connected_agents():
    """Get a list of all connected agents"""
    try:
        agents = []
        connected_devices = get_connected_devices()
        
        for device_uuid in connected_devices:
            connection = connection_registry.get_connection(device_uuid)
            if connection:
                agents.append({
                    'device_uuid': device_uuid,
                    'connected_at': connection['connected_at'].isoformat(),
                    'last_heartbeat': connection['last_heartbeat'].isoformat(),
                    'ip_address': connection.get('ip_address', 'Unknown'),
                    'connection_id': connection.get('connection_id', 'Unknown')
                })

        return jsonify({
            'success': True,
            'count': len(agents),
            'agents': agents
        })

    except Exception as e:
        log_with_route(logging.ERROR, f"Error getting connected agents: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agents_api_bp.route('/api/agents/<uuid:device_uuid>/command', methods=['POST'])
@login_required
def send_command(device_uuid):
    """Send a command to a connected agent"""
    try:
        device_uuid_str = str(device_uuid)

        # WebSocket functionality temporarily disabled
        # Check if agent is connected via database instead
        device = Devices.query.filter_by(deviceuuid=device_uuid).first()
        if not device:
            return jsonify({
                'success': False,
                'error': 'Device not found'
            }), 404

        # Get command from request
        data = request.get_json()
        if not data or 'command' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing command parameter'
            }), 400

        # Generate command ID
        command_id = str(uuid.uuid4())

        # Create command payload
        command = {
            'type': 'command',
            'command_id': command_id,
            'command': data['command'],
            'parameters': data.get('parameters', {}),
            'timestamp': time.time()
        }

        # WebSocket functionality temporarily disabled
        # Return error indicating WebSocket is not available
        return jsonify({
            'success': False,
            'error': 'WebSocket functionality is currently disabled'
        }), 503

    except Exception as e:
        log_with_route(logging.ERROR, f"Error sending command: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agents_api_bp.route('/api/agents/<uuid:device_uuid>/connectivity', methods=['GET'])
@login_required
def get_device_connectivity(device_uuid):
    """Get device connectivity status"""
    try:
        device_uuid_str = str(device_uuid)

        # Check if DeviceConnectivity table exists and has this device
        connectivity = DeviceConnectivity.query.filter_by(deviceuuid=device_uuid).first()

        if not connectivity:
            # Fall back to DeviceStatus
            device_status = DeviceStatus.query.filter_by(deviceuuid=device_uuid).first()

            if device_status:
                connectivity_data = {
                    'is_online': getattr(device_status, 'is_online', False),
                    'online_status': getattr(device_status, 'get_online_status', lambda: 'Unknown')(),
                    'last_seen_online': device_status.last_update,  # Use last_update from DeviceStatus
                    'last_heartbeat': getattr(device_status, 'last_heartbeat', None)
                }
            else:
                # No connectivity data available
                connectivity_data = {
                    'is_online': False,
                    'online_status': 'Unknown',
                    'last_seen_online': None,
                    'last_heartbeat': None
                }
        else:
            # Use DeviceConnectivity data
            connectivity_data = connectivity.to_dict()

        return jsonify({
            'success': True,
            'connectivity': connectivity_data
        })

    except Exception as e:
        log_with_route(logging.ERROR, f"Error getting device connectivity: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agents_api_bp.route('/api/agents/<uuid:device_uuid>/status', methods=['GET'])
@login_required
def get_device_status(device_uuid):
    """Get simple device online/offline status"""
    try:
        device_uuid_str = str(device_uuid)

        # WebSocket functionality temporarily disabled
        # Check database for connectivity status instead

        # Otherwise check DB
        connectivity = DeviceConnectivity.query.filter_by(deviceuuid=device_uuid).first()

        if not connectivity:
            # Fall back to DeviceStatus
            device_status = DeviceStatus.query.filter_by(deviceuuid=device_uuid).first()

            if device_status:
                is_online = getattr(device_status, 'is_online', False)
                status = getattr(device_status, 'get_online_status', lambda: ('Online' if is_online else 'Offline'))()
            else:
                is_online = False
                status = 'Unknown'
        else:
            # Use DeviceConnectivity data
            is_online = connectivity.is_online
            status = 'Online' if is_online else 'Offline'

        return jsonify({
            'success': True,
            'is_online': is_online,
            'status': status
        })

    except Exception as e:
        log_with_route(logging.ERROR, f"Error getting device status: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'is_online': False,
            'status': 'Error'
        }), 500