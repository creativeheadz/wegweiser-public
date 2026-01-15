# Filepath: app/utilities/ui_devices_devicedetails.py

from sqlalchemy import text
from app.models import db
from app.utilities.app_logging_helper import log_with_route
from app.utilities.ui_devices_devicetable import get_devices_table_data
import logging
import re
import json
from uuid import UUID

# Mapping for analysis type labels
ANALYSIS_TYPE_LABELS = {
    'eventsFiltered-Application': 'Application Events',
    'eventsFiltered-Security': 'Security Events',
    'eventsFiltered-System': 'System Events',
    'msinfo-SystemSoftwareConfig': 'System Software Configuration',
    'msinfo-StorageInfo': 'Storage Information',
    'msinfo-NetworkConfig': 'Network Configuration',
    'msinfo-InstalledPrograms': 'Installed Programs',
    'msinfo-RecentAppCrashes': 'Recent Application Crashes',
    'msinfo-SystemHardwareConfig': 'System Hardware Configuration',
    'authFiltered': 'Authentication Logs',
    'kernFiltered': 'Kernel Logs',
    'syslogFiltered': 'System Logs',
    'windrivers': 'Windows Drivers Analysis',
    # macOS Analysis Types
    'macos-hardware-eol-analysis': 'macOS Hardware End-of-Life Analysis',
    'macos-os-version-analysis': 'macOS Version Analysis',
    'macos-log-health-analysis': 'macOS Log Health Analysis',
    'macos-errors-filtered': 'macOS Error Logs',
    'macos-security-filtered': 'macOS Security Logs',
    'macos-crashes-filtered': 'macOS Crash Reports',
    'macos-log-summary': 'macOS System Summary'
}

def sanitize_html_content(content):
    """
    This function processes and cleans up the HTML content from the database,
    removing unwanted sections and formatting the content for display.
    """
    # Check if content is None, and return an empty string if true
    if content is None:
        return ""

    # Strip out any unwanted characters or tags that might not render correctly
    content = content.replace("```html", "").replace("```", "").strip()

    # Remove or replace the health score pattern, e.g., (|Healthscore 65|)
    content = re.sub(r'\(\|Healthscore \d+\|\)', '', content)

    # Further processing can be added here if needed

    return content

def get_device_details(deviceuuid, tenantuuid):
    # Validate UUID format first
    try:
        # Try to parse as UUID to validate format
        if deviceuuid and deviceuuid != 'undefined':
            UUID(str(deviceuuid))
        else:
            log_with_route(logging.ERROR, f"Invalid device UUID provided: {deviceuuid}")
            return None
    except (ValueError, AttributeError, TypeError):
        log_with_route(logging.ERROR, f"Malformed device UUID: {deviceuuid}")
        return None

    devices_data, _ = get_devices_table_data(tenantuuid)
    
    if not isinstance(devices_data, list):
        log_with_route(logging.ERROR, f"Expected a list of devices but got {type(devices_data)}")
        return None

    device_data = next(
        (device for device in devices_data if str(device.get('deviceuuid', '')).lower() == deviceuuid.lower()), 
        None
    )

    if not device_data:
        log_with_route(logging.ERROR, f"No device found with uuid {deviceuuid} for tenant {tenantuuid}")
        return None

    latest_analyses_query = text("""
    SELECT DISTINCT ON (dm.metalogos_type)
        dm.metalogos_type, dm.ai_analysis, dm.created_at, dm.score, 
        dm.processing_status
    FROM public.devicemetadata dm
    WHERE dm.deviceuuid = :deviceuuid
    AND dm.metalogos_type != 'msinfo-SystemResources'
    AND dm.processing_status = 'processed'
    ORDER BY dm.metalogos_type, dm.created_at DESC
    """)

    latest_analyses = db.session.execute(latest_analyses_query, {'deviceuuid': deviceuuid}).fetchall()

    if not latest_analyses:
        log_with_route(logging.ERROR, f"No analyses found for device with uuid {deviceuuid}")
        return device_data

    device_data['eventlogs'] = {}

    # Check if device is Windows before loading windrivers analysis
    from app.models import DeviceStatus
    device_status = DeviceStatus.query.filter_by(deviceuuid=deviceuuid).first()
    is_windows = device_status and device_status.agent_platform.startswith('Windows') if device_status else False

    # Only load windrivers analysis for Windows devices
    if is_windows:
        windrivers_query = text("""
            SELECT ai_analysis, score
            FROM public.devicemetadata
            WHERE deviceuuid = :deviceuuid
            AND metalogos_type = 'windrivers'
            AND processing_status = 'processed'
            ORDER BY created_at DESC
            LIMIT 1
        """)

        try:
            windrivers_result = db.session.execute(windrivers_query, {'deviceuuid': deviceuuid}).first()

            if windrivers_result:
                device_data['windrivers'] = {
                    'analysis': sanitize_html_content(windrivers_result.ai_analysis),
                    'score': windrivers_result.score
                }
                log_with_route(logging.DEBUG, f"Windrivers analysis loaded successfully")
            else:
                log_with_route(logging.DEBUG, "No windrivers analysis found")
                device_data['windrivers'] = None

        except Exception as e:
            log_with_route(logging.ERROR, f"Error processing windrivers analysis: {str(e)}")
            device_data['windrivers'] = None
    else:
        log_with_route(logging.DEBUG, f"Skipping windrivers analysis for non-Windows device (platform: {device_status.agent_platform if device_status else 'Unknown'})")
        device_data['windrivers'] = None

    # Process other analyses
    for analysis in latest_analyses:
        if analysis.metalogos_type != 'windrivers':
            device_data['eventlogs'][ANALYSIS_TYPE_LABELS.get(analysis.metalogos_type, analysis.metalogos_type)] = {
                'ai_analysis': sanitize_html_content(analysis.ai_analysis),
                'created_at': analysis.created_at,
                'score': analysis.score,
                'metalogos_type': analysis.metalogos_type
            }

    return device_data