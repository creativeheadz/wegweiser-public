# Filepath: app/routes/devices/devices_poc_jsonb.py
"""
POC Route: Dynamic device page rendering from JSONB payload
Demonstrates performance and flexibility of storing full audit in single JSONB column
"""
import logging
import json
from flask import render_template, session, redirect, url_for, jsonify
from sqlalchemy import text
from uuid import UUID

# Import the blueprint
from . import devices_bp

# Models and database
from app.models import db, Devices, DeviceAuditJsonTest, Organisations, Groups

# Utilities
from app.utilities.app_access_login_required import login_required
from app.utilities.app_logging_helper import log_with_route
from app import csrf


@devices_bp.route('/poc-jsonb/<uuid:deviceuuid>', methods=['GET'])
@login_required
def view_device_poc_jsonb(deviceuuid):
    """
    POC: Render device page dynamically from JSONB audit data.
    This demonstrates the alternative architecture approach.
    """
    try:
        tenantuuid = session.get('tenant_uuid')
        if not tenantuuid:
            log_with_route(logging.ERROR, "No tenant_uuid found in session")
            return redirect(url_for('login_bp.login'))
        
        # Validate UUID format
        try:
            UUID(str(deviceuuid))
        except (ValueError, AttributeError, TypeError):
            log_with_route(logging.ERROR, f"Invalid device UUID: {deviceuuid}")
            return render_template('errors/404.html', message='Invalid device UUID'), 400
        
        # Single query to get device + audit data
        query = text("""
            SELECT 
                d.deviceuuid,
                d.devicename,
                d.hardwareinfo,
                d.health_score,
                d.created_at,
                o.orgname,
                g.groupname,
                daj.audit_data,
                daj.last_update,
                daj.last_json_timestamp
            FROM devices d
            LEFT JOIN organisations o ON d.orguuid = o.orguuid
            LEFT JOIN groups g ON d.groupuuid = g.groupuuid
            LEFT JOIN device_audit_json_test daj ON d.deviceuuid = daj.deviceuuid
            WHERE d.deviceuuid = :deviceuuid 
            AND d.tenantuuid = :tenantuuid
        """)
        
        result = db.session.execute(
            query, 
            {'deviceuuid': str(deviceuuid), 'tenantuuid': str(tenantuuid)}
        ).first()
        
        if not result:
            log_with_route(logging.ERROR, f"Device not found: {deviceuuid}")
            return render_template('errors/404.html', message='Device not found'), 404
        
        # Convert result to dictionary
        device_data = {
            'deviceuuid': str(result.deviceuuid),
            'devicename': result.devicename,
            'hardwareinfo': result.hardwareinfo,
            'health_score': result.health_score,
            'created_at': result.created_at,
            'orgname': result.orgname,
            'groupname': result.groupname,
            'audit_data': result.audit_data or {},
            'last_update': result.last_update,
            'last_json_timestamp': result.last_json_timestamp
        }
        
        log_with_route(
            logging.INFO, 
            f"POC JSONB: Loaded device {deviceuuid} with single query"
        )
        
        return render_template(
            'devices/poc-jsonb-device.html',
            device=device_data
        )
        
    except Exception as e:
        log_with_route(logging.ERROR, f"Error in POC JSONB view: {str(e)}", exc_info=True)
        return render_template('errors/500.html', message=str(e)), 500


@devices_bp.route('/poc-jsonb/<uuid:deviceuuid>/populate', methods=['POST'])
@csrf.exempt
@login_required
def populate_poc_jsonb(deviceuuid):
    """
    Utility endpoint: Populate POC table from existing payload file.
    This allows testing without waiting for new audit data.
    """
    try:
        tenantuuid = session.get('tenant_uuid')
        if not tenantuuid:
            return jsonify({'error': 'No tenant in session'}), 401
        
        # Verify device exists and belongs to tenant
        device = Devices.query.filter_by(
            deviceuuid=deviceuuid,
            tenantuuid=tenantuuid
        ).first()
        
        if not device:
            return jsonify({'error': 'Device not found'}), 404
        
        # Try to find a recent payload file for this device
        import os
        import glob
        from flask import current_app
        
        project_root = os.path.dirname(current_app.root_path)
        payload_dir = os.path.join(project_root, 'payloads', 'sucessfulImport')
        
        # Find most recent audit file for this device
        pattern = os.path.join(payload_dir, f"{deviceuuid}.*.audit.json")
        files = glob.glob(pattern)
        
        if not files:
            return jsonify({'error': 'No audit payload found for this device'}), 404
        
        # Get most recent file
        latest_file = max(files, key=os.path.getctime)
        
        with open(latest_file, 'r') as f:
            payload = json.load(f)
        
        audit_data = payload.get('data', {})

        # Extract key fields for quick filtering
        device_name = audit_data.get('device', {}).get('devicename')
        platform = audit_data.get('system', {}).get('platform')
        cpu_name = audit_data.get('cpu', {}).get('cpuname')
        total_memory = audit_data.get('memory', {}).get('totalMemory')

        # Upsert into test table
        from sqlalchemy.dialects.postgresql import insert

        stmt = insert(DeviceAuditJsonTest).values(
            deviceuuid=deviceuuid,
            audit_data=audit_data,
            last_update=int(payload.get('timestamp', 0)),
            last_json_timestamp=int(payload.get('timestamp', 0)),
            device_name=device_name,
            platform=platform,
            cpu_name=cpu_name,
            total_memory=total_memory
        ).on_conflict_do_update(
            index_elements=['deviceuuid'],
            set_={
                'audit_data': audit_data,
                'last_update': int(payload.get('timestamp', 0)),
                'last_json_timestamp': int(payload.get('timestamp', 0)),
                'device_name': device_name,
                'platform': platform,
                'cpu_name': cpu_name,
                'total_memory': total_memory
            }
        )

        db.session.execute(stmt)
        db.session.commit()

        log_with_route(
            logging.INFO,
            f"POC: Populated JSONB test table for device {deviceuuid} from {latest_file}"
        )

        return jsonify({
            'success': True,
            'message': 'POC table populated',
            'source_file': os.path.basename(latest_file),
            'device_name': device_name,
            'platform': platform
        }), 200

    except Exception as e:
        db.session.rollback()
        log_with_route(logging.ERROR, f"Error populating POC table: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

