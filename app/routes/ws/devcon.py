# Filepath: app/routes/ws/devcon.py

import json
import logging
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from flask import Blueprint, request, jsonify, current_app, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from werkzeug.exceptions import BadRequest

from app.models import db, Devices, DeviceStatus, DeviceConnectivity
from app.utilities.app_logging_helper import log_with_route
from app import safe_db_session
from app import csrf

# Initialize Blueprint
connectivity_bp = Blueprint('connectivity_bp', __name__)

# Configuration - Add your Node-RED server IP address here
ALLOWED_IPS = [
    '127.0.0.1',           # localhost
    '::1',                 # IPv6 localhost
    '20.0.138.218',       # Your Node-RED server IP (replace with actual)
    # Add your Node-RED server's actual IP address here
]

def check_ip_allowed():
    """Check if the request comes from an allowed IP address"""
    client_ip = request.remote_addr
    
    # Handle proxy headers if you're behind a reverse proxy
    if request.headers.get('X-Forwarded-For'):
        client_ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        client_ip = request.headers.get('X-Real-IP')
    
    if client_ip not in ALLOWED_IPS:
        log_with_route(logging.WARNING, f"Unauthorized access attempt from IP: {client_ip}")
        abort(403, description="Access denied: IP not authorized")
    
    log_with_route(logging.DEBUG, f"Authorized request from IP: {client_ip}")

@connectivity_bp.route('/ws/device/<uuid:device_uuid>/connectivity', methods=['POST'])
@csrf.exempt 
def update_device_connectivity(device_uuid):
    """
    Update device connectivity status
    
    Expected JSON payload:
    {
        "is_online": true,
        "connection_type": "node-red",
        "agent_version": "1.0.0",
        "connection_info": {
            "node_red_server": "vidar.wegweiser.tech",
            "connection_time": "2025-06-05T12:34:56Z"
        }
    }
    """
    # Check IP authorization first
    check_ip_allowed()
    
    try:
        device_uuid_str = str(device_uuid)
        
        # Get JSON data from request
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        # Verify device exists
        with safe_db_session() as session:
            device = session.query(Devices).filter_by(deviceuuid=device_uuid_str).first()
            if not device:
                log_with_route(logging.ERROR, f"Device not found: {device_uuid_str}")
                return jsonify({"error": "Device not found"}), 404
        
        # Update connectivity
        result = update_device_connectivity_status(
            device_uuid_str=device_uuid_str,
            is_online=data.get('is_online', False),
            connection_type=data.get('connection_type', 'node-red'),
            agent_version=data.get('agent_version'),
            connection_info=data.get('connection_info')
        )
        
        if result:
            log_with_route(logging.INFO, f"Updated connectivity for device {device_uuid_str}")
            return jsonify({
                "success": True,
                "message": "Device connectivity updated",
                "device_uuid": device_uuid_str,
                "timestamp": int(time.time())
            }), 200
        else:
            return jsonify({"error": "Failed to update connectivity"}), 500
            
    except Exception as e:
        log_with_route(logging.ERROR, f"Error updating connectivity for {device_uuid}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@connectivity_bp.route('/ws/device/<uuid:device_uuid>/heartbeat', methods=['POST'])
def update_device_heartbeat(device_uuid):
    """
    Update device heartbeat timestamp
    
    Expected JSON payload example:
    {
        "timestamp": "2025-06-05T12:34:56Z",
        "system_info": {
            "hostname": "DESKTOP-ABC123",
            "platform": "Windows",
            "platform_version": "10.0.19044",
            "architecture": "AMD64",
            "python_version": "3.9.7",
            "processor": "Intel64 Family 6 Model 142 Stepping 10, GenuineIntel",
            "ip_addresses": ["192.168.1.100", "203.0.113.45"],
            "memory_total": 17179869184,
            "memory_available": 8589934592,
            "cpu_count": 8,
            "boot_time": 1717567890,
            "network_interfaces": ["Ethernet", "Wi-Fi", "Loopback"],
            "users": ["john.doe", "admin"]
        }
    }
    
    Note: system_info is optional and can contain any subset of the above fields
    """
    # Check IP authorization first
    check_ip_allowed()
    
    try:
        device_uuid_str = str(device_uuid)
        
        # Get JSON data from request
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        # Verify device exists
        with safe_db_session() as session:
            device = session.query(Devices).filter_by(deviceuuid=device_uuid_str).first()
            if not device:
                return jsonify({"error": "Device not found"}), 404
        
        # Update heartbeat
        result = update_device_heartbeat_status(
            device_uuid_str=device_uuid_str,
            heartbeat_timestamp=data.get('timestamp'),
            system_info=data.get('system_info')
        )
        
        if result:
            return jsonify({
                "success": True,
                "message": "Heartbeat updated",
                "device_uuid": device_uuid_str,
                "timestamp": int(time.time())
            }), 200
        else:
            return jsonify({"error": "Failed to update heartbeat"}), 500
            
    except Exception as e:
        log_with_route(logging.ERROR, f"Error updating heartbeat for {device_uuid}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@connectivity_bp.route('/ws/device/<uuid:device_uuid>/status', methods=['POST'])
def update_device_status(device_uuid):
    """
    Update device status information
    
    Expected JSON payload example:
    {
        "cpu_usage": 45.2,
        "memory_usage": 67.8,
        "disk_usage": 23.1,
        "hostname": "DESKTOP-ABC123",
        "platform": "Windows",
        "username": "john.doe",
        "cpu_count": 8,
        "boot_time": 1717567890,
        "system_info": {
            "additional_data": "any extra system information"
        }
    }
    """
    # Check IP authorization first
    check_ip_allowed()
    
    try:
        device_uuid_str = str(device_uuid)
        
        # Get JSON data from request
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        # Verify device exists
        with safe_db_session() as session:
            device = session.query(Devices).filter_by(deviceuuid=device_uuid_str).first()
            if not device:
                return jsonify({"error": "Device not found"}), 404
        
        # Update status
        result = update_device_status_info(
            device_uuid_str=device_uuid_str,
            status_data=data
        )
        
        if result:
            return jsonify({
                "success": True,
                "message": "Device status updated",
                "device_uuid": device_uuid_str,
                "timestamp": int(time.time())
            }), 200
        else:
            return jsonify({"error": "Failed to update status"}), 500
            
    except Exception as e:
        log_with_route(logging.ERROR, f"Error updating status for {device_uuid}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@connectivity_bp.route('/ws/device/<uuid:device_uuid>/connectivity', methods=['GET'])
def get_device_connectivity(device_uuid):
    """Get current connectivity status for a device"""
    # Check IP authorization first
    check_ip_allowed()
    
    try:
        device_uuid_str = str(device_uuid)
        
        with safe_db_session() as session:
            # Convert string UUID to UUID type
            db_uuid = uuid.UUID(device_uuid_str)
            
            # Get connectivity record
            connectivity = session.query(DeviceConnectivity).filter_by(deviceuuid=db_uuid).first()
            
            if connectivity:
                return jsonify({
                    "success": True,
                    "connectivity": connectivity.to_dict()
                }), 200
            else:
                return jsonify({
                    "success": False,
                    "message": "No connectivity record found"
                }), 404
                
    except Exception as e:
        log_with_route(logging.ERROR, f"Error getting connectivity for {device_uuid}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@connectivity_bp.route('/ws/debug/ip', methods=['GET'])
def debug_ip():
    """Debug endpoint to see what IP the request is coming from"""
    return jsonify({
        "remote_addr": request.remote_addr,
        "x_forwarded_for": request.headers.get('X-Forwarded-For'),
        "x_real_ip": request.headers.get('X-Real-IP'),
        "all_headers": dict(request.headers)
    })

# Helper Functions

def update_device_connectivity_status(device_uuid_str: str, is_online: bool, 
                                    connection_type: str = "node-red", 
                                    agent_version: Optional[str] = None,
                                    connection_info: Optional[Dict] = None) -> bool:
    """Update device connectivity status in database"""
    try:
        current_time = int(time.time())
        
        with safe_db_session() as session:
            # Convert string UUID to UUID type
            db_uuid = uuid.UUID(device_uuid_str)
            
            # Check if connectivity record exists
            connectivity = session.query(DeviceConnectivity).filter_by(deviceuuid=db_uuid).first()
            
            if connectivity:
                # Update existing record
                old_status = connectivity.is_online
                connectivity.is_online = is_online
                connectivity.connection_type = connection_type
                
                if agent_version:
                    connectivity.agent_version = agent_version
                
                if connection_info:
                    connectivity.connection_info = connection_info
                
                # Update timestamps
                if old_status != is_online:
                    connectivity.last_online_change = current_time
                
                if is_online:
                    connectivity.last_seen_online = current_time
                    connectivity.last_heartbeat = current_time
                    
            else:
                # Create new record
                new_connectivity = DeviceConnectivity(
                    deviceuuid=db_uuid,
                    is_online=is_online,
                    last_online_change=current_time,
                    last_seen_online=current_time if is_online else None,
                    last_heartbeat=current_time if is_online else None,
                    agent_version=agent_version,
                    connection_type=connection_type,
                    connection_info=connection_info
                )
                session.add(new_connectivity)
            
            session.commit()
            log_with_route(logging.INFO, f"Updated connectivity for {device_uuid_str}: {'online' if is_online else 'offline'}")
            return True
            
    except Exception as e:
        log_with_route(logging.ERROR, f"Error updating connectivity status: {str(e)}")
        return False

def update_device_heartbeat_status(device_uuid_str: str, 
                                 heartbeat_timestamp: Optional[str] = None,
                                 system_info: Optional[Dict] = None) -> bool:
    """Update device heartbeat timestamp"""
    try:
        current_time = int(time.time())
        
        with safe_db_session() as session:
            # Convert string UUID to UUID type
            db_uuid = uuid.UUID(device_uuid_str)
            
            # Update connectivity record
            connectivity = session.query(DeviceConnectivity).filter_by(deviceuuid=db_uuid).first()
            
            if connectivity:
                connectivity.last_heartbeat = current_time
                connectivity.is_online = True
                connectivity.last_seen_online = current_time
                
                # Update connection info with system info if provided
                if system_info:
                    if not connectivity.connection_info:
                        connectivity.connection_info = {}
                    connectivity.connection_info.update({
                        "last_system_info": system_info,
                        "last_heartbeat_time": datetime.utcnow().isoformat()
                    })
            else:
                # Create new record if it doesn't exist
                connection_info_data = None
                if system_info:
                    connection_info_data = {
                        "last_system_info": system_info,
                        "last_heartbeat_time": datetime.utcnow().isoformat()
                    }
                
                new_connectivity = DeviceConnectivity(
                    deviceuuid=db_uuid,
                    is_online=True,
                    last_online_change=current_time,
                    last_seen_online=current_time,
                    last_heartbeat=current_time,
                    connection_type="node-red",
                    connection_info=connection_info_data
                )
                session.add(new_connectivity)
            
            session.commit()
            log_with_route(logging.DEBUG, f"Updated heartbeat for {device_uuid_str}")
            return True
            
    except Exception as e:
        log_with_route(logging.ERROR, f"Error updating heartbeat status: {str(e)}")
        return False

def update_device_status_info(device_uuid_str: str, status_data: Dict[str, Any]) -> bool:
    """Update device status information"""
    try:
        current_time = int(time.time())
        
        with safe_db_session() as session:
            # Update DeviceStatus table
            device_status = session.query(DeviceStatus).filter_by(deviceuuid=device_uuid_str).first()
            
            if device_status:
                # Update fields based on provided data
                for key, value in status_data.items():
                    if hasattr(device_status, key):
                        setattr(device_status, key, value)
                
                device_status.last_update = current_time
            else:
                # Create new status record
                new_status = DeviceStatus(
                    deviceuuid=device_uuid_str,
                    last_update=current_time,
                    last_json=current_time,
                    agent_platform=status_data.get('platform', 'Unknown'),
                    system_name=status_data.get('hostname', 'Unknown'),
                    logged_on_user=status_data.get('username', 'Unknown'),
                    cpu_usage=status_data.get('cpu_usage', 0),
                    cpu_count=status_data.get('cpu_count', 0),
                    boot_time=status_data.get('boot_time', 0)
                )
                session.add(new_status)
            
            session.commit()
            log_with_route(logging.INFO, f"Updated status for {device_uuid_str}")
            return True
            
    except Exception as e:
        log_with_route(logging.ERROR, f"Error updating device status: {str(e)}")
        return False

# Add this to your devcon.py file

@connectivity_bp.route('/ws/devices/online-devices', methods=['GET'])
@csrf.exempt 
def get_online_devices():
    """Get all devices currently marked as online"""
    check_ip_allowed()
    
    try:
        current_time = int(time.time())
        stale_threshold = 120  # 2 minutes in seconds
        
        with safe_db_session() as session:
            # Get all devices marked as online
            online_devices = session.query(DeviceConnectivity).filter_by(is_online=True).all()
            
            active_devices = []
            stale_devices = []
            
            for device in online_devices:
                last_heartbeat = device.last_heartbeat or 0
                time_since_heartbeat = current_time - last_heartbeat
                
                device_info = {
                    "device_uuid": str(device.deviceuuid),
                    "last_heartbeat": last_heartbeat,
                    "time_since_heartbeat": time_since_heartbeat,
                    "last_seen_online": device.last_seen_online
                }
                
                if time_since_heartbeat > stale_threshold:
                    stale_devices.append(device_info)
                else:
                    active_devices.append(device_info)
            
            return jsonify({
                "success": True,
                "active_devices": active_devices,
                "stale_devices": stale_devices,
                "total_online": len(online_devices),
                "stale_count": len(stale_devices),
                "threshold_seconds": stale_threshold,
                "current_time": current_time
            }), 200
            
    except Exception as e:
        log_with_route(logging.ERROR, f"Error getting online devices: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Add this to your devcon.py file

@connectivity_bp.route('/ws/devices/bulk-offline', methods=['POST'])
@csrf.exempt 
def bulk_offline_update():
    """Mark multiple devices as offline"""
    check_ip_allowed()
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
            
        offline_devices = data.get('offline_devices', [])
        if not offline_devices:
            return jsonify({"error": "No offline_devices provided"}), 400
        
        current_time = int(time.time())
        updated_count = 0
        
        with safe_db_session() as session:
            for device_info in offline_devices:
                device_uuid_str = device_info.get('device_uuid')
                if not device_uuid_str:
                    continue
                    
                try:
                    db_uuid = uuid.UUID(device_uuid_str)
                    
                    # Update connectivity record
                    connectivity = session.query(DeviceConnectivity).filter_by(deviceuuid=db_uuid).first()
                    
                    if connectivity and connectivity.is_online:
                        connectivity.is_online = False
                        connectivity.last_online_change = current_time
                        updated_count += 1
                        log_with_route(logging.INFO, f"Marked device {device_uuid_str} as offline")
                        
                except ValueError:
                    log_with_route(logging.WARNING, f"Invalid UUID format: {device_uuid_str}")
                    continue
                    
            session.commit()
            
        return jsonify({
            "success": True,
            "updated_devices": updated_count,
            "processed_devices": len(offline_devices),
            "timestamp": current_time
        }), 200
        
    except Exception as e:
        log_with_route(logging.ERROR, f"Error in bulk offline update: {str(e)}")
        return jsonify({"error": str(e)}), 500