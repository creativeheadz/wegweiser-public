# Filepath: app/utilities/ui_devices_devicetable.py
from sqlalchemy import text
from flask import current_app
from app import db
from app.utilities.app_logging_helper import log_with_route
from app.utilities.ui_time_converter import unix_to_utc
import logging

def get_devices_table_data(tenantuuid):
    query = text("""
        WITH latest_devices AS (
            SELECT DISTINCT ON (a.deviceuuid)
                a.deviceuuid,
                a.devicename,
                a.hardwareinfo,
                d.groupname,
                d.groupuuid,
                pg.orgname,
                pg.orguuid,
                a.created_at,
                c.agent_platform,
                c.last_update,
                dg.gpu_vendor,
                dg.gpu_product,
                c.logged_on_user,
                c.publicIp,
                db.battery_installed,
                db.percent_charged,
                db.on_mains_power,
                dbios.bios_vendor,
                dbios.bios_version,
                dcpu.cpu_name,
                dm.total_memory,
                dm.mem_used_percent,
                c.cpu_count,
                c.boot_time,
                a.health_score,
                dc.is_online,
                COALESCE(c.last_update, dc.last_seen_online) as last_seen_online,
                CASE
                    WHEN dc.is_online THEN 'Online'
                    ELSE 'Offline'
                END as status
            FROM
                public.devices a
            LEFT JOIN
                public.groups d ON a.groupuuid = d.groupuuid
            LEFT JOIN
                public.devicestatus c ON a.deviceuuid = c.deviceuuid
            LEFT JOIN
                public.devicegpu dg ON a.deviceuuid = dg.deviceuuid
            LEFT JOIN
                public.organisations pg ON a.orguuid = pg.orguuid
            LEFT JOIN
                public.devicebattery db ON a.deviceuuid = db.deviceuuid
            LEFT JOIN
                public.devicebios dbios ON a.deviceuuid = dbios.deviceuuid
            LEFT JOIN
                public.devicecpu dcpu ON a.deviceuuid = dcpu.deviceuuid
            LEFT JOIN
                public.devicememory dm ON a.deviceuuid = dm.deviceuuid
            LEFT JOIN
                public.deviceconnectivity dc ON a.deviceuuid = dc.deviceuuid
            WHERE
                a.tenantuuid = :tenantuuid
            ORDER BY
                a.deviceuuid, a.created_at DESC
        )
        SELECT
            ld.*,
            STRING_AGG(DISTINCT dd.drive_name || ': ' || dd.drive_used_percentage::text || '%', ', ') as drives,
            STRING_AGG(DISTINCT dn.network_name || ': ' || dn.address_4, ', ') as networks,
            tags.tags,
            ld.last_update  -- Referencing last_update from latest_devices (ld)
        FROM
            latest_devices ld
        LEFT JOIN
            public.devicedrives dd ON ld.deviceuuid = dd.deviceuuid
        LEFT JOIN
            public.devicenetworks dn ON ld.deviceuuid = dn.deviceuuid
        LEFT JOIN LATERAL (
            SELECT STRING_AGG(t.tagvalue, ', ') as tags
            FROM tags t
            JOIN tagsxdevices td ON t.taguuid = td.taguuid
            WHERE td.deviceuuid = ld.deviceuuid
        ) tags ON true
        GROUP BY
            ld.deviceuuid, ld.devicename, ld.hardwareinfo, ld.groupname, ld.groupuuid, ld.orgname, ld.orguuid, ld.created_at, ld.agent_platform,
            ld.gpu_vendor, ld.gpu_product, ld.logged_on_user, ld.publicIp, ld.battery_installed,
            ld.percent_charged, ld.on_mains_power, ld.bios_vendor, ld.bios_version, ld.cpu_name,
            ld.total_memory, ld.mem_used_percent, ld.cpu_count, ld.boot_time, ld.health_score,
            ld.is_online, ld.last_seen_online, ld.status, tags.tags, ld.last_update;
        """)

    try:
        result = db.session.execute(query, {'tenantuuid': tenantuuid})
        column_names = result.keys()
        devices = [dict(zip(column_names, row)) for row in result.fetchall()]

        # Log each device to inspect its structure
        for device in devices:
            logging.debug(f"Device: {device}")

        # Process devices

        # Process devices
        for device in devices:
            device['tags'] = device['tags'].split(', ') if device['tags'] else []
            device['created_at'] = unix_to_utc(device['created_at'])

            # Check if last_update is not None before converting
            if device['last_update'] is not None:
                device['last_update'] = unix_to_utc(device['last_update'])
            else:
                device['last_update'] = 'Unknown'  # or handle it accordingly

            # Format last_seen_online timestamp
            if device['last_seen_online'] is not None:
                try:
                    device['last_seen'] = unix_to_utc(device['last_seen_online'])
                except (ValueError, TypeError):
                    device['last_seen'] = 'Never'
            else:
                device['last_seen'] = 'Never'

        # Automatically generate column information
        columns = []
        for col_name in column_names:
            label = ' '.join(word.capitalize() for word in col_name.split('_'))
            columns.append({
                'name': col_name,
                'label': label,
                'visible': True  # Set all columns visible by default
            })

        # Customize specific columns
        column_customizations = {
            'deviceuuid': {'visible': True},  # Hide deviceuuid by default
            'devicename': {'label': 'Device Name', 'order': 0},
            'health_score': {'label': 'Health Score', 'order': 1},
            'agent_platform': {'label': 'Platform', 'order': 2},
            'created_at': {'label': 'Created At', 'order': -1},  # Place at the end
        #    'last_update': {'label': 'Last Update', 'order': -2},  # Place at the end
        }

        # Apply customizations and sort columns
        for col in columns:
            if col['name'] in column_customizations:
                col.update(column_customizations[col['name']])

        columns.sort(key=lambda x: x.get('order', 99))  # Sort columns, unordered columns go to the end

        log_with_route(logging.DEBUG, f"Fetched {len(devices)} devices for tenant {tenantuuid}")
        return devices, columns
    except Exception as e:
        log_with_route(logging.ERROR, f"Error fetching devices for tenant {tenantuuid}: {str(e)}", exc_info=True)
        return None, None
