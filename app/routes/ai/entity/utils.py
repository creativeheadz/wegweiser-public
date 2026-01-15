# Filepath: app/routes/ai/entity/utils.py
# Entity-specific utility functions

import logging
import re
from app.utilities.app_logging_helper import log_with_route
from app.models import (
    db,
    Devices,
    DeviceMetadata,
    Groups,
    Organisations,
    DeviceStatus,
    DeviceGpu,
    DeviceBios,
    DeviceMemory,
    DeviceDrives,
    DeviceNetworks,
    DevicePrinters,
)
from app.routes.ai.core import get_entity, get_printers_by_deviceuuid

def get_entity_context(entity_type, entity_uuid, device_info=None):
    """Get comprehensive entity context including all available metadata"""
    entity = get_entity(entity_type, entity_uuid)

    if not entity:
        return "Entity not found"

    context = ""
    if entity_type == 'device':
        # Basic device information
        context = f"Device Name: {entity.devicename}\n"
        context += f"Hardware Info: {entity.hardwareinfo}\n"
        context += f"Health Score: {entity.health_score}\n\n"

        # Use already queried device_info if provided
        if device_info:
            context += _format_device_info(device_info)

        # Get device status information
        status = DeviceStatus.query.filter_by(deviceuuid=entity_uuid).first()
        if status:
            context += "System Information:\n"
            context += f"Platform: {status.agent_platform}\n"
            context += f"System Name: {status.system_name}\n"
            context += f"Logged On User: {status.logged_on_user}\n"
            context += f"CPU Count: {status.cpu_count}\n"
            context += f"Public IP: {status.publicIp}\n"
            context += f"System Model: {status.system_model}\n"
            context += f"System Manufacturer: {status.system_manufacturer}\n\n"

        # Include all metadata analyses
        metadata_items = DeviceMetadata.query.filter_by(deviceuuid=entity_uuid).all()
        if metadata_items:
            # Group metadata by type
            metadata_by_type = {}
            for item in metadata_items:
                if item.metalogos_type not in metadata_by_type or item.created_at > metadata_by_type[item.metalogos_type].created_at:
                    metadata_by_type[item.metalogos_type] = item

            # Add relevant metadata summaries to context
            for meta_type, meta_item in metadata_by_type.items():
                if 'eventsFiltered' in meta_type or 'journalFiltered' in meta_type:
                    context += f"\n{meta_type} Analysis:\n"
                    if meta_item.score:
                        context += f"Health Score: {meta_item.score}\n"

                    # Extract key information from the JSON data if available
                    if meta_item.metalogos and isinstance(meta_item.metalogos, dict):
                        # Extract events summary if available
                        sources = meta_item.metalogos.get('Sources', {})
                        top_events = sources.get('TopEvents', [])
                        if top_events:
                            context += "Top Events:\n"
                            for event in top_events[:5]:  # Limit to 5 events
                                level = event.get('Level', 'INFO')
                                message = event.get('Message', 'No message')
                                context += f"- [{level}] {message}\n"

                    # Include AI analysis summary if available
                    if meta_item.ai_analysis:
                        # Extract first 300 characters as a summary
                        summary = meta_item.ai_analysis.replace("<p>", "").replace("</p>", "\n")
                        summary = re.sub(r'<[^>]+>', '', summary)  # Remove any HTML tags
                        context += f"Analysis Summary: {summary[:300]}\n"
                        if len(summary) > 300:
                            context += "...\n"

        # Include specific device components details
        # Memory
        memory = DeviceMemory.query.filter_by(deviceuuid=entity_uuid).first()
        if memory:
            context += "\nMemory Information:\n"
            total_gb = round(memory.total_memory / (1024**3), 2)
            used_gb = round(memory.used_memory / (1024**3), 2)
            context += f"Total Memory: {total_gb} GB\n"
            context += f"Used Memory: {used_gb} GB ({memory.mem_used_percent}%)\n"

        # Storage
        drives = DeviceDrives.query.filter_by(deviceuuid=entity_uuid).all()
        if drives:
            context += "\nStorage Information:\n"
            for drive in drives:
                context += f"Drive {drive.drive_name}: {round(drive.drive_total / (1024**3), 2)} GB total, {drive.drive_used_percentage}% used\n"

        # Network
        networks = DeviceNetworks.query.filter_by(deviceuuid=entity_uuid).all()
        if networks:
            context += "\nNetwork Information:\n"
            for net in networks:
                context += f"Interface {net.network_name}: {'UP' if net.if_is_up else 'DOWN'}, IP: {net.address_4}\n"

        # GPU
        gpu = DeviceGpu.query.filter_by(deviceuuid=entity_uuid).first()
        if gpu:
            context += f"\nGPU Information:\nVendor: {gpu.gpu_vendor}\nProduct: {gpu.gpu_product}\n"

        # BIOS
        bios = DeviceBios.query.filter_by(deviceuuid=entity_uuid).first()
        if bios:
            context += f"\nBIOS Information:\nVendor: {bios.bios_vendor}\nVersion: {bios.bios_version}\n"

        # Printer information
        printers = get_printers_by_deviceuuid(entity_uuid)
        if printers:
            context += "\nPrinters:\n"
            for printer in printers:
                context += f"- {printer.printer_name} ({printer.printer_status})\n"



    elif entity_type == 'group':
        context = f"Group Name: {entity.groupname}\n"
        context += get_hierarchical_entity_context(entity_type, entity)
    elif entity_type == 'organisation':
        context = f"Organisation Name: {entity.orgname}\n"
        context += get_hierarchical_entity_context(entity_type, entity)
    elif entity_type == 'tenant':
        context = f"Tenant Name: {entity.tenantname}\n"
        context += f"Tenant UUID: {entity.tenantuuid}\n"
        context += get_hierarchical_entity_context(entity_type, entity)

    return context

def _format_device_info(device_info):
    """Format device_info dictionary into a readable string"""
    context = ""

    for info_type, info in device_info.items():
        if 'error' in info:
            continue

        if info_type == 'system':
            context += f"\nSystem Information (Real-time):\n"
            context += f"Platform: {info.get('platform', 'Unknown')}\n"
            context += f"Model: {info.get('manufacturer', 'Unknown')} {info.get('model', 'Unknown')}\n"

            # Include CPU details if available
            cpu = info.get('cpu', {})
            if cpu:
                context += f"CPU: {cpu.get('name', 'Unknown')}, {cpu.get('cores', 0)} cores\n"
                context += f"Current CPU Usage: {cpu.get('usage', 'Unknown')}%\n"

        elif info_type == 'memory':
            context += f"\nMemory Status (Real-time):\n"
            context += f"Total: {info.get('total_gb', 0)} GB\n"
            context += f"Used: {info.get('used_gb', 0)} GB ({info.get('used_percentage', 0)}%)\n"
            context += f"Free: {info.get('free_gb', 0)} GB\n"

        elif info_type == 'storage':
            context += f"\nStorage Status (Real-time):\n"
            for drive in info.get('drives', []):
                context += f"Drive {drive.get('name', 'Unknown')}: {drive.get('total_gb', 0)} GB total, {drive.get('used_percentage', 0)}% used\n"

        elif info_type == 'network':
            context += f"\nNetwork Status (Real-time):\n"
            for iface in info.get('interfaces', []):
                context += f"Interface {iface.get('name', 'Unknown')}: {iface.get('status', 'Unknown')}, Speed: {iface.get('speed', 'Unknown')}\n"
                context += f"  Sent: {iface.get('bytes_sent', 0)} bytes, Received: {iface.get('bytes_received', 0)} bytes\n"

        elif info_type == 'gpu':
            context += f"\nGPU Information (Real-time):\n"
            context += f"Vendor: {info.get('vendor', 'Unknown')}\n"
            context += f"Product: {info.get('product', 'Unknown')}\n"
            context += f"Resolution: {info.get('resolution', 'Unknown')}\n"

        elif info_type == 'health':
            context += f"\nHealth Status (Real-time):\n"
            context += f"Health Score: {info.get('health_score', 'Unknown')}\n"
            context += f"Status: {info.get('status', 'Unknown')}\n"

    return context

def get_device_metadata_context(metadata):
    context = ""
    critical_metadata = []
    for item in metadata:
        if item.metalogos_type in ['eventsFiltered-Application', 'eventsFiltered-System']:
            events = item.metalogos.get('Sources', {}).get('TopEvents', [])
            critical_events = [event for event in events if event.get('Level') in ['ERROR', 'WARNING']]
            if critical_events:
                summary = f"{item.metalogos_type}: {len(critical_events)} critical events detected.\n"
                for event in critical_events[:3]:
                    summary += f"Event: {event.get('Message')}, Level: {event.get('Level')}\n"
                critical_metadata.append(summary)

        elif item.metalogos_type == 'msinfo-StorageInfo':
            if isinstance(item.metalogos, list):
                for drive in item.metalogos:
                    used_space = drive.get('UsedSpacePercent')
                    if isinstance(used_space, (int, float)) and used_space > 80:
                        summary = f"Drive {drive.get('Name')}: {used_space}% used.\n"
                        critical_metadata.append(summary)

    context += "\n".join(critical_metadata)
    return context

def get_hierarchical_entity_context(entity_type, entity):
    context = ""
    if entity_type == 'group':
        devices = Devices.query.filter_by(groupuuid=entity.groupuuid).all()
        context += f"Number of devices: {len(devices)}\n"
        valid_health_scores = [d.health_score for d in devices if d.health_score is not None]
        avg_health_score = sum(valid_health_scores) / len(valid_health_scores) if valid_health_scores else 'N/A'
        context += f"Average device health score: {avg_health_score}\n"
        context += "Devices:\n"
        for device in devices[:5]:  # Limit to 5 devices to avoid overwhelming context
            context += f"- {device.devicename} (Health Score: {device.health_score})\n"
        if len(devices) > 5:
            context += f"  ... and {len(devices) - 5} more devices\n"
    elif entity_type == 'organisation':
        groups = Groups.query.filter_by(orguuid=entity.orguuid).all()
        context += f"Number of groups: {len(groups)}\n"
        valid_health_scores = [g.health_score for g in groups if g.health_score is not None]
        avg_health_score = sum(valid_health_scores) / len(valid_health_scores) if valid_health_scores else 'N/A'
        context += f"Average group health score: {avg_health_score}\n"
        context += "Groups:\n"
        for group in groups[:5]:  # Limit to 5 groups
            context += f"- {group.groupname} (Health Score: {group.health_score})\n"
            devices = Devices.query.filter_by(groupuuid=group.groupuuid).all()
            context += f"  Number of devices: {len(devices)}\n"
        if len(groups) > 5:
            context += f"  ... and {len(groups) - 5} more groups\n"
    elif entity_type == 'tenant':
        organisations = Organisations.query.filter_by(tenantuuid=entity.tenantuuid).all()
        context += f"Number of organisations: {len(organisations)}\n"
        valid_health_scores = [o.health_score for o in organisations if o.health_score is not None]
        avg_health_score = sum(valid_health_scores) / len(valid_health_scores) if valid_health_scores else 'N/A'
        context += f"Average organisation health score: {avg_health_score}\n"
        context += "Organisations:\n"
        for org in organisations[:5]:  # Limit to 5 organizations
            context += f"- {org.orgname} (Health Score: {org.health_score})\n"
            groups = Groups.query.filter_by(orguuid=org.orguuid).all()
            context += f"  Number of groups: {len(groups)}\n"
        if len(organisations) > 5:
            context += f"  ... and {len(organisations) - 5} more organisations\n"

    return context
