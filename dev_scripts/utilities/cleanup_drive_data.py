#!/usr/bin/env python3
"""
Script to clean up corrupted drive data in the database
This script will:
1. Identify duplicate drive entries
2. Remove duplicates, keeping the most recent entry
3. Report on the cleanup process
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import db, DeviceDrives, Devices
from sqlalchemy import text, func
import logging

def setup_logging():
    """Setup logging for the cleanup script"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('drive_cleanup.log'),
            logging.StreamHandler()
        ]
    )

def find_duplicate_drives():
    """Find devices with duplicate drive entries"""
    query = text("""
    SELECT deviceuuid, drive_name, COUNT(*) as count
    FROM devicedrives
    GROUP BY deviceuuid, drive_name
    HAVING COUNT(*) > 1
    ORDER BY count DESC, deviceuuid, drive_name
    """)
    
    result = db.session.execute(query)
    return result.fetchall()

def get_device_info(deviceuuid):
    """Get device information"""
    device = db.session.query(Devices).filter(Devices.deviceuuid == deviceuuid).first()
    if device:
        return device.devicename
    return "Unknown Device"

def cleanup_duplicate_drives():
    """Clean up duplicate drive entries, keeping the most recent one"""
    app = create_app()
    
    with app.app_context():
        setup_logging()
        logging.info("Starting drive data cleanup process")
        
        # Find all duplicate entries
        duplicates = find_duplicate_drives()
        
        if not duplicates:
            logging.info("No duplicate drive entries found")
            return
        
        logging.info(f"Found {len(duplicates)} sets of duplicate drive entries")
        
        total_removed = 0
        
        for duplicate in duplicates:
            deviceuuid = duplicate.deviceuuid
            drive_name = duplicate.drive_name
            count = duplicate.count
            
            device_name = get_device_info(deviceuuid)
            logging.info(f"Processing device: {device_name} ({deviceuuid})")
            logging.info(f"  Drive: {drive_name} has {count} duplicate entries")
            
            # Get all entries for this device/drive combination, ordered by last_update DESC
            entries = db.session.query(DeviceDrives)\
                .filter(DeviceDrives.deviceuuid == deviceuuid)\
                .filter(DeviceDrives.drive_name == drive_name)\
                .order_by(DeviceDrives.last_update.desc())\
                .all()
            
            if len(entries) <= 1:
                logging.warning(f"  Expected {count} entries but found {len(entries)}")
                continue
            
            # Keep the first (most recent) entry, delete the rest
            entries_to_keep = entries[0]
            entries_to_delete = entries[1:]
            
            logging.info(f"  Keeping entry with last_update: {entries_to_keep.last_update}")
            logging.info(f"  Deleting {len(entries_to_delete)} duplicate entries")
            
            try:
                # Delete the duplicate entries
                for entry in entries_to_delete:
                    db.session.delete(entry)
                
                db.session.commit()
                total_removed += len(entries_to_delete)
                logging.info(f"  Successfully removed {len(entries_to_delete)} duplicates")
                
            except Exception as e:
                logging.error(f"  Error removing duplicates: {str(e)}")
                db.session.rollback()
                continue
        
        logging.info(f"Cleanup completed. Total duplicate entries removed: {total_removed}")
        
        # Verify cleanup
        remaining_duplicates = find_duplicate_drives()
        if remaining_duplicates:
            logging.warning(f"Warning: {len(remaining_duplicates)} duplicate sets still remain")
        else:
            logging.info("All duplicates successfully removed")

def analyze_drive_data():
    """Analyze drive data for inconsistencies"""
    app = create_app()
    
    with app.app_context():
        setup_logging()
        logging.info("Analyzing drive data for inconsistencies")
        
        # Check for Windows devices with '/' drives
        query = text("""
        SELECT d.deviceuuid, d.devicename, dd.drive_name, dd.drive_total, dd.drive_used
        FROM devices d
        JOIN devicedrives dd ON d.deviceuuid = dd.deviceuuid
        WHERE dd.drive_name = '/'
        ORDER BY d.devicename
        """)
        
        result = db.session.execute(query)
        linux_drives = result.fetchall()
        
        if linux_drives:
            logging.warning(f"Found {len(linux_drives)} devices with '/' drives:")
            for row in linux_drives:
                logging.warning(f"  Device: {row.devicename} ({row.deviceuuid})")
        else:
            logging.info("No devices found with '/' drives")
        
        # Check for devices with unusual drive counts
        query = text("""
        SELECT d.deviceuuid, d.devicename, COUNT(dd.drive_name) as drive_count
        FROM devices d
        JOIN devicedrives dd ON d.deviceuuid = dd.deviceuuid
        GROUP BY d.deviceuuid, d.devicename
        HAVING COUNT(dd.drive_name) > 10
        ORDER BY drive_count DESC
        """)
        
        result = db.session.execute(query)
        high_drive_counts = result.fetchall()
        
        if high_drive_counts:
            logging.warning(f"Found {len(high_drive_counts)} devices with unusually high drive counts:")
            for row in high_drive_counts:
                logging.warning(f"  Device: {row.devicename} ({row.deviceuuid}) - {row.drive_count} drives")
        else:
            logging.info("No devices found with unusually high drive counts")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "analyze":
        analyze_drive_data()
    else:
        cleanup_duplicate_drives()
