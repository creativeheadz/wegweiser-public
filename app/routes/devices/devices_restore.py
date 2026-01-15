# Filepath: app/routes/devices/devices_restore.py
"""
Device Restoration Routes

Handles restoration of deleted devices from backup JSON files.
"""

import logging
from flask import jsonify, request
from app.routes.devices import devices_bp
from app.utilities.device_restore import restore_device_from_backup, find_device_backup, list_available_backups
from app.utilities.app_logging_helper import log_with_route
from app.utilities.app_access_login_required import login_required
from app import master_permission


@devices_bp.route('/restore/<device_uuid>', methods=['POST'])
@login_required
@master_permission.require(http_exception=403)
def restore_device(device_uuid):
    """
    Restore a deleted device from its backup JSON file.
    
    This endpoint allows manual restoration of a device that was previously deleted.
    The device will be recreated with all its historical data from the backup.
    """
    try:
        log_with_route(logging.INFO, f"Request to restore device {device_uuid}")
        
        # Optional: allow specifying a specific backup file path
        data = request.get_json() or {}
        backup_path = data.get('backup_path')
        
        # Attempt restoration
        success, message = restore_device_from_backup(device_uuid, backup_path)
        
        if success:
            log_with_route(logging.INFO, f"Successfully restored device {device_uuid}")
            return jsonify({
                'success': True,
                'message': message,
                'deviceuuid': device_uuid
            }), 200
        else:
            log_with_route(logging.ERROR, f"Failed to restore device {device_uuid}: {message}")
            return jsonify({
                'success': False,
                'error': message
            }), 400
            
    except Exception as e:
        error_msg = f"Error restoring device {device_uuid}: {str(e)}"
        log_with_route(logging.ERROR, error_msg)
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500


@devices_bp.route('/restore/<device_uuid>/check', methods=['GET'])
@login_required
def check_device_backup(device_uuid):
    """
    Check if a backup exists for a device UUID.
    
    Returns information about the most recent backup file if found.
    """
    try:
        backup_path = find_device_backup(device_uuid)
        
        if backup_path:
            import os
            import json
            
            # Get backup file info
            file_size = os.path.getsize(backup_path)
            file_mtime = os.path.getmtime(backup_path)
            
            # Try to read device name from backup
            device_name = None
            try:
                with open(backup_path, 'r') as f:
                    backup_data = json.load(f)
                    device_name = backup_data.get('device_info', {}).get('devicename')
            except:
                pass
            
            return jsonify({
                'backup_exists': True,
                'backup_path': backup_path,
                'file_size': file_size,
                'modified_time': file_mtime,
                'device_name': device_name
            }), 200
        else:
            return jsonify({
                'backup_exists': False,
                'message': f'No backup found for device {device_uuid}'
            }), 404
            
    except Exception as e:
        error_msg = f"Error checking backup for device {device_uuid}: {str(e)}"
        log_with_route(logging.ERROR, error_msg)
        return jsonify({
            'error': error_msg
        }), 500


@devices_bp.route('/backups/list', methods=['GET'])
@login_required
@master_permission.require(http_exception=403)
def list_device_backups():
    """
    List all available device backups.
    
    Optional query parameter:
    - device_uuid: Filter backups for a specific device
    """
    try:
        device_uuid = request.args.get('device_uuid')
        backups = list_available_backups(device_uuid)
        
        return jsonify({
            'success': True,
            'count': len(backups),
            'backups': backups
        }), 200
        
    except Exception as e:
        error_msg = f"Error listing backups: {str(e)}"
        log_with_route(logging.ERROR, error_msg)
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500

