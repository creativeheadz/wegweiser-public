# Filepath: app/utilities/device_restore.py
"""
Device Restoration Utility

Restores a deleted device and all its related data from a backup JSON file.
"""

import json
import logging
import os
import glob
import time
import uuid as uuid_module
from uuid import UUID
from app.models import (
    db, Devices, DeviceMetadata, DeviceBattery, DeviceDrives, DeviceMemory,
    DeviceNetworks, DeviceStatus, DeviceUsers, DevicePartitions, DeviceCpu,
    DeviceGpu, DeviceBios, DeviceCollector, DevicePrinters, DevicePciDevices,
    DeviceUsbDevices, DeviceDrivers, DeviceRealtimeData, DeviceRealtimeHistory,
    DeviceConnectivity, Messages, TagsXDevices, Conversations
)
from app.utilities.app_logging_helper import log_with_route


def find_device_backup(device_uuid):
    """
    Find the most recent backup file for a device UUID.
    
    Args:
        device_uuid: UUID of the device to find backup for
        
    Returns:
        str: Path to backup file, or None if not found
    """
    backup_locations = [
        '/var/log/wegweiser/device_backups',
        '/tmp/wegweiser/device_backups'
    ]
    
    for backup_dir in backup_locations:
        if not os.path.exists(backup_dir):
            continue
            
        # Find all backup files for this device UUID
        pattern = os.path.join(backup_dir, f'*{device_uuid}*.json')
        matching_files = glob.glob(pattern)
        
        if matching_files:
            # Return the most recent backup (sorted by modification time)
            most_recent = max(matching_files, key=os.path.getmtime)
            log_with_route(logging.INFO, f"Found backup for device {device_uuid}: {most_recent}")
            return most_recent
    
    log_with_route(logging.WARNING, f"No backup found for device {device_uuid}")
    return None


def restore_device_from_backup(device_uuid, backup_path=None):
    """
    Restore a device and all its related data from a backup JSON file.
    
    Args:
        device_uuid: UUID of the device to restore
        backup_path: Optional path to backup file. If not provided, will search for it.
        
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        # Find backup file if not provided
        if not backup_path:
            backup_path = find_device_backup(device_uuid)
            if not backup_path:
                return False, f"No backup found for device {device_uuid}"
        
        # Check if backup file exists
        if not os.path.exists(backup_path):
            return False, f"Backup file not found: {backup_path}"
        
        # Load backup data
        log_with_route(logging.INFO, f"Loading backup from {backup_path}")
        with open(backup_path, 'r') as f:
            backup_data = json.load(f)
        
        # Check if device already exists
        existing_device = Devices.query.get(device_uuid)
        if existing_device:
            return False, f"Device {device_uuid} already exists in database"
        
        # Restore main device record
        device_info = backup_data.get('device_info', {})
        if not device_info:
            return False, "Backup file missing device_info section"
        
        log_with_route(logging.INFO, f"Restoring device: {device_info.get('devicename')} ({device_uuid})")
        
        # Create device object
        device = Devices(
            deviceuuid=device_info['deviceuuid'],
            devicename=device_info['devicename'],
            hardwareinfo=device_info.get('hardwareinfo'),
            groupuuid=device_info['groupuuid'],
            orguuid=device_info['orguuid'],
            tenantuuid=device_info['tenantuuid'],
            created_at=device_info.get('created_at'),
            health_score=device_info.get('health_score'),
            agent_public_key=device_info.get('agent_public_key'),
            force_analysis=device_info.get('force_analysis', False),
            is_manual_profile=device_info.get('is_manual_profile', False),
            manual_profile_created_at=device_info.get('manual_profile_created_at'),
            is_online=device_info.get('is_online', False),
            last_online_change=device_info.get('last_online_change'),
            last_seen_online=device_info.get('last_seen_online'),
            last_heartbeat=device_info.get('last_heartbeat')
        )
        db.session.add(device)
        
        # Create a NEW conversation for the restored device
        new_conversation_uuid = str(uuid_module.uuid4())
        conversation = Conversations(
            conversationuuid=new_conversation_uuid,
            deviceuuid=device_uuid,
            entityuuid=device_uuid,
            entity_type='device',
            tenantuuid=device_info['tenantuuid']
        )
        db.session.add(conversation)
        # Flush to ensure conversation exists before adding messages
        db.session.flush()

        # Restore related tables
        tables_data = backup_data.get('tables', {})
        restored_counts = {}

        # Map table names to model classes (excluding messages and conversations - we handle those specially)
        table_models = {
            'device_metadata': DeviceMetadata,
            'device_battery': DeviceBattery,
            'device_drives': DeviceDrives,
            'device_memory': DeviceMemory,
            'device_networks': DeviceNetworks,
            'device_status': DeviceStatus,
            'device_users': DeviceUsers,
            'device_partitions': DevicePartitions,
            'device_cpu': DeviceCpu,
            'device_gpu': DeviceGpu,
            'device_bios': DeviceBios,
            'device_collector': DeviceCollector,
            'device_printers': DevicePrinters,
            'device_pci_devices': DevicePciDevices,
            'device_usb_devices': DeviceUsbDevices,
            'device_drivers': DeviceDrivers,
            'device_realtime_data': DeviceRealtimeData,
            'device_realtime_history': DeviceRealtimeHistory,
            'device_connectivity': DeviceConnectivity,
            'tags_x_devices': TagsXDevices
        }

        # Restore each table's data
        for table_name, model_class in table_models.items():
            if table_name not in tables_data:
                continue

            records = tables_data[table_name]
            restored_count = 0

            for record_data in records:
                try:
                    # Create model instance from record data
                    record = model_class(**record_data)
                    db.session.add(record)
                    restored_count += 1
                except Exception as e:
                    log_with_route(logging.WARNING,
                        f"Failed to restore {table_name} record: {str(e)}")
                    continue

            if restored_count > 0:
                restored_counts[table_name] = restored_count
                log_with_route(logging.DEBUG,
                    f"Restored {restored_count} records for {table_name}")

        # Restore messages with NEW conversation UUID
        if 'messages' in tables_data:
            messages_records = tables_data['messages']
            restored_message_count = 0

            for message_data in messages_records:
                try:
                    # Update the conversation UUID to the new one
                    message_data['conversationuuid'] = new_conversation_uuid

                    # Create message instance
                    message = Messages(**message_data)
                    db.session.add(message)
                    restored_message_count += 1
                except Exception as e:
                    log_with_route(logging.WARNING,
                        f"Failed to restore message record: {str(e)}")
                    continue

            if restored_message_count > 0:
                restored_counts['messages'] = restored_message_count
                log_with_route(logging.DEBUG,
                    f"Restored {restored_message_count} messages with new conversation UUID")

        # Add a system message about the restoration
        system_useruuid = '00000000-0000-0000-0000-000000000000'
        restoration_message = Messages(
            messageuuid=str(uuid_module.uuid4()),
            conversationuuid=new_conversation_uuid,
            useruuid=system_useruuid,
            tenantuuid=device_info['tenantuuid'],
            entityuuid=device_uuid,
            entity_type='device',
            title="Device Restored from Backup",
            content=f"Device '{device_info['devicename']}' has been automatically restored from backup after reconnection attempt. Previous conversation history has been preserved.",
            is_read=False,
            created_at=int(time.time()),
            message_type='chat'
        )
        db.session.add(restoration_message)
        
        # Commit all changes
        db.session.commit()
        
        summary = f"Successfully restored device '{device_info['devicename']}' ({device_uuid})"
        if restored_counts:
            summary += f" with {sum(restored_counts.values())} related records"
        
        log_with_route(logging.INFO, summary)
        return True, summary
        
    except Exception as e:
        db.session.rollback()
        error_msg = f"Failed to restore device {device_uuid}: {str(e)}"
        log_with_route(logging.ERROR, error_msg)
        return False, error_msg


def list_available_backups(device_uuid=None):
    """
    List all available device backups.
    
    Args:
        device_uuid: Optional UUID to filter backups for specific device
        
    Returns:
        list: List of dicts with backup information
    """
    backup_locations = [
        '/var/log/wegweiser/device_backups',
        '/tmp/wegweiser/device_backups'
    ]
    
    backups = []
    
    for backup_dir in backup_locations:
        if not os.path.exists(backup_dir):
            continue
        
        if device_uuid:
            pattern = os.path.join(backup_dir, f'*{device_uuid}*.json')
        else:
            pattern = os.path.join(backup_dir, '*.json')
        
        for backup_file in glob.glob(pattern):
            try:
                # Extract info from filename: devicename_uuid_timestamp.json
                filename = os.path.basename(backup_file)
                parts = filename.replace('.json', '').split('_')
                
                # Get file modification time
                mtime = os.path.getmtime(backup_file)
                
                backups.append({
                    'path': backup_file,
                    'filename': filename,
                    'size': os.path.getsize(backup_file),
                    'modified': mtime,
                    'location': backup_dir
                })
            except Exception as e:
                log_with_route(logging.WARNING, f"Error reading backup file {backup_file}: {str(e)}")
                continue
    
    # Sort by modification time (most recent first)
    backups.sort(key=lambda x: x['modified'], reverse=True)
    
    return backups

