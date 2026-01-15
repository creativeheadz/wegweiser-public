# Filepath: app/routes/devices/lynis.py
"""
Lynis Security Audit Routes

Handles ingestion of Lynis security audit results from agents
and provides historical tracking endpoints.
"""

# Flask core imports
from flask import Blueprint, request, jsonify, current_app

# SQLAlchemy imports
from sqlalchemy.exc import SQLAlchemyError
from uuid import UUID

# Standard library imports
import logging
import time
import uuid

# Models and database
from app.models import db, Devices, DeviceMetadata, Tenants

# Utilities
from app.utilities.app_access_login_required import login_required
from app.utilities.app_logging_helper import log_with_route

# Celery task
from app.tasks.lynis_parser_task import parse_lynis_audit

logger = logging.getLogger(__name__)

# Create blueprint
lynis_bp = Blueprint('lynis', __name__)


@lynis_bp.route('/devices/<device_id>/lynis/ingest', methods=['POST'])
@login_required
def ingest_lynis_results(device_id):
    """
    Accept Lynis JSON results from agent, validate toggle, store, and queue parsing.

    Expected JSON payload:
    {
        "results": {...lynis json data...}
    }

    Returns:
        202 Accepted: Task queued successfully
        400 Bad Request: Invalid input
        403 Forbidden: Lynis audits not enabled for tenant
        404 Not Found: Device not found
        500 Internal Server Error: Processing error
    """
    try:
        # Validate device UUID format
        try:
            device_uuid = UUID(device_id)
        except (ValueError, AttributeError):
            log_with_route(logging.ERROR, f"Invalid device UUID format: {device_id}")
            return jsonify({'error': 'Invalid device UUID format'}), 400

        # Load device and verify it exists
        device = db.session.query(Devices).filter_by(deviceuuid=device_uuid).first()
        if not device:
            log_with_route(logging.ERROR, f"Device not found: {device_id}")
            return jsonify({'error': 'Device not found'}), 404

        # Verify tenant isolation (device belongs to user's tenant)
        from flask import g
        if hasattr(g, 'tenantuuid') and device.tenantuuid != g.tenantuuid:
            log_with_route(logging.WARNING, f"Tenant isolation violation - Device {device_id} not in tenant {g.tenantuuid}")
            return jsonify({'error': 'Access denied'}), 403

        # Load tenant
        tenant = db.session.query(Tenants).get(device.tenantuuid)
        if not tenant:
            log_with_route(logging.ERROR, f"Tenant not found: {device.tenantuuid}")
            return jsonify({'error': 'Tenant not found'}), 500

        # CHECK TOGGLE: Verify Lynis audits are enabled for this tenant
        if not tenant.is_analysis_enabled('lynis-audit'):
            log_with_route(logging.INFO, f"Lynis audit rejected - disabled for tenant {tenant.tenantname}")
            return jsonify({
                'error': 'Lynis audits are not enabled for this tenant',
                'message': 'Please enable Lynis Security Audit in Analysis Settings'
            }), 403

        # Get Lynis results from request
        lynis_json = request.json.get('results')
        if not lynis_json:
            log_with_route(logging.ERROR, f"Missing 'results' in request body")
            return jsonify({'error': 'Missing results in request body'}), 400

        # Validate JSON structure (basic check for required fields)
        if not isinstance(lynis_json, (dict, str)):
            log_with_route(logging.ERROR, f"Invalid results format - expected dict or string")
            return jsonify({'error': 'Invalid results format'}), 400

        # If string, validate it's parseable JSON
        if isinstance(lynis_json, str):
            try:
                import json
                json.loads(lynis_json)
            except json.JSONDecodeError as e:
                log_with_route(logging.ERROR, f"Invalid JSON in results: {str(e)}")
                return jsonify({'error': f'Invalid JSON: {str(e)}'}), 400

        # Create DeviceMetadata entry with raw Lynis data
        metadata = DeviceMetadata(
            metadatauuid=uuid.uuid4(),
            deviceuuid=device.deviceuuid,
            metalogos_type='lynis_audit',
            metalogos=lynis_json,  # Store raw JSON (JSONB column)
            processing_status='pending',  # Will be updated by Celery task
            created_at=int(time.time())
        )

        db.session.add(metadata)
        db.session.commit()

        log_with_route(logging.INFO, f"Lynis audit stored - Device: {device.devicename}, Metadata ID: {metadata.metadatauuid}")

        # Queue Celery task for async parsing (no AI, no wegcoins)
        task = parse_lynis_audit.delay(str(metadata.metadatauuid))

        log_with_route(logging.INFO, f"Queued Lynis parsing task {task.id} for device {device.devicename}")

        return jsonify({
            'status': 'queued',
            'message': 'Lynis audit received and queued for processing',
            'metadata_id': str(metadata.metadatauuid),
            'task_id': task.id,
            'device_name': device.devicename
        }), 202

    except SQLAlchemyError as e:
        db.session.rollback()
        log_with_route(logging.ERROR, f"Database error ingesting Lynis audit: {str(e)}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500

    except Exception as e:
        db.session.rollback()
        log_with_route(logging.ERROR, f"Unexpected error ingesting Lynis audit: {str(e)}", exc_info=True)
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500


@lynis_bp.route('/devices/<device_id>/lynis/history', methods=['GET'])
@login_required
def lynis_history(device_id):
    """
    Get Lynis audit history for a device (for trend charts).

    Query params:
        limit: Number of audits to return (default: 10)

    Returns:
        200 OK: Historical data
        404 Not Found: Device not found
        403 Forbidden: Access denied
    """
    try:
        # Validate device UUID format
        try:
            device_uuid = UUID(device_id)
        except (ValueError, AttributeError):
            return jsonify({'error': 'Invalid device UUID format'}), 400

        # Load device
        device = db.session.query(Devices).filter_by(deviceuuid=device_uuid).first()
        if not device:
            return jsonify({'error': 'Device not found'}), 404

        # Verify tenant isolation
        from flask import g
        if hasattr(g, 'tenantuuid') and device.tenantuuid != g.tenantuuid:
            return jsonify({'error': 'Access denied'}), 403

        # Get limit from query params
        limit = request.args.get('limit', 10, type=int)
        limit = min(limit, 50)  # Cap at 50

        # Query Lynis audit history
        audits = db.session.query(DeviceMetadata).filter_by(
            deviceuuid=device_uuid,
            metalogos_type='lynis_audit',
            processing_status='processed'
        ).order_by(DeviceMetadata.created_at.desc()).limit(limit).all()

        if not audits:
            return jsonify({
                'device_name': device.devicename,
                'audits': [],
                'message': 'No Lynis audits found for this device'
            }), 200

        # Parse each audit to extract key metrics
        history_data = []
        for audit in reversed(audits):  # Reverse to get chronological order
            # Parse metalogos to get suggestions/warnings counts
            lynis_data = audit.metalogos
            warnings_count = len(lynis_data.get('warnings', []))
            suggestions_count = len(lynis_data.get('suggestions', []))

            history_data.append({
                'timestamp': audit.created_at,
                'date': time.strftime('%Y-%m-%d', time.localtime(audit.created_at)),
                'score': audit.score,
                'warnings': warnings_count,
                'suggestions': suggestions_count
            })

        # Prepare data for Chart.js
        response = {
            'device_name': device.devicename,
            'labels': [item['date'] for item in history_data],
            'scores': [item['score'] for item in history_data],
            'warnings': [item['warnings'] for item in history_data],
            'suggestions': [item['suggestions'] for item in history_data],
            'count': len(history_data)
        }

        return jsonify(response), 200

    except Exception as e:
        log_with_route(logging.ERROR, f"Error fetching Lynis history: {str(e)}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500
