# Device Deletion Process in Wegweiser

## Overview

The Wegweiser device deletion system follows a robust process that ensures data integrity while providing comprehensive backups of deleted devices. This document outlines the complete device deletion workflow, including backup mechanisms and dataset handling.

## Deletion Process Flow

### 1. Deletion Request Validation
- User selects device(s) for deletion via the UI
- System validates the device UUIDs exist
- Permission checks are performed to ensure the user has access to delete devices

### 2. Data Backup
Before any deletion occurs, the system creates a complete backup of all device data:
- Device records from the main `devices` table
- All related data from associated tables (see "Backed Up Datasets" below)
- Configuration and metadata information
- Historical analytics and performance data

### 3. Cascading Deletion
Deletion follows a specific order to maintain database integrity:
- Child records in related tables are deleted first
- Main device record is deleted last
- Database constraints are respected to prevent orphaned records

### 4. Backup Storage
Backups are stored as structured JSON files in one of two locations:
- **Primary location**: `/var/log/wegweiser/device_backups` 
- **Fallback location**: `/tmp/wegweiser/device_backups` (used if primary location isn't writable)

The system automatically determines which location to use based on filesystem permissions and availability.

### 5. Notification and Logging
- Success/failure status is returned to the user
- Operation details are logged for audit purposes
- Backup file paths are included in operation logs

## Backed Up Datasets

The backup includes comprehensive data from the following tables:

| Category | Tables | Description |
|----------|--------|-------------|
| Core Device Data | `devices` | Primary device information including name, UUIDs, and configuration |
| Metadata | `devicemetadata` | Various metadata and analysis results |
| Analytics | `analysis_cycles` | Information about analysis operations performed |
| Hardware | `device_battery`, `device_cpu`, `device_gpu`, `device_memory`, `device_bios` | Hardware component information |
| Storage | `device_drives`, `device_partitions` | Storage configuration and status |
| Networking | `device_networks` | Network interfaces and configuration |
| Peripherals | `device_printers`, `device_pci_devices`, `device_usb_devices` | Connected peripheral information |
| System | `device_status`, `device_collector`, `device_drivers` | System status and configuration |
| Users | `device_users` | User accounts on the device |
| Messages | `messages` | System messages related to the device |
| Tags | `tags_x_devices` | Tag associations for the device |
| Realtime Data | `device_realtime_data`, `device_realtime_history` | Performance and monitoring data |

## Backup File Format

Backups are stored as JSON files with the following structure:

```json
{
  "device_info": {
    "deviceuuid": "device-uuid-here",
    "devicename": "example-device",
    "hardwareinfo": "Windows",
    ...
  },
  "tables": {
    "device_metadata": [
      { "record1": "data" },
      { "record2": "data" }
    ],
    "device_networks": [
      { "network1_data": "value" }
    ],
    ...
  }
}
```

## Backup Filename Format

Backup files follow a consistent naming pattern for easy identification:
```
{device_name}_{device_uuid}_{timestamp}.json
```

For example:
```
WindowsLaptop_ff20ad09-979f-407b-8e6e-b8d61f795826_20230410_192831.json
```

## Error Handling

The deletion process includes robust error handling:
- If backup creation fails, the deletion is aborted
- If any table deletion fails, the transaction is rolled back
- All errors are logged with detailed information
- Users are informed of any issues via the UI

## Recovery Process

In case a device needs to be restored from backup:
1. Locate the appropriate backup file in the backup directory
2. Use the backup/restore utility to recreate the device and its associated data
3. Verify the restoration was successful by checking device visibility in the UI

## Best Practices

1. **Regular Backups**: Perform system-wide backups in addition to the automatic per-device backups
2. **Backup Rotation**: Set up rotation policies for backup files to manage storage
3. **Verification**: Periodically verify backup integrity with test restorations
4. **Documentation**: Keep records of deleted devices and their backup locations

## Current Dataset Tables

As of the latest update, the following tables are included in device backups and cascading deletion:

- `DeviceMetadata`
- `AnalysisCycle`
- `DeviceBattery`
- `DeviceDrives`
- `DeviceMemory`
- `DeviceNetworks`
- `DeviceStatus`
- `DeviceUsers`
- `DevicePartitions`
- `DeviceCpu`
- `DeviceGpu`
- `DeviceBios`
- `DeviceCollector`
- `DevicePrinters`
- `DevicePciDevices`
- `DeviceUsbDevices`
- `DeviceDrivers`
- `DeviceRealtimeData`
- `DeviceRealtimeHistory`
- `Messages` (where entity_type='device')
- `TagsXDevices`

This comprehensive backup and deletion approach ensures that data integrity is maintained while providing a complete historical record of removed devices.
