# Filepath: app/routes/devices/devices_details.py
# Filepath: app/routes/tenant/devices.py
# Flask core imports
from flask import (
    Blueprint, session, render_template, request, redirect, url_for, flash,
    current_app, jsonify, g, render_template_string
)
from flask_mail import Message
from flask_bcrypt import Bcrypt
from flask_wtf.csrf import CSRFProtect

# SQLAlchemy imports
from sqlalchemy import text, desc
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import joinedload, aliased

# Standard library imports
import logging
import json
import os
import time
import uuid
from uuid import UUID
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from markupsafe import Markup
from werkzeug.utils import secure_filename
import secrets
import string
from typing import Dict, Any
import json

# Models and database
from app.models import (
    db, Devices, Organisations, Groups, DeviceMetadata, HealthScoreHistory,
    Accounts, Tenants, Roles, UserXOrganisation, TenantMetadata, Tags,
    TagsXDevices, Snippets, DeviceBattery, DeviceDrives, DeviceMemory,
    DeviceNetworks, DeviceStatus, Messages
)
import re


# Utilities
from app import csrf, mail, master_permission, admin_or_master_permission
from app.utilities.app_access_login_required import login_required
from app.utilities.app_access_role_required import role_required
from app.utilities.notifications import create_notification
from app.utilities.ui_devices_delete_device import delete_devices
from app.utilities.app_logging_helper import log_with_route
from app.utilities.ui_devices_printers import fetch_printers_by_device
from app.utilities.ui_devices_eventlogs import fetch_event_logs_by_device
from app.utilities.ui_devices_devicetable import get_devices_table_data
from app.utilities.ui_devices_devicedetails import get_device_details

from app.utilities.langchain_utils import generate_entity_suggestions, generate_tool_recommendations
from app.utilities.ui_wegcoins_currencystate import get_tenant_wegcoin_balance
from app.routes.ai.ai import get_or_create_conversation


# Forms
from app.forms.tenant_profile import TenantProfileForm
from app.forms.chat_form import ChatForm

# Load environment variables
load_dotenv()

# Logging setup
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Import the blueprint
from . import devices_bp



bcrypt = Bcrypt()



#csrf = CSRFProtect()

import re




def categorize_analysis(analysis_type):
    """Categorize analysis based on type"""
    categories = {
        'System': ['eventsFiltered-System', 'msinfo-SystemSoftwareConfig',
                   'msinfo-SystemHardwareConfig'],
        'Security': ['eventsFiltered-Security', 'authFiltered'],
        'Applications': ['eventsFiltered-Application', 'msinfo-InstalledPrograms',
                         'msinfo-RecentAppCrashes'],
        'Hardware': ['windrivers', 'msinfo-StorageInfo', 'msinfo-NetworkConfig'],
        'Logs': ['journalFiltered', 'syslogFiltered', 'kernFiltered']
    }

    for category, types in categories.items():
        if analysis_type in types:
            return category
    return 'Other'

# Define specific icons for analysis types
def get_analysis_icon(analysis_type):
    """Get specific icon for analysis type"""
    specific_icons = {
        'macos-hardware-eol-analysis': 'fa-microchip',
        'macos-os-version-analysis': 'fab fa-apple',
        'macos-log-health-analysis': 'fa-heartbeat'
    }

    if analysis_type in specific_icons:
        return specific_icons[analysis_type]

    # Fall back to category icons
    category = categorize_analysis(analysis_type)
    category_icons = {
        'System': 'fa-cogs',
        'Security': 'fa-shield-alt',
        'Applications': 'fa-laptop-code',
        'Hardware': 'fa-microchip',
        'Network': 'fa-network-wired',
        'Storage': 'fa-database',
        'Logs': 'fa-file-alt',
        'Other': 'fa-question-circle'
    }
    return category_icons.get(category, 'fa-question-circle')

@devices_bp.route('/details/<uuid:device_uuid>/analyses', methods=['GET'])
@login_required
def get_device_analyses(device_uuid):
    try:
        # Add timeout parameter to the request
        timeout = 10  # 10 seconds timeout

        # Validate UUID format
        try:
            UUID(str(device_uuid))
        except (ValueError, AttributeError, TypeError):
            log_with_route(logging.ERROR, f"Invalid device UUID provided: {device_uuid}")
            return jsonify({'error': 'Invalid device UUID provided'}), 400

        # Fetch the tenant object
        tenant = Tenants.query.filter_by(tenantuuid=session['tenant_uuid']).first()
        if not tenant:
            return jsonify({'error': 'Tenant not found'}), 404

        # Verify device exists before proceeding
        device = Devices.query.filter_by(deviceuuid=device_uuid).first()
        if not device:
            log_with_route(logging.ERROR, f"Device with UUID {device_uuid} not found")
            return jsonify({'error': 'Device not found'}), 404

        # Get friendly titles from the tenant's analysis groups
        analysis_groups = tenant.get_analysis_groups()

        # Create a mapping of `type` to `name`
        friendly_titles = {}
        for group in analysis_groups.values():
            for analysis in group:
                friendly_titles[analysis['type']] = analysis['name']

        # Get device platform information to filter platform-specific analyses
        device_status = DeviceStatus.query.filter_by(deviceuuid=device_uuid).first()
        is_windows = device_status and device_status.agent_platform.startswith('Windows') if device_status else False

        # Optimize the query by splitting it into two simpler queries
        # First, get the latest processed entries, filtering out windrivers for non-Windows devices
        windrivers_filter = ""
        if not is_windows:
            windrivers_filter = "AND metalogos_type != 'windrivers'"

        latest_analyses = db.session.execute(text(f"""
            SELECT DISTINCT ON (metalogos_type)
                deviceuuid,
                metalogos_type,
                ai_analysis,
                score,
                analyzed_at,
                created_at
            FROM devicemetadata
            WHERE deviceuuid = :device_uuid
            AND processing_status = 'processed'
            {windrivers_filter}
            ORDER BY metalogos_type, created_at DESC
        """), {'device_uuid': str(device_uuid)}).fetchall()

        # Then, get pending counts in a separate query, applying same platform filtering
        pending_counts = db.session.execute(text(f"""
            SELECT metalogos_type, COUNT(*) as pending_count
            FROM devicemetadata
            WHERE deviceuuid = :device_uuid
            AND processing_status = 'pending'
            {windrivers_filter}
            GROUP BY metalogos_type
        """), {'device_uuid': str(device_uuid)}).fetchall()

        # Get total analysis counts for each type
        total_counts = db.session.execute(text(f"""
            SELECT metalogos_type, COUNT(*) as total_count
            FROM devicemetadata
            WHERE deviceuuid = :device_uuid
            {windrivers_filter}
            GROUP BY metalogos_type
        """), {'device_uuid': str(device_uuid)}).fetchall()

        # Create mappings
        pending_map = {row.metalogos_type: row.pending_count for row in pending_counts}
        total_map = {row.metalogos_type: row.total_count for row in total_counts}

        # Process the results
        analyses_data = []
        for row in latest_analyses:
            # Get the previous score for this type
            prev_score = db.session.execute(text("""
                SELECT score
                FROM devicemetadata
                WHERE deviceuuid = :device_uuid
                AND metalogos_type = :type
                AND processing_status = 'processed'
                AND created_at < :created_at
                ORDER BY created_at DESC
                LIMIT 1
            """), {
                'device_uuid': str(device_uuid),
                'type': row.metalogos_type,
                'created_at': row.created_at
            }).scalar()

            # Calculate next scheduled analysis time using actual analysis schedules
            # These are the real analysis intervals from task definitions, not worker check intervals
            analysis_schedules = {
                'msinfo-NetworkConfig': 21600,  # 6 hours
                'msinfo-RecentAppCrashes': 1800,  # 30 minutes
                'msinfo-SystemSoftwareConfig': 43200,  # 12 hours
                'syslogFiltered': 3600,  # 1 hour
                'msinfo-StorageInfo': 43200,  # 12 hours
                'msinfo-InstalledPrograms': 43200,  # 12 hours
                'eventsFiltered-System': 3600,  # 1 hour
                'journalFiltered': 3600,  # 1 hour
                'authFiltered': 3600,  # 1 hour
                'eventsFiltered-Application': 1800,  # 30 minutes
                'eventsFiltered-Security': 3600,  # 1 hour
                'kernFiltered': 10800,  # 3 hours
                'msinfo-SystemHardwareConfig': 3600,  # 1 hour
                'windrivers': 14400,  # 4 hours
                'macos-hardware-eol-analysis': 0,  # Run once (one-time analysis)
                'macos-os-version-analysis': 86400,  # Daily
                'macos-log-health-analysis': 604800,  # Weekly
            }

            schedule_interval = analysis_schedules.get(row.metalogos_type, 3600)  # Default to 1 hour
            next_analysis = None

            if schedule_interval > 0:  # Only calculate if it's a recurring analysis
                last_analysis_time = datetime.fromtimestamp(row.analyzed_at)
                next_analysis = last_analysis_time + timedelta(seconds=schedule_interval)
            # If schedule_interval is 0, it's a one-time analysis, so next_analysis stays None

            # Calculate status indicators
            pending_count = pending_map.get(row.metalogos_type, 0)
            total_count = total_map.get(row.metalogos_type, 1)  # At least 1 (current analysis)
            has_new_data = pending_count > 0

            analyses_data.append({
                'type': row.metalogos_type,
                'name': friendly_titles.get(row.metalogos_type, row.metalogos_type),
                'analysis': row.ai_analysis,
                'score': row.score if row.score is not None else 0,
                'previous_score': prev_score if prev_score is not None else None,
                'analyzed_at': datetime.fromtimestamp(row.analyzed_at),
                'next_analysis': next_analysis,
                'pending_count': pending_count,
                'total_count': total_count,
                'has_new_data': has_new_data,
                'status_text': 'New data received' if has_new_data else 'Waiting for data',
                'icon': get_analysis_icon(row.metalogos_type)
            })

        # Sort by score descending
        analyses_data.sort(key=lambda x: x['score'], reverse=True)

        return render_template('devices/deviceanalyses.html', analyses=analyses_data)

    except SQLAlchemyError as e:
        db.session.rollback()
        log_with_route(logging.ERROR, f"Database error in analyses: {str(e)}", exc_info=True)
        return jsonify({'error': 'Database error occurred'}), 500
    except Exception as e:
        log_with_route(logging.ERROR, f"Error fetching analyses: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to fetch analyses'}), 500
