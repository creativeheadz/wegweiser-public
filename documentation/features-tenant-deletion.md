# Tenant Deletion with Comprehensive Backup Feature

## Overview

This feature implements comprehensive tenant deletion with automatic data backup, similar to the existing device deletion functionality. When a tenant is deleted, a complete backup of all related data is created before deletion proceeds.

## Features

### 1. Comprehensive Data Backup
- **Tenant Information**: Complete tenant record with all metadata
- **Organizations**: All organizations under the tenant
- **Groups**: All machine groups under the tenant  
- **Devices**: All devices and their complete data sets
- **Related Data**: All associated data including:
  - Device metadata, battery, drives, memory, networks, status, users, partitions
  - CPU, GPU, BIOS, collector, printer, PCI device, USB device, driver info
  - Realtime data and history
  - Messages, conversations, AI memories, contexts
  - Wegcoin transactions, health score history
  - Snippets and snippet history
  - Tag associations
  - User-organization associations

### 2. Backup File Structure
- **Location**: `/var/log/wegweiser/tenant_backups/` (fallback to `/tmp/wegweiser_tenant_backups/`)
- **Naming**: `tenant_{tenantname}_{tenantuuid}_{timestamp}.json`
- **Format**: Structured JSON with sections for:
  - `tenant_info`: Main tenant record
  - `organisations`: Array of organization records
  - `groups`: Array of group records  
  - `devices`: Array of device records
  - `related_data`: Object containing all related table data

### 3. User Interface
- **Individual Deletion**: Delete button on each tenant accordion
- **Bulk Deletion**: Select multiple tenants with checkboxes
- **Select All**: Checkbox to select all tenants at once
- **Confirmation Modal**: Warning dialog explaining the scope of deletion
- **Progress Indication**: Loading states during deletion process

## Implementation Details

### Backend Functions

#### `ensure_tenant_backup_directory()`
Creates and verifies the backup directory with proper permissions.

#### `backup_tenant_data(tenant_uuid)`
- Creates comprehensive backup of all tenant-related data
- Handles UUID serialization and data type conversion
- Returns backup file path for reference

#### `delete_tenant_cascade(tenant_uuid)`
- Performs cascading deletion in proper order
- Deletes device-related data first
- Then organization and group data
- Finally tenant-level data
- Maintains referential integrity

#### `/admin/tenants/delete` Route
- Accepts array of tenant UUIDs
- Creates backup before each deletion
- Returns detailed results for each tenant
- Handles errors gracefully

### Frontend Features

#### Enhanced Template (`admin_tenants.html`)
- Added checkboxes for tenant selection
- Individual delete buttons with confirmation
- Bulk delete functionality
- Select all/none capability
- Bootstrap modal for confirmation

#### JavaScript Functions
- `deleteTenant(uuid, name)`: Single tenant deletion
- `deleteSelectedTenants()`: Bulk deletion
- `performTenantDeletion(uuids)`: AJAX deletion handler
- `toggleSelectAll()`: Select all functionality

## Security Considerations

- **Admin Permission Required**: Only admin users can delete tenants
- **Confirmation Required**: Modal confirmation prevents accidental deletion
- **Backup First**: Deletion only proceeds after successful backup
- **Transaction Safety**: Database rollback on errors
- **Comprehensive Logging**: All operations logged with details

## Error Handling

- **Backup Failures**: Deletion prevented if backup fails
- **Database Errors**: Automatic rollback and error reporting
- **Permission Issues**: Fallback backup directory
- **Network Errors**: Frontend error handling with user feedback

## Usage

1. Navigate to Admin → Tenant Management
2. Select tenant(s) to delete using checkboxes or individual delete buttons
3. Click "Delete Selected" or individual delete button
4. Review warning in confirmation modal
5. Confirm deletion
6. System creates backup and performs deletion
7. Results displayed with backup file paths

## Recovery

Deleted tenant data can be recovered from the JSON backup files. The backup contains all necessary information to reconstruct the tenant and all related data if needed.

## File Locations

- **Backup Function**: `app/routes/admin/admin.py` (lines 979-1198)
- **Delete Function**: `app/routes/admin/admin.py` (lines 1201-1323) 
- **Delete Route**: `app/routes/admin/admin.py` (lines 1326-1388)
- **Template**: `app/templates/administration/admin_tenants.html`
- **Backup Directory**: `/var/log/wegweiser/tenant_backups/`
