#!/usr/bin/env python3
"""
Debug script to check drive data issues in the database
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import db, DeviceDrives, Devices
from sqlalchemy import text

def check_drive_duplicates():
    """Check for duplicate drive entries"""
    app = create_app()
    
    with app.app_context():
        # Check the specific UUIDs mentioned
        problem_uuids = [
            '7c8d1b73-11fa-462e-8111-63e5fc88ac3f',
            'e686ffcd-ed5e-45ea-8998-dd52989b9292', 
            '510a188e-ca5b-48cc-8fe7-173f14fa8928',
            '6e526b54-716b-4103-a58c-8aa505188d37'
        ]
        
        print("=== Checking Drive Data for Problem UUIDs ===")
        
        for uuid in problem_uuids:
            print(f"\n--- Device UUID: {uuid} ---")
            
            # Get device info
            device = db.session.query(Devices).filter(Devices.deviceuuid == uuid).first()
            if device:
                print(f"Device Name: {device.devicename}")
            else:
                print("Device not found!")
                continue
            
            # Get drive data
            drives = db.session.query(DeviceDrives).filter(DeviceDrives.deviceuuid == uuid).all()
            print(f"Number of drive entries: {len(drives)}")
            
            for drive in drives:
                print(f"  Drive: {drive.drive_name}")
                print(f"    Total: {drive.drive_total}")
                print(f"    Used: {drive.drive_used}")
                print(f"    Free: {drive.drive_free}")
                print(f"    Last Update: {drive.last_update}")
                print(f"    Last JSON: {drive.last_json}")
                print()
        
        # Check for devices with '/' drive that shouldn't have it
        print("\n=== Checking for Windows devices with '/' drive ===")
        
        query = text("""
        SELECT d.deviceuuid, d.devicename, dd.drive_name, dd.drive_total, dd.drive_used
        FROM devices d
        JOIN devicedrives dd ON d.deviceuuid = dd.deviceuuid
        WHERE dd.drive_name = '/'
        ORDER BY d.devicename
        """)
        
        result = db.session.execute(query)
        rows = result.fetchall()
        
        for row in rows:
            print(f"Device: {row.devicename} ({row.deviceuuid})")
            print(f"  Drive: {row.drive_name}, Total: {row.drive_total}, Used: {row.drive_used}")
        
        # Check for duplicate drive entries per device
        print("\n=== Checking for duplicate drive entries ===")
        
        query = text("""
        SELECT deviceuuid, drive_name, COUNT(*) as count
        FROM devicedrives
        GROUP BY deviceuuid, drive_name
        HAVING COUNT(*) > 1
        ORDER BY count DESC, deviceuuid, drive_name
        """)
        
        result = db.session.execute(query)
        rows = result.fetchall()
        
        if rows:
            print("Found duplicate drive entries:")
            for row in rows:
                print(f"  Device: {row.deviceuuid}, Drive: {row.drive_name}, Count: {row.count}")
        else:
            print("No duplicate drive entries found")

if __name__ == "__main__":
    check_drive_duplicates()
