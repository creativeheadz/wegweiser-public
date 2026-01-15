# Filepath: app/routes/devices/devices.py
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
from sqlalchemy.inspection import inspect

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

# Models and database
from app.models import (
    db, Devices, Organisations, Groups, DeviceMetadata, HealthScoreHistory,
    Accounts, Tenants, Roles, UserXOrganisation, TenantMetadata, Tags,
    TagsXDevices, Snippets, DeviceBattery, DeviceDrives, DeviceMemory,
    DeviceNetworks, DeviceStatus, Messages, DeviceUsers, DevicePartitions,
    DeviceCpu, DeviceGpu, DeviceBios, DeviceCollector, DevicePrinters, DevicePciDevices,
    DeviceUsbDevices, DeviceDrivers, Messages, TagsXDevices, DeviceRealtimeData, DeviceRealtimeHistory,
    DeviceConnectivity, AgentUpdateHistory
)
from app.utilities.guided_tour_manager import get_tour_for_page

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
from app.utilities.ui_time_converter import unix_to_utc

from app.utilities.langchain_utils import generate_entity_suggestions, generate_tool_recommendations
from app.utilities.ui_wegcoins_currencystate import get_tenant_wegcoin_balance
from app.routes.ai.ai import get_or_create_conversation
from app.utilities.sys_function_generate_healthscores import update_cascading_health_scores


# Forms
from app.forms.tenant_profile import TenantProfileForm
from app.forms.chat_form import ChatForm
from app.forms.device_forms import ManualDeviceProfilerForm, AIQuestionsForm, SaveProfileForm

# Load environment variables
load_dotenv()

# Logging setup - using centralized logging helper

# Import the blueprint
from . import devices_bp



bcrypt = Bcrypt()



#csrf = CSRFProtect()

@devices_bp.route('/', methods=['GET'])
@login_required
def handle_devices():
    """Optimized devices listing - only fetches data displayed in the card view"""
    tenantuuid = session.get('tenant_uuid')
    if not tenantuuid:
        return render_template('error.html', message='Tenant UUID is required'), 400

    # User preference for default devices layout
    user_default_layout = 'card'
    try:
        user_id = session.get('user_id')
        if user_id:
            user = Accounts.query.get(user_id)
            if user and user.user_preferences:
                pref = user.user_preferences.get('devices_layout')
                if pref in ('list', 'card'):
                    user_default_layout = pref
    except Exception as e:
        log_with_route(logging.WARNING, f"Unable to read user devices layout preference: {e}")

    try:
        # Optimized query - only fetch fields displayed in devices/index.html
        query = text("""
            SELECT
                d.deviceuuid,
                d.devicename,
                d.hardwareinfo,
                d.health_score,
                d.orguuid,
                d.groupuuid,
                o.orgname,
                g.groupname,
                dc.is_online,
                COALESCE(ds.last_update, dc.last_seen_online) as last_seen_online,
                CASE
                    WHEN dc.is_online THEN 'Online'
                    ELSE 'Offline'
                END as status
            FROM devices d
            LEFT JOIN organisations o ON d.orguuid = o.orguuid
            LEFT JOIN groups g ON d.groupuuid = g.groupuuid
            LEFT JOIN deviceconnectivity dc ON d.deviceuuid = dc.deviceuuid
            LEFT JOIN devicestatus ds ON d.deviceuuid = ds.deviceuuid
            WHERE d.tenantuuid = :tenantuuid
            ORDER BY d.devicename
        """)

        result = db.session.execute(query, {'tenantuuid': tenantuuid})
        devices_data = result.fetchall()

        # Icon mapping (FontAwesome classes)
        icon_mapping = {
            'Darwin': 'fab fa-apple',
            'Windows': 'fab fa-windows',
            'Linux': 'fab fa-linux',
            'Other': 'fas fa-desktop'
        }

        # Process devices for template and group by org/group
        devices_by_group = {}
        devices = []  # Keep flat list for backward compatibility

        for row in devices_data:
            device = {
                'deviceuuid': str(row.deviceuuid),
                'devicename': row.devicename,
                'hardwareinfo': row.hardwareinfo,
                'health_score': row.health_score,
                'orguuid': str(row.orguuid),
                'groupuuid': str(row.groupuuid),
                'orgname': row.orgname or 'No Organization',
                'groupname': row.groupname or 'No Group',
                'status': row.status,
                'is_online': row.is_online,
                'icon': icon_mapping.get(row.hardwareinfo, 'fas fa-desktop')
            }

            # Format last_seen timestamp
            if row.last_seen_online:
                try:
                    device['last_seen'] = unix_to_utc(row.last_seen_online)
                except (ValueError, TypeError):
                    device['last_seen'] = 'Never'
            else:
                device['last_seen'] = 'Never'

            devices.append(device)

            # Group devices by org/group combination
            org_group_key = f"{device['orgname']}/{device['groupname']}"
            if org_group_key not in devices_by_group:
                devices_by_group[org_group_key] = {
                    'orgname': device['orgname'],
                    'groupname': device['groupname'],
                    'orguuid': device['orguuid'],
                    'groupuuid': device['groupuuid'],
                    'devices': []
                }
            devices_by_group[org_group_key]['devices'].append(device)

        # Sort groups by org name, then group name
        sorted_groups = sorted(devices_by_group.items(), key=lambda x: (x[1]['orgname'], x[1]['groupname']))

        # Get organisations for filter dropdown
        organisations = Organisations.query.filter_by(tenantuuid=tenantuuid).all()

        # Get tour data for devices page
        tour_data = get_tour_for_page('devices', session.get('user_id'))

        return render_template('devices/index.html',
                             devices=devices,
                             devices_by_group=sorted_groups,
                             organisations=organisations,
                             tour_data=tour_data,
                             default_layout=user_default_layout)

    except Exception as e:
        log_with_route(logging.ERROR, f"Error handling devices: {e}")
        return render_template('error.html', message=str(e)), 500


@devices_bp.route('/preferences/layout', methods=['POST'])
@login_required
def set_devices_layout_preference():
    """Persist the user's preferred default layout for the devices page."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401

    payload = request.get_json(silent=True) or {}
    layout = payload.get('layout')
    if layout not in ('list', 'card'):
        return jsonify({'error': 'Invalid layout'}), 400

    try:
        user = Accounts.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        if user.user_preferences is None:
            user.user_preferences = {}

        user.user_preferences['devices_layout'] = layout
        db.session.commit()
        return jsonify({'ok': True, 'layout': layout}), 200
    except Exception as e:
        db.session.rollback()
        log_with_route(logging.ERROR, f"Error saving devices layout preference for user {user_id}: {e}", exc_info=True)
        return jsonify({'error': 'Failed to save preference'}), 500


@devices_bp.route('/create', methods=['POST'])
@login_required
def create_device():
    data = request.get_json()
    devicename = data.get('devicename')
    groupuuid = data.get('groupuuid')
    orguuid = data.get('orguuid')
    hardwareinfo = data.get('hardwareinfo')
    tenantuuid = session.get('tenant_uuid')


    if not (devicename and groupuuid and orguuid and tenantuuid):
        return jsonify({'error': 'Device name, group UUID, organisation UUID, and tenant UUID are required'}), 400

    try:
        group = Groups.query.filter_by(groupuuid=groupuuid, tenantuuid=tenantuuid).first()
        if not group:
            return jsonify({'error': 'Group does not exist'}), 400

        device_uuid = str(uuid.uuid4())
        new_device = Devices(
            deviceuuid=device_uuid,
            devicename=devicename,
            hardwareinfo=hardwareinfo,
            groupuuid=groupuuid,
            orguuid=orguuid,
            tenantuuid=tenantuuid,
            created_at=int(datetime.utcnow().timestamp())  # Store current time in Unix format
        )
        db.session.add(new_device)
        db.session.commit()

        return jsonify({'message': 'Device created successfully'}), 201
    except IntegrityError as e:
        db.session.rollback()
        log_with_route(logging.ERROR, f"Integrity error creating device: {e}")
        return jsonify({'error': 'Integrity error: ' + str(e)}), 400
    except Exception as e:
        db.session.rollback()
        log_with_route(logging.ERROR, f"Error creating device: {e}")
        return jsonify({'error': str(e)}), 500

@devices_bp.route('/organisations_groups', methods=['GET'])
@login_required
def get_organisations_groups():
    tenantuuid = session.get('tenant_uuid')
    if not tenantuuid:
        return jsonify({'error': 'Tenant UUID is required'}), 400

    try:
        organisations = Organisations.query.filter_by(tenantuuid=tenantuuid).all()
        result = []
        for org in organisations:
            groups = Groups.query.filter_by(orguuid=org.orguuid).all()
            result.append({
                'orguuid': org.orguuid,
                'orgname': org.orgname,
                'groups': [{'groupuuid': group.groupuuid, 'groupname': group.groupname} for group in groups]
            })
        return jsonify({'organisations': result}), 200
    except Exception as e:
        log_with_route(logging.ERROR, f"Error fetching organisations and groups: {e}")
        return jsonify({'error': str(e)}), 500




def ensure_backup_directory():
    """
    Ensure the backup directory exists and is properly configured at /var/log/wegweiser/device_backups.
    Falls back to /tmp if there are permission issues.
    """
    backup_dir = '/var/log/wegweiser/device_backups'

    try:
        # First try the preferred location
        os.makedirs(backup_dir, mode=0o755, exist_ok=True)

        # Verify we can actually write to it
        test_file = os.path.join(backup_dir, '.write_test')
        try:
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            log_with_route(logging.INFO, f"Using backup directory: {backup_dir}")
        except Exception as e:
            log_with_route(logging.WARNING, f"Cannot write to {backup_dir}: {str(e)}")
            raise

    except Exception as e:
        log_with_route(logging.WARNING,
            f"Failed to use {backup_dir}, falling back to /tmp/wegweiser/device_backups: {str(e)}")

        # Fall back to /tmp
        backup_dir = '/tmp/wegweiser/device_backups'
        os.makedirs(backup_dir, mode=0o755, exist_ok=True)
        log_with_route(logging.INFO, f"Using fallback backup directory: {backup_dir}")

    return backup_dir

def backup_device_data(device_uuid):
    """
    Create a complete backup of all device-related data before deletion.
    Returns the path to the backup file.
    """
    device = Devices.query.get(device_uuid)
    if not device:
        raise ValueError(f"Device {device_uuid} not found")

    # Initialize backup dictionary
    backup_data = {
        "device_info": {},
        "tables": {}
    }

    # Get device name for the filename
    device_name = device.devicename

    # Backup main device info
    device_mapper = inspect(Devices)
    for column in device_mapper.columns:
        value = getattr(device, column.key)
        if isinstance(value, UUID):
            value = str(value)
        backup_data["device_info"][column.key] = value

    # Define all related tables to backup
    related_tables = {
        "device_metadata": DeviceMetadata,
        "device_battery": DeviceBattery,
        "device_drives": DeviceDrives,
        "device_memory": DeviceMemory,
        "device_networks": DeviceNetworks,
        "device_status": DeviceStatus,
        "device_users": DeviceUsers,
        "device_partitions": DevicePartitions,
        "device_cpu": DeviceCpu,
        "device_gpu": DeviceGpu,
        "device_bios": DeviceBios,
        "device_collector": DeviceCollector,
        "device_printers": DevicePrinters,
        "device_pci_devices": DevicePciDevices,
        "device_usb_devices": DeviceUsbDevices,
        "device_drivers": DeviceDrivers,
        "device_connectivity": DeviceConnectivity,  # Add this line
        "messages": Messages,
        "tags_x_devices": TagsXDevices,
        "device_realtime_data": DeviceRealtimeData,
        "device_realtime_history": DeviceRealtimeHistory
    }

    # Backup data from each related table
    for table_name, model in related_tables.items():
        backup_data["tables"][table_name] = []

        # Special handling for Messages table which uses entityuuid and entity_type
        if model == Messages:
            results = model.query.filter_by(entityuuid=device_uuid, entity_type='device').all()
        else:
            results = model.query.filter_by(deviceuuid=device_uuid).all()

        for row in results:
            row_data = {}
            mapper = inspect(model)
            for column in mapper.columns:
                value = getattr(row, column.key)
                if isinstance(value, UUID):
                    value = str(value)
                elif isinstance(value, bytes):
                    value = value.decode('utf-8', errors='ignore')
                row_data[column.key] = value
            backup_data["tables"][table_name].append(row_data)

    # Ensure backup directory exists
    backup_dir = ensure_backup_directory()

    # Create filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_device_name = "".join(x for x in device_name if x.isalnum() or x in ('-', '_'))
    filename = f"{safe_device_name}_{device_uuid}_{timestamp}.json"
    filepath = os.path.join(backup_dir, filename)

    # Write backup to file
    with open(filepath, 'w') as f:
        json.dump(backup_data, f, indent=2, default=str)

    log_with_route(logging.INFO, f"Created backup at {filepath}")
    return filepath

def delete_device_cascade(device_uuid):
    """
    Delete a device and all its related data with proper error handling and logging.
    Uses dynamic discovery of dependent tables with correct deletion order.
    """
    try:
        device = Devices.query.get(device_uuid)
        if not device:
            raise ValueError(f"Device {device_uuid} not found")

        device_name = device.devicename  # Get name before deletion for the message

        # Define explicit deletion order to respect foreign key constraints
        # Messages must be deleted before conversations
        # Conversations must be deleted before devices
        deletion_order = [
            # First: Delete leaf tables (no other tables depend on them)
            ('messages', 'entityuuid', 'entity_type'),  # Special: uses entityuuid + entity_type
            ('health_score_history', 'entity_uuid', 'entity_type'),  # Special: entity_uuid + entity_type

            # Then: Delete all device-related data tables
            ('devicebattery', 'deviceuuid', None),
            ('devicebios', 'deviceuuid', None),
            ('devicecollector', 'deviceuuid', None),
            ('devicecpu', 'deviceuuid', None),
            ('devicedrivers', 'deviceuuid', None),
            ('devicedrives', 'deviceuuid', None),
            ('devicegpu', 'deviceuuid', None),
            ('devicememory', 'deviceuuid', None),
            ('devicemetadata', 'deviceuuid', None),
            ('devicenetworks', 'deviceuuid', None),
            ('devicepartitions', 'deviceuuid', None),
            ('devicepcidevices', 'deviceuuid', None),
            ('deviceprinters', 'deviceuuid', None),
            ('devicestatus', 'deviceuuid', None),
            ('deviceusbdevices', 'deviceuuid', None),
            ('deviceusers', 'deviceuuid', None),
            ('devicerealtimedata', 'deviceuuid', None),
            ('devicerealtimehistory', 'deviceuuid', None),
            ('deviceconnectivity', 'deviceuuid', None),
            ('device_osquery', 'deviceuuid', None),
            ('device_audit_json_test', 'deviceuuid', None),
            ('agent_update_history', 'deviceuuid', None),
            ('snippetsschedule', 'deviceuuid', None),
            ('tagsxdevices', 'deviceuuid', None),

            # Finally: Delete conversations (after messages are gone)
            ('conversations', 'deviceuuid', None),
        ]

        # Execute deletions in order
        for table_info in deletion_order:
            table_name = table_info[0]
            column_name = table_info[1]
            entity_type_column = table_info[2] if len(table_info) > 2 else None

            try:
                # Build the appropriate DELETE query
                if entity_type_column:
                    delete_query = text(
                        f"DELETE FROM {table_name} WHERE {column_name} = :device_uuid AND {entity_type_column} = 'device'"
                    )
                else:
                    delete_query = text(
                        f"DELETE FROM {table_name} WHERE {column_name} = :device_uuid"
                    )

                result = db.session.execute(delete_query, {'device_uuid': device_uuid})
                deleted_count = result.rowcount

                if deleted_count > 0:
                    log_with_route(logging.DEBUG, f"Deleted {deleted_count} records from {table_name} for device {device_uuid}")

            except Exception as table_error:
                # If a table doesn't exist or has issues, log and continue
                log_with_route(logging.DEBUG, f"Skipping {table_name}: {str(table_error)}")
                continue

        # Delete the device itself using raw SQL
        device_delete_query = text("DELETE FROM devices WHERE deviceuuid = :device_uuid")
        db.session.execute(device_delete_query, {'device_uuid': device_uuid})
        db.session.commit()

        log_with_route(logging.INFO, f"Successfully deleted device {device_name} ({device_uuid})")
        return True, device_name

    except Exception as e:
        db.session.rollback()
        log_with_route(logging.ERROR, f"Error in cascade delete for device {device_uuid}: {str(e)}")
        raise

@devices_bp.route('/delete', methods=['POST'])
def delete_device():
    """
    Enhanced device deletion endpoint that creates a backup before deletion
    """
    data = request.get_json()
    deviceuuids = data.get('deviceuuids')

    if not deviceuuids:
        flash('No devices selected for deletion', 'error')
        return jsonify({'error': 'No device UUIDs provided'}), 400

    success_count = 0
    error_count = 0
    results = []

    try:
        for device_uuid in deviceuuids:
            try:
                # Create backup first
                backup_path = backup_device_data(device_uuid)

                # Perform cascade deletion
                success, device_name = delete_device_cascade(device_uuid)

                if success:
                    success_count += 1
                    flash(f'Successfully deleted device {device_name}', 'success')
                    results.append({
                        'deviceuuid': device_uuid,
                        'status': 'success',
                        'backup_path': backup_path,
                        'message': f'Device {device_name} deleted successfully'
                    })

            except Exception as e:
                error_count += 1
                error_msg = str(e)
                flash(f'Error deleting device: {error_msg}', 'error')
                results.append({
                    'deviceuuid': device_uuid,
                    'status': 'error',
                    'error': error_msg
                })
                log_with_route(logging.ERROR, f"Error deleting device {device_uuid}: {error_msg}")

        summary_message = f"Deletion complete. {success_count} devices deleted successfully"
        if error_count > 0:
            summary_message += f", {error_count} failed"
        flash(summary_message, 'info')

        return jsonify({
            'message': summary_message,
            'results': results,
            'success_count': success_count,
            'error_count': error_count
        }), 200

    except Exception as e:
        error_msg = str(e)
        flash(f'Error during deletion process: {error_msg}', 'error')
        log_with_route(logging.ERROR, f"Error in delete_device route: {error_msg}")
        return jsonify({'error': error_msg}), 500




@devices_bp.route('/grouped', methods=['GET'])
@login_required
def get_grouped_devices():
    tenantuuid = session.get('tenant_uuid')
    if not tenantuuid:
        return jsonify({'error': 'Tenant UUID is required'}), 400

    try:
        organisations = Organisations.query.filter_by(tenantuuid=tenantuuid).all()
        result = []
        for org in organisations:
            groups = Groups.query.filter_by(orguuid=org.orguuid).all()
            group_list = []
            for group in groups:
                devices = Devices.query.filter_by(groupuuid=group.groupuuid).all()
                group_list.append({
                    'groupuuid': group.groupuuid,
                    'groupname': group.groupname,
                    'devices': [{'deviceuuid': device.deviceuuid, 'devicename': device.devicename} for device in devices]
                })
            result.append({
                'orguuid': org.orguuid,
                'orgname': org.orgname,
                'groups': group_list
            })
        return jsonify({'organisations': result}), 200
    except Exception as e:
        log_with_route(logging.ERROR, f"Error fetching grouped devices: {e}")
        return jsonify({'error': str(e)}), 500


@devices_bp.route('/<uuid:device_uuid>/tags', methods=['GET'])
@login_required
def get_device_tags(device_uuid):
    Tag = aliased(Tags)
    device_tags = db.session.query(Tag.taguuid, Tag.tagvalue).join(
        TagsXDevices, Tag.taguuid == TagsXDevices.taguuid
    ).filter(TagsXDevices.deviceuuid == device_uuid).all()

    return jsonify([{"uuid": str(tag.taguuid), "value": tag.tagvalue} for tag in device_tags])





@devices_bp.route('/manual-device-profiler', methods=['GET', 'POST'])
@login_required
def manual_device_profiler():
    form = ManualDeviceProfilerForm()
    ai_form = AIQuestionsForm()
    save_form = SaveProfileForm()

    if form.validate_on_submit():
        initial_data = {
            'name': form.device_name.data,
            'manufacturer': form.manufacturer.data,
            'device_type': form.device_type.data,
            'description': form.description.data
        }
        analysis = analyze_device_info(initial_data)
        return render_template('devices/manual_device_profiler.html',
                               form=form,
                               ai_form=ai_form,
                               save_form=save_form,
                               analysis=analysis,
                               initial_data=initial_data)

    return render_template('devices/manual_device_profiler.html',
                           form=form,
                           ai_form=ai_form,
                           save_form=save_form)

@devices_bp.route('/manual-device-profiler/save', methods=['POST'])
@login_required
def save_manual_device_profile():
    save_form = SaveProfileForm()
    if save_form.validate_on_submit():
        data = request.form.to_dict()
        recommendations = generate_recommendations(data)

        new_profile = ManualDeviceProfiles(
            name=data['device_name'],
            manufacturer=data['manufacturer'],
            device_type=data['device_type'],
            description=data['description'],
            additional_info=data.get('additional_info', ''),
            recommendations=recommendations,
            user_id=current_user.id,
            organization_id=current_user.organization_id
        )

        db.session.add(new_profile)
        db.session.commit()

        return jsonify({"success": True, "profile_id": new_profile.id})
    return jsonify({"success": False, "errors": save_form.errors}), 400


# COMMENTED OUT - Heavy table route no longer needed for main devices page
# @devices_bp.route('/table/data')
# @login_required
# def get_devices_table():
#     tenantuuid = session.get('tenant_uuid')
#     if not tenantuuid:
#         log_with_route(logging.ERROR, "Unauthorized access")
#         return jsonify({"error": "Unauthorized access"}), 403

#     devices = get_devices_table_data(tenantuuid)
#     if devices is None:
#         log_with_route(logging.ERROR, "Failed to fetch devices")
#         return jsonify({"error": "An error occurred while fetching devices"}), 500

#     log_with_route(logging.DEBUG, "Successfully fetched devices table data")
#     return jsonify(devices), 200



@devices_bp.route('/printers')
@login_required
def get_devices_printers():
    tenantuuid = session.get('tenant_uuid')
    if not tenantuuid:
        log_with_route(logging.ERROR, "Unauthorized access")
        return jsonify({"error": "Unauthorized access"}), 403

    query = text("""
    SELECT deviceuuid, last_update, last_json, printer_name, printer_driver, printer_location, printer_status, printer_port
    FROM public.v_printerlist
    WHERE tenantuuid = :tenantuuid
    """)

    try:
        result = db.session.execute(query, {'tenantuuid': tenantuuid})
        column_names = result.keys()
        printers = [dict(zip(column_names, row)) for row in result.fetchall()]
        log_with_route(logging.DEBUG, f"Fetched {len(printers)} printers for tenant {tenantuuid}")
        return jsonify(printers), 200
    except Exception as e:
        log_with_route(logging.ERROR, f"Error fetching printers: {str(e)}")
        return jsonify({"error": "An error occurred while fetching printers"}), 500


@devices_bp.route('/eventlogs/data')
@login_required
def get_devices_eventlogs():
    tenantuuid = session.get('tenant_uuid')
    if not tenantuuid:
        log_with_route(logging.ERROR, "Unauthorized access")
        return jsonify({"error": "Unauthorized access"}), 403

    query = text("""
    SELECT devicename, metalogos_type, ai_analysis, created_at, to_timestamp
    FROM public.v_latestanalysis
    WHERE tenantuuid = :tenantuuid
    AND metalogos_type IN ('eventsFiltered-Application', 'eventsFiltered-Security', 'eventsFiltered-System')
    ORDER BY devicename, metalogos_type
    """)

    try:
        result = db.session.execute(query, {'tenantuuid': tenantuuid})
        column_names = result.keys()
        eventlogs = [dict(zip(column_names, row)) for row in result.fetchall()]

        log_with_route(logging.DEBUG, f"Number of eventlogs fetched: {len(eventlogs)}")
        if eventlogs:
            log_with_route(logging.DEBUG, f"Sample eventlog: {eventlogs[0]}")

        return jsonify(eventlogs), 200
    except Exception as e:
        log_with_route(logging.ERROR, f"Error fetching event logs: {str(e)}")
        return jsonify({"error": "An error occurred while fetching event logs"}), 500




# COMMENTED OUT - Heavy table route with eventlogs/printers - can be reactivated later for detailed view
# @devices_bp.route('/table')
# @login_required
# def populate_devices_table():
#     tenantuuid = session.get('tenant_uuid')
#     try:
#         devices, columns = get_devices_table_data(tenantuuid)
#         eventlogs_response, eventlogs_status = get_devices_eventlogs()
#         printers_response, printers_status = get_devices_printers()

#         if devices is None or columns is None or eventlogs_status != 200 or printers_status != 200:
#             if LOG_DEVICES_TABLE:
#                 log_with_route(logging.ERROR, "An error occurred while fetching data")
#             return "An error occurred while fetching data", 500

#         eventlogs = eventlogs_response.json
#         printers = printers_response.json

#         # Icon mapping (FontAwesome classes)
#         icon_mapping = {
#             'Darwin': 'fab fa-apple',
#             'Windows': 'fab fa-windows',
#             'Linux': 'fab fa-linux',
#             'Other': 'fas fa-desktop'  # Fallback icon
#         }

#         # Organize event logs by device
#         eventlogs_by_device = {}
#         for log in eventlogs:
#             devicename = log['devicename']
#             if devicename not in eventlogs_by_device:
#                 eventlogs_by_device[devicename] = {}
#             eventlogs_by_device[devicename][log['metalogos_type']] = {
#                 'ai_analysis': log['ai_analysis'],
#                 'created_at': log['to_timestamp']
#             }

#         # Organize printers by device
#         printers_by_device = {}
#         for printer in printers:
#             deviceuuid = printer['deviceuuid']
#             if deviceuuid not in printers_by_device:
#                 printers_by_device[deviceuuid] = []
#             printers_by_device[deviceuuid].append(printer)

#         # Combine devices with event logs and printers, assign icons
#         for device in devices:
#             deviceuuid = device['deviceuuid']
#             hardwareinfo = device.get('hardwareinfo', 'Other')
#             device['eventlogs'] = eventlogs_by_device.get(device['devicename'], {})
#             device['printers'] = printers_by_device.get(deviceuuid, [])
#             device['icon'] = icon_mapping.get(hardwareinfo, 'fas fa-desktop')

#         if LOG_DEVICES_TABLE and current_app.debug:
#             log_with_route(logging.DEBUG, f"Number of devices: {len(devices)}")
#             if devices:
#                 log_with_route(logging.DEBUG, f"Sample device: {devices[0]}")
#             log_with_route(logging.DEBUG, f"Columns: {columns}")

#         return render_template('devices/index.html', devices=devices, columns=columns)

#     except Exception as e:
#         if LOG_DEVICES_TABLE:
#             log_with_route(logging.ERROR, f"Error in populate_devices_table: {str(e)}")
#         return "An error occurred", 500


@devices_bp.route('/<string:deviceuuid>/eventlog/<log_type>')
@login_required
def get_device_eventlog(deviceuuid, log_type):
    try:
        deviceuuid = UUID(deviceuuid)
    except ValueError:
        log_with_route(logging.ERROR, "Invalid device UUID")
        return "Invalid device UUID", 400

    tenantuuid = session.get('tenant_uuid')
    if not tenantuuid:
        log_with_route(logging.ERROR, "No tenant_uuid found in session")
        return "Unauthorized access", 403

    valid_log_types = ['eventsFiltered-Application', 'eventsFiltered-Security', 'eventsFiltered-System']
    if log_type not in valid_log_types:
        log_with_route(logging.ERROR, "Invalid log type")
        return "Invalid log type", 400

    query = text("""
    SELECT dm.ai_analysis, dm.created_at
    FROM public.devicemetadata dm
    JOIN public.devices d ON dm.deviceuuid = d.deviceuuid
    WHERE dm.deviceuuid = :deviceuuid
      AND d.tenantuuid = :tenantuuid
      AND dm.metalogos_type = :log_type
    ORDER BY dm.created_at DESC
    LIMIT 1
    """)

    try:
        result = db.session.execute(query, {'deviceuuid': deviceuuid, 'tenantuuid': tenantuuid, 'log_type': log_type})
        row = result.fetchone()

        if row:
            eventlog, created_at = row
            readable_time = datetime.fromtimestamp(created_at).strftime('%Y-%m-%d %H:%M:%S')
            eventlog_html = f"<p>Timestamp: {readable_time}</p>" + Markup(eventlog)
            log_with_route(logging.DEBUG, f"Fetched event log for device {deviceuuid} and log type {log_type}")
            return eventlog_html
        else:
            log_with_route(logging.DEBUG, f"No event logs available for device {deviceuuid} and log type {log_type}")
            return Markup('<p>No event logs available</p>')
    except Exception as e:
        log_with_route(logging.ERROR, f"Error fetching event log: {str(e)}")
        return f"An error occurred while fetching event logs: {str(e)}", 500






@devices_bp.route('/device/<uuid:device_uuid>/health_history')
@login_required
def get_device_health_history(device_uuid):
    """
    Get the health score history for a specific device.

    Args:
        device_uuid: UUID of the device

    Returns:
        JSON response containing the device's health score history data
    """
    try:
        # Verify device exists and get current health score
        device = Devices.query.get_or_404(device_uuid)

        # Get historical health scores
        history = HealthScoreHistory.query.filter_by(
            entity_type='device',
            entity_uuid=device_uuid
        ).order_by(HealthScoreHistory.timestamp).all()

        # Format data for response
        data = [{'x': h.timestamp.isoformat(), 'y': h.health_score} for h in history]

        # Add current health score if available
        if device.health_score is not None:
            data.append({
                'x': datetime.utcnow().isoformat(),
                'y': device.health_score
            })

        return jsonify(data)

    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        log_with_route(
            logging.ERROR,
            f"Error in get_device_health_history: {str(e)}",
            exc_info=True
        )
        return jsonify({'error': 'An unexpected error occurred'}), 500



################### HELPER FUNCTIONS #######################

def checkDir(dirToCheck):
    if os.path.isdir(dirToCheck):
        log_with_route(logging.INFO, f'{dirToCheck} already exists.')
    else:
        log_with_route(logging.INFO, f'{dirToCheck} does not exist. Creating...')
        try:
            os.makedirs(dirToCheck)
            log_with_route(logging.INFO, f'{dirToCheck} created.')
        except Exception as e:
            log_with_route(logging.ERROR, f'Failed to create {dirToCheck}. Reason: {e}')

def sendJsonPayloadFlask(payload, host, endpoint):
	import requests
	debugMode = True
	url 		= f'https://{host}{endpoint}'
	if debugMode == True:
		log_with_route(logging.DEBUG, f'payload to send: {payload}')
		log_with_route(logging.DEBUG, f'Attempting to connect to {url}')
	headers 	= {'Content-Type': 'application/json'}
	response 	= requests.post(url, headers=headers, data=json.dumps(payload))
	return(response)

def lookupSnippetId(snippetName):
	log_with_route(logging.DEBUG, f'Attempting to get snippetuuid for {snippetName}')
	tenantUuid  = '00000000-0000-0000-0000-000000000000'
	snippets    = Snippets.query.filter_by(snippetname = snippetName, tenantuuid = tenantUuid).first()
	snippetUuid = str(snippets.snippetuuid)
	log_with_route(logging.DEBUG, f'snippetUuid for {snippetName} is {snippetUuid}')
	return(snippetUuid)

def getDelayedStartTime(minsDelay):
	from datetime import datetime, timedelta
	now 				= datetime.now()
	delayedStartTime 	= (now + timedelta(minutes=minsDelay)).strftime("%H:%M")
	return(delayedStartTime)

def scheduleDefaultSnippets(deviceUuid, hardwareinfo=None):
	host 			= 'app.wegweiser.tech'
	endpoint 		= '/snippets/schedulesnippet'

	# Choose the appropriate audit script based on platform
	if hardwareinfo == 'Darwin':
		audit_script = 'MacAudit.py'
		log_with_route(logging.INFO, f'Scheduling macOS-specific audit script for device {deviceUuid}')
	else:
		audit_script = 'fullAudit.py'
		log_with_route(logging.INFO, f'Scheduling standard audit script for device {deviceUuid} (platform: {hardwareinfo})')

	payloadList = [
		{
		'snippetuuid': 	lookupSnippetId('zipLogs.py'),
		'deviceuuid': 	deviceUuid,
		'recstring': 	'1d',
		'starttime': 	'00:00'},
		{
		'snippetuuid': 	lookupSnippetId(audit_script),
		'deviceuuid': 	deviceUuid,
		'recstring': 	'1d',
		'starttime': 	getDelayedStartTime(3)
		},
		{
		'snippetuuid': 	lookupSnippetId('quickCheckin.py'),
		'deviceuuid': 	deviceUuid,
		'recstring': 	'5m',
		'starttime': 	getDelayedStartTime(4)
        },
        {
        'snippetuuid': 	lookupSnippetId('eventLogAudit.py'),
		'deviceuuid': 	deviceUuid,
		'recstring': 	'1d',
		'starttime': 	getDelayedStartTime(10)
        },
        {
        'snippetuuid': 	lookupSnippetId('realtime_cpu.py'),
		'deviceuuid': 	deviceUuid,
		'recstring': 	'1m',
		'starttime': 	getDelayedStartTime(1)
        },
        {
        'snippetuuid': 	lookupSnippetId('realtime_memory.py'),
		'deviceuuid': 	deviceUuid,
		'recstring': 	'1m',
		'starttime': 	getDelayedStartTime(1)
        }
        ]

	for payload in payloadList:
		scheduleSuccess = 999
		while scheduleSuccess != 200:
			log_with_route(logging.INFO, f'Attempting to schedule {payload["snippetuuid"]}...')
			response 		= sendJsonPayloadFlask(payload, host, endpoint)
			scheduleSuccess = response.status_code
			log_with_route(logging.DEBUG, f'scheduleSuccess: {scheduleSuccess}')
			if scheduleSuccess != 200:
				log_with_route(logging.WARNING, f'Failed to schedule {payload["snippetuuid"]}. Retrying...')
			else:
				log_with_route(logging.INFO, f'Successfully scheduled {payload["snippetuuid"]}')
