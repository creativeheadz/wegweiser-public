# Filepath: app/routes/devices/devices_deviceuuid.py
# Filepath: app/routes/tenant/devices.py
# Flask core imports
from flask import session, render_template, redirect, url_for, flash, request, jsonify

# Standard library imports
import logging
from dotenv import load_dotenv

# Device Data Providers
from app.utilities.device_data_providers import DeviceDataAggregator

# Utilities
from app.utilities.app_access_login_required import login_required
from app.utilities.app_logging_helper import log_with_route
# Removed legacy printers import - now using DevicePrintersProvider via DeviceDataAggregator

# Forms
from app.forms.chat_form import ChatForm

# Load environment variables
load_dotenv()

# Logging setup
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Import the blueprint
from . import devices_bp



@devices_bp.route('/<uuid:deviceuuid>', methods=['GET'])
@login_required
def view_device(deviceuuid):
    try:
        tenantuuid = session.get('tenant_uuid')
        if not tenantuuid:
            log_with_route(logging.ERROR, "No tenant_uuid found in session")
            return redirect(url_for('login_bp.login'))

        # Convert UUID to string for database queries
        deviceuuid_str = str(deviceuuid)

        # Initialize the device data aggregator
        aggregator = DeviceDataAggregator(deviceuuid_str, tenantuuid)

        # Fetch all device data using the modular system
        device_data = aggregator.get_all_data()

        if not device_data or 'basic' not in device_data:
            log_with_route(logging.ERROR, f"Device with UUID {deviceuuid_str} not found")
            flash('Device not found', 'error')
            return redirect(url_for('devices_bp.handle_devices'))

        # Create the chat form instance
        form = ChatForm()

        # Printers data is now handled by DevicePrintersProvider via DeviceDataAggregator
        # No need for legacy override - the aggregator already includes printers data

        # Extract widgets from metadata if available
        if 'metadata' in device_data and device_data['metadata']:
            device_data['widgets'] = device_data['metadata'].get('widgets', [])
        else:
            device_data['widgets'] = []

        # Extract event logs and regular analyses from metadata
        if 'metadata' in device_data and device_data['metadata']:
            metadata = device_data['metadata']
            device_data['eventlogs'] = metadata.get('event_logs', {})
            device_data['regular_analyses'] = metadata.get('regular_analyses', {})
        else:
            device_data['eventlogs'] = {}
            device_data['regular_analyses'] = {}

        # Flatten the modular data structure for template compatibility
        flattened_device_data = _flatten_device_data(device_data)

        # Query for latest Lynis security audit
        from app.models import DeviceMetadata
        latest_lynis_audit = DeviceMetadata.query.filter_by(
            deviceuuid=deviceuuid,
            metalogos_type='lynis_audit'
        ).order_by(DeviceMetadata.created_at.desc()).first()

        # Query for latest Loki malware scan
        latest_loki_scan = DeviceMetadata.query.filter_by(
            deviceuuid=deviceuuid,
            metalogos_type='loki-scan'
        ).order_by(DeviceMetadata.created_at.desc()).first()

        return render_template(
            'devices/index-single-device.html',
            device=flattened_device_data,
            form=form,
            latest_lynis_audit=latest_lynis_audit,
            latest_loki_scan=latest_loki_scan
        )

    except Exception as e:
        log_with_route(logging.ERROR, f"Error fetching device details: {str(e)}")
        flash('An error occurred while fetching device details', 'error')
        return redirect(url_for('devices_bp.handle_devices'))


def _flatten_device_data(modular_data):
    """
    Flatten the modular data structure into the format expected by the template.

    Args:
        modular_data: Dictionary containing modular device data

    Returns:
        Dictionary with flattened structure for template compatibility
    """
    flattened = {}

    # Flatten basic device information
    if 'basic' in modular_data:
        flattened.update(modular_data['basic'])

    # Flatten status information
    if 'status' in modular_data:
        flattened.update(modular_data['status'])

    # Flatten connectivity information
    if 'connectivity' in modular_data:
        connectivity = modular_data['connectivity']
        flattened['is_online'] = connectivity.get('is_online', False)
        flattened['last_seen_online'] = connectivity.get('last_seen_online')
        flattened['connection_status'] = connectivity.get('status', 'Unknown')

    # Flatten hardware information
    if 'battery' in modular_data:
        battery = modular_data['battery']
        flattened['battery_installed'] = battery.get('battery_installed', False)
        flattened['percent_charged'] = battery.get('percent_charged')
        flattened['on_mains_power'] = battery.get('on_mains_power')

    if 'memory' in modular_data:
        memory = modular_data['memory']
        flattened['total_memory'] = memory.get('total_memory')
        flattened['mem_used_percent'] = memory.get('mem_used_percent')

    if 'cpu' in modular_data:
        cpu = modular_data['cpu']
        flattened['cpu_name'] = cpu.get('cpu_name')
        flattened['cpu_cores'] = cpu.get('cpu_cores')

    # Keep modular data structure for components that need it
    flattened['modular_data'] = modular_data

    # Preserve existing keys that might be added elsewhere
    for key in ['printers', 'widgets', 'eventlogs', 'regular_analyses']:
        if key in modular_data:
            flattened[key] = modular_data[key]

    return flattened




@devices_bp.route('/api/device/<uuid:deviceuuid>/loki/schedule', methods=['POST'])
@login_required
def schedule_loki_scan(deviceuuid):
    """Schedule the Loki snippet for a single device.

    This uses the existing snippets scheduling system and looks up the
    Loki snippet for the current tenant by name ("Loki" or "Loki.py").
    Currently it always creates a one-off schedule (recurrence=0).
    """
    try:
        tenantuuid = session.get('tenant_uuid')
        if not tenantuuid:
            log_with_route(logging.ERROR, "No tenant_uuid found in session while scheduling Loki scan")
            return jsonify({"success": False, "error": "Missing tenant context"}), 400

        from app.models import Snippets
        from app.routes.snippets import upsertSnippetSchedule

        data = request.get_json() or {}
        schedule_type = data.get("schedule_type", "now")
        start_time = data.get("start_time") or "0"

        # For now we always schedule a single execution (recurrence=0).
        if schedule_type == "now":
            recstring = "0"
            starttime = "0"
        else:
            # One-off execution at the specified HH:MM (server local time)
            recstring = "0"
            starttime = start_time

        # Look up Loki snippet by name.
        # First try a tenant-specific override, then fall back to the
        # global/default snippet owner tenant (0000...).
        DEFAULT_SNIPPET_TENANT = "00000000-0000-0000-0000-000000000000"

        snippet = (
            # Tenant-specific Loki snippet (if you ever want overrides per tenant)
            Snippets.query
            .filter_by(tenantuuid=tenantuuid, snippetname="Loki")
            .first()
            or Snippets.query.filter_by(tenantuuid=tenantuuid, snippetname="Loki.py").first()
            or
            # Global Loki snippet owned by the default tenant
            Snippets.query
            .filter_by(tenantuuid=DEFAULT_SNIPPET_TENANT, snippetname="Loki")
            .first()
            or Snippets.query.filter_by(tenantuuid=DEFAULT_SNIPPET_TENANT, snippetname="Loki.py").first()
        )

        if not snippet:
            log_with_route(logging.ERROR, f"No Loki snippet found for tenant {tenantuuid}")
            return jsonify({"success": False, "error": "Loki snippet not registered for this tenant"}), 404

        deviceuuid_str = str(deviceuuid)
        upsertSnippetSchedule(deviceuuid_str, str(snippet.snippetuuid), recstring, starttime)

        return jsonify({"success": True})
    except Exception as e:
        log_with_route(logging.ERROR, f"Error scheduling Loki snippet: {str(e)}")
        return jsonify({"success": False, "error": "Failed to schedule Loki scan"}), 500
