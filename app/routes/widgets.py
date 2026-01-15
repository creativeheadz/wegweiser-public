# Filepath: app/routes/widgets.py
import os
from flask import Blueprint, render_template, request, jsonify, session, g
from flask_principal import Permission, RoleNeed
from sqlalchemy import func
from datetime import datetime, timedelta
from app.models import db, Devices, Tenants, Organisations, Groups, DeviceStatus, DeviceRealtimeData,  DeviceRealtimeHistory, DeviceMetadata
from app.utilities.ui_widgets_get_coordinates_from_ip import get_coordinates_from_ip
from app.utilities.app_access_login_required import login_required
import logging
from app.utilities.app_logging_helper import log_with_route
from dotenv import load_dotenv
from app import csrf
from sqlalchemy.exc import IntegrityError 
import time
import json


load_dotenv()

widgets_bp = Blueprint('widgets', __name__)

# Define permissions
admin_permission = Permission(RoleNeed('admin'))
master_permission = Permission(RoleNeed('master'))
master_or_admin_permission = Permission(RoleNeed('master'), RoleNeed('admin'))

@widgets_bp.route('/widgets/devices/onboarded')
def devices_onboarded():
    now = datetime.utcnow()
    forty_five_days_ago = now - timedelta(days=45)

    # Role-based filtering
    if admin_permission.can():
        query = db.session.query(
            func.date(func.to_timestamp(Devices.created_at)).label('date'),
            func.count(Devices.deviceuuid).label('count')
        ).filter(
            Devices.created_at >= int(forty_five_days_ago.timestamp())
        )
    elif master_permission.can():
        query = db.session.query(
            func.date(func.to_timestamp(Devices.created_at)).label('date'),
            func.count(Devices.deviceuuid).label('count')
        ).filter(
            Devices.created_at >= int(forty_five_days_ago.timestamp()),
            Devices.tenantuuid == g.user.tenantuuid
        )
    else:
        log_with_route(logging.WARNING, "Unauthorized access attempt to devices_onboarded route.")
        return jsonify({"error": "Unauthorized"}), 403

    data = query.group_by(
        func.date(func.to_timestamp(Devices.created_at))
    ).all()

    chart_data = {
        "labels": [(now - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(44, -1, -1)],
        "data": [0] * 45
    }
    date_index_map = {chart_data["labels"][i]: i for i in range(45)}

    for row in data:
        date_str = row.date.strftime('%Y-%m-%d')
        if date_str in date_index_map:
            chart_data["data"][date_index_map[date_str]] = row.count

    log_with_route(logging.INFO, "Device onboarded data successfully prepared for chart.")

    return jsonify(chart_data)


@widgets_bp.route('/widgets/devices/onboarded/data')
@master_or_admin_permission.require(http_exception=403)
def devices_onboarded_data():
    user_role = session.get('role')
    tenant_uuid = session.get('tenant_uuid')
    user_id = session.get('user_id')

    log_with_route(logging.INFO, f"Fetching devices onboarded data for user_role: {user_role}, tenant_uuid: {tenant_uuid}, user_id: {user_id}")

    if user_role == 'admin':
        devices_query = Devices.query
    elif user_role == 'master':
        devices_query = Devices.query.filter_by(tenantuuid=tenant_uuid)
    else:
        devices_query = Devices.query.filter_by(user_uuid=user_id)

    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=44)  # Include 44 days before today

    dates = [start_date + timedelta(days=i) for i in range(45)]
    labels = [date.strftime('%Y-%m-%d') for date in dates]
    data = []

    for date in dates:
        next_day = date + timedelta(days=1)
        count = devices_query.filter(
            Devices.created_at >= date.timestamp(),
            Devices.created_at < next_day.timestamp()
        ).count()
        data.append(count)
        log_with_route(logging.DEBUG, f"Devices onboarded on {date.strftime('%Y-%m-%d')}: {count}")

    # Adjust labels to show every 5 days
    adjusted_labels = [labels[i] if i % 5 == 0 else '' for i in range(45)]

    log_with_route(logging.INFO, "Device onboarded data prepared and ready to be sent.")

    return jsonify({'labels': adjusted_labels, 'data': data})


@widgets_bp.route('/widgets/map', methods=['GET'])
@login_required
@master_or_admin_permission.require(http_exception=403)
def map():
    return render_template('administration/admin_map.html')

@widgets_bp.route('/widgets/map_data', methods=['GET'])
@login_required
@master_or_admin_permission.require(http_exception=403)
def map_data():
    try:
        devices = db.session.query(DeviceStatus).filter(DeviceStatus.publicIp != None, DeviceStatus.country != None).all()
        
        # Use a dictionary to group devices by their public IP address
        ip_to_device_map = {}
        for device in devices:
            if device.publicIp not in ip_to_device_map:
                lat, lon = get_coordinates_from_ip(device.publicIp)
                if lat and lon:
                    ip_to_device_map[device.publicIp] = {
                        'latitude': lat,
                        'longitude': lon,
                        'devices': []
                    }
            
            # Append device information to the list associated with the IP
            ip_to_device_map[device.publicIp]['devices'].append({
                'deviceuuid': str(device.deviceuuid),
                'devicename': device.system_name,
                'country': device.country
            })

        # Convert the dictionary to a list for JSON serialization
        device_list = []
        for ip, data in ip_to_device_map.items():
            device_list.append({
                'publicIp': ip,
                'latitude': data['latitude'],
                'longitude': data['longitude'],
                'device_count': len(data['devices']),  # Count of devices
                'devices': data['devices']
            })

        log_with_route(logging.INFO, f"Map data fetched successfully with {len(device_list)} unique IPs.")
        return jsonify(device_list)
    except Exception as e:
        log_with_route(logging.ERROR, f"Error fetching map data: {e}")
        return jsonify({"error": "Internal Server Error"}), 500


@widgets_bp.route('/widgets/map/embed')
@login_required
def map_embed():
    """Renders the map widget as a standalone page"""
    try:
        return render_template('widgets/maps/uk.html')
    except Exception as e:
        log_with_route(logging.ERROR, f"Error rendering map embed: {str(e)}")
        return jsonify({"error": "Failed to render map widget"}), 500


@widgets_bp.route('/widgets/<uuid:device_uuid>/realtime-data', methods=['POST'])
@csrf.exempt
def add_realtime_data(device_uuid):
    try:
        data = request.get_json()
        current_time = int(time.time())
        data_value_json = json.dumps(data['data_value'])

        # Add to history
        new_history = DeviceRealtimeHistory(
            deviceuuid=device_uuid,
            data_type=data['data_type'],
            data_value=data_value_json,
            timestamp=current_time
        )
        db.session.add(new_history)

        # Delete existing realtime entries
        DeviceRealtimeData.query.filter_by(
            deviceuuid=device_uuid,
            data_type=data['data_type']
        ).delete()

        # Create new realtime entry
        new_realtime = DeviceRealtimeData(
            deviceuuid=device_uuid,
            data_type=data['data_type'],
            data_value=data_value_json,
            last_updated=current_time
        )
        db.session.add(new_realtime)

        db.session.commit()
        log_with_route(logging.INFO, f"Real-time data for device {device_uuid} added successfully.")
        return jsonify({"message": "Real-time data added successfully"}), 201

    except Exception as e:
        db.session.rollback()
        log_with_route(logging.ERROR, f"Unexpected error while adding real-time data: {e}")
        return jsonify({"error": "Internal server error"}), 500


@widgets_bp.route('/widgets/<uuid:device_uuid>/realtime-data', methods=['GET'])
@login_required
def get_realtime_data(device_uuid):
    """
    Get the latest real-time data for a device.
    """
    try:
        data = DeviceRealtimeData.query.filter_by(deviceuuid=device_uuid).all()
        
        if not data:
            log_with_route(logging.WARNING, f"No real-time data found for device {device_uuid}.")
            return jsonify({"error": "No real-time data found"}), 404

        response = [entry.to_dict() for entry in data]
        log_with_route(logging.INFO, f"Fetched real-time data for device {device_uuid}.")
        return jsonify(response), 200

    except Exception as e:
        log_with_route(logging.ERROR, f"Error fetching real-time data for device {device_uuid}: {e}")
        return jsonify({"error": "Internal server error"}), 500


@widgets_bp.route('/widgets/<uuid:device_uuid>/realtime-data/history', methods=['GET'])
@login_required
def get_realtime_data_history(device_uuid):
    """
    Get the history of real-time data updates for a device.
    """
    try:
        history = DeviceRealtimeDataHistory.query.filter_by(deviceuuid=device_uuid).all()
        
        if not history:
            log_with_route(logging.WARNING, f"No real-time data history found for device {device_uuid}.")
            return jsonify({"error": "No real-time data history found"}), 404

        response = [entry.to_dict() for entry in history]
        log_with_route(logging.INFO, f"Fetched real-time data history for device {device_uuid}.")
        return jsonify(response), 200

    except Exception as e:
        log_with_route(logging.ERROR, f"Error fetching real-time data history for device {device_uuid}: {e}")
        return jsonify({"error": "Internal server error"}), 500

@widgets_bp.route('/widgets/cpu-load', methods=['GET'])
@login_required
def render_cpu_load_widget():
    """
    Render the CPU load widget.
    """
    try:
        return render_template('widgets/widget.html')
    except Exception as e:
        log_with_route(logging.ERROR, f"Error rendering CPU load widget: {str(e)}")
        return jsonify({"error": "Failed to render CPU load widget"}), 500


@widgets_bp.route('/widgets/cpu-load')
@login_required
def cpu_load_widget():
    """Render the CPU load widget template."""
    return render_template('widgets/cpu_load.html')

@widgets_bp.route('/widgets/latest-cpu-data')
@login_required
def get_latest_cpu_data():
    try:
        device_uuid = request.args.get('device_uuid')
        
        if not device_uuid:
            log_with_route(logging.WARNING, "Device UUID not provided.")
            return jsonify({"error": "Device UUID required"}), 400
        
        # Base query
        query = db.session.query(DeviceRealtimeData).filter(
            DeviceRealtimeData.data_type == 'osquery-info',
            DeviceRealtimeData.deviceuuid == device_uuid
        )
        
        # Get latest data
        latest_data = query.order_by(DeviceRealtimeData.last_updated.desc()).first()

        if not latest_data:
            log_with_route(logging.INFO, f"No CPU load data found for device {device_uuid}")
            return jsonify({"load_percentage": "0", "cpu_status": "0", "last_updated": "N/A"}), 404

        # Parse the JSON data from data_value
        data_value = json.loads(latest_data.data_value)
        
        response = {
            "load_percentage": data_value.get("load_percentage", "0"),
            "cpu_status": data_value.get("cpu_status", "0"),
            "last_updated": latest_data.last_updated  # Add last_updated to the response
        }
        
        log_with_route(logging.INFO, f"Successfully retrieved CPU load data for device {device_uuid}: {response}")
        return jsonify(response)

    except Exception as e:
        log_with_route(logging.ERROR, f"Error retrieving CPU load data: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    
    # Add to widgets.py

@widgets_bp.route('/widgets/device/<uuid:device_uuid>/cpu_history')
@login_required
def get_device_cpu_history(device_uuid):
    try:
        # Get the last 24 hours of CPU data
        cutoff_time = int(time.time()) - (24 * 60 * 60)
        
        history_data = db.session.query(
            DeviceRealtimeHistory.timestamp,
            DeviceRealtimeHistory.data_value
        ).filter(
            DeviceRealtimeHistory.deviceuuid == device_uuid,
            DeviceRealtimeHistory.data_type == 'osquery-info',
            DeviceRealtimeHistory.timestamp >= cutoff_time
        ).order_by(DeviceRealtimeHistory.timestamp.asc()).all()

        # Format data for ApexCharts
        formatted_data = []
        for timestamp, data_value in history_data:
            try:
                data_dict = json.loads(data_value)
                load_percentage = float(data_dict.get('load_percentage', 0))
                # Convert timestamp to milliseconds for ApexCharts
                formatted_data.append([timestamp * 1000, load_percentage])
            except (json.JSONDecodeError, ValueError, TypeError) as e:
                log_with_route(logging.ERROR, f"Error parsing data value: {str(e)}")
                continue

        log_with_route(logging.INFO, f"Successfully retrieved CPU history for device {device_uuid}")
        return jsonify(formatted_data)

    except Exception as e:
        log_with_route(logging.ERROR, f"Error retrieving CPU history: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500



@widgets_bp.route('/widgets/<uuid:device_uuid>/realtime-ram-data', methods=['POST'])
@csrf.exempt
def add_realtime_ram_data(device_uuid):
    try:
        data = request.get_json()
        current_time = int(time.time())

        # Add to history
        new_history = DeviceRealtimeHistory(
            deviceuuid=device_uuid,
            data_type=data['data_type'],
            data_value=json.dumps(data['data_value']),
            timestamp=current_time
        )
        db.session.add(new_history)

        # Update realtime data
        DeviceRealtimeData.query.filter_by(
            deviceuuid=device_uuid,
            data_type=data['data_type']
        ).delete()
        
        new_realtime = DeviceRealtimeData(
            deviceuuid=device_uuid,
            data_type=data['data_type'],
            data_value=json.dumps(data['data_value']),
            last_updated=current_time
        )
        db.session.add(new_realtime)

        db.session.commit()
        return jsonify({"message": "Success"}), 201

    except Exception as e:
        db.session.rollback()
        log_with_route(logging.ERROR, f"Error adding RAM data: {e}")
        return jsonify({"error": "Internal server error"}), 500

@widgets_bp.route('/widgets/latest-ram-data')
@login_required
def get_latest_ram_data():
    try:
        device_uuid = request.args.get('device_uuid')
        if not device_uuid:
            return jsonify({"error": "Device UUID required"}), 400
            
        latest_data = DeviceRealtimeData.query.filter_by(
            deviceuuid=device_uuid,
            data_type='osquery-info-ram'
        ).order_by(DeviceRealtimeData.last_updated.desc()).first()

        if not latest_data:
            return jsonify({
                "total_memory": "0",
                "used_memory": "0",
                "memory_percentage": "0",
                "last_updated": "N/A"  # Add last_updated to the response
            }), 404

        data_value = json.loads(latest_data.data_value)
        response = {
            "total_memory": data_value.get("total_memory", "0"),
            "used_memory": data_value.get("used_memory", "0"),
            "memory_percentage": data_value.get("memory_percentage", "0"),
            "last_updated": latest_data.last_updated  # Add last_updated to the response
        }

        return jsonify(response)

    except Exception as e:
        log_with_route(logging.ERROR, f"Error retrieving RAM data: {e}")
        return jsonify({"error": "Internal server error"}), 500

@widgets_bp.route('/widgets/device/<uuid:device_uuid>/ram_history')
@login_required
def get_device_ram_history(device_uuid):
    try:
        cutoff_time = int(time.time()) - (24 * 60 * 60)
        
        history_data = db.session.query(
            DeviceRealtimeHistory.timestamp,
            DeviceRealtimeHistory.data_value
        ).filter(
            DeviceRealtimeHistory.deviceuuid == device_uuid,
            DeviceRealtimeHistory.data_type == 'osquery-info-ram',
            DeviceRealtimeHistory.timestamp >= cutoff_time
        ).order_by(DeviceRealtimeHistory.timestamp.asc()).all()

        formatted_data = []
        for timestamp, data_value in history_data:
            try:
                data_dict = json.loads(data_value)
                memory_percentage = float(data_dict.get('memory_percentage', 0))
                formatted_data.append([timestamp * 1000, memory_percentage])
            except Exception as e:
                continue

        return jsonify(formatted_data)

    except Exception as e:
        log_with_route(logging.ERROR, f"Error retrieving RAM history: {e}")
        return jsonify({"error": "Internal server error"}), 500
    
    
    # Add to widgets.py

@widgets_bp.route('/widgets/<uuid:device_uuid>/realtime-socket-data', methods=['POST'])
@csrf.exempt
def add_realtime_socket_data(device_uuid):
    try:
        data = request.get_json()
        current_time = int(time.time())

        # Add to history
        new_history = DeviceRealtimeHistory(
            deviceuuid=device_uuid,
            data_type=data['data_type'],
            data_value=json.dumps(data['data_value']),
            timestamp=current_time
        )
        db.session.add(new_history)

        # Update realtime data
        DeviceRealtimeData.query.filter_by(
            deviceuuid=device_uuid,
            data_type=data['data_type']
        ).delete()
        
        new_realtime = DeviceRealtimeData(
            deviceuuid=device_uuid,
            data_type=data['data_type'],
            data_value=json.dumps(data['data_value']),
            last_updated=current_time
        )
        db.session.add(new_realtime)

        db.session.commit()
        return jsonify({"message": "Success"}), 201

    except Exception as e:
        db.session.rollback()
        log_with_route(logging.ERROR, f"Error adding socket data: {e}")
        return jsonify({"error": "Internal server error"}), 500

@widgets_bp.route('/widgets/latest-socket-data')
@login_required
def get_latest_socket_data():
    try:
        device_uuid = request.args.get('device_uuid')
        if not device_uuid:
            return jsonify({"error": "Device UUID required"}), 400
            
        latest_data = DeviceRealtimeData.query.filter_by(
            deviceuuid=device_uuid,
            data_type='osquery-info-sockets'
        ).order_by(DeviceRealtimeData.last_updated.desc()).first()

        if not latest_data:
            return jsonify({
                "connections": [],
                "stats": {
                    "total_connections": 0,
                    "listening_ports": 0,
                    "established_connections": 0,
                    "unusual_ports": 0,
                    "foreign_connections": 0
                }
            }), 404

        return jsonify(json.loads(latest_data.data_value))

    except Exception as e:
        log_with_route(logging.ERROR, f"Error retrieving socket data: {e}")
        return jsonify({"error": "Internal server error"}), 500

@widgets_bp.route('/widgets/device/<uuid:device_uuid>/socket_history')
@login_required
def get_device_socket_history(device_uuid):
    try:
        cutoff_time = int(time.time()) - (24 * 60 * 60)  # Last 24 hours
        
        history_data = db.session.query(
            DeviceRealtimeHistory.timestamp,
            DeviceRealtimeHistory.data_value
        ).filter(
            DeviceRealtimeHistory.deviceuuid == device_uuid,
            DeviceRealtimeHistory.data_type == 'osquery-info-sockets',
            DeviceRealtimeHistory.timestamp >= cutoff_time
        ).order_by(DeviceRealtimeHistory.timestamp.asc()).all()

        formatted_data = []
        for timestamp, data_value in history_data:
            try:
                data_dict = json.loads(data_value)
                stats = data_dict.get('stats', {})
                formatted_data.append({
                    'timestamp': timestamp * 1000,  # Convert to milliseconds for charts
                    'stats': stats,
                    'connections': data_dict.get('connections', [])
                })
            except Exception as e:
                continue

        return jsonify(formatted_data)

    except Exception as e:
        log_with_route(logging.ERROR, f"Error retrieving socket history: {e}")
        return jsonify({"error": "Internal server error"}), 500
    

@widgets_bp.route('/widgets/device/<uuid:device_uuid>/socket-analysis', methods=['GET'])
@login_required
def get_device_socket_analysis(device_uuid):
    """
    Fetch the latest socket analysis data for a specific device.
    """
    try:
        # Query the latest socket analysis from DeviceMetadata
        analysis = db.session.query(DeviceMetadata).filter_by(
            deviceuuid=device_uuid,
            metalogos_type='socket-connections-analysis'
        ).order_by(DeviceMetadata.created_at.desc()).first()

        if not analysis:
            return jsonify({"error": "No socket analysis data found"}), 404

        response_data = analysis.metalogos
        response_data['last_updated'] = analysis.created_at

        return jsonify(response_data), 200

    except Exception as e:
        log_with_route(logging.ERROR, f"Error fetching socket analysis for device {device_uuid}: {e}")
        return jsonify({"error": "Internal server error"}), 500