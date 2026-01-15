#!/usr/bin/env python3
# Filepath: tools/restore_device_test.py
"""
Test script to restore a device from backup.

Usage:
    python tools/restore_device_test.py <device_uuid>
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.utilities.device_restore import restore_device_from_backup, find_device_backup

def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/restore_device_test.py <device_uuid>")
        sys.exit(1)
    
    device_uuid = sys.argv[1]
    
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        print(f"\n=== Device Restoration Test ===")
        print(f"Device UUID: {device_uuid}\n")
        
        # First, check if backup exists
        print("Step 1: Searching for backup file...")
        backup_path = find_device_backup(device_uuid)
        
        if not backup_path:
            print(f"❌ No backup found for device {device_uuid}")
            sys.exit(1)
        
        print(f"✅ Found backup: {backup_path}")
        
        # Show backup file size
        file_size = os.path.getsize(backup_path)
        print(f"   File size: {file_size:,} bytes ({file_size / 1024:.2f} KB)")
        
        # Ask for confirmation
        print(f"\nStep 2: Ready to restore device from backup")
        response = input("Do you want to proceed with restoration? (yes/no): ")
        
        if response.lower() not in ['yes', 'y']:
            print("❌ Restoration cancelled by user")
            sys.exit(0)
        
        # Perform restoration
        print(f"\nStep 3: Restoring device...")
        success, message = restore_device_from_backup(device_uuid, backup_path)
        
        if success:
            print(f"✅ {message}")
            print(f"\nDevice '{device_uuid}' has been successfully restored!")
            print(f"The device should now be able to check in normally.")
        else:
            print(f"❌ Restoration failed: {message}")
            sys.exit(1)

if __name__ == '__main__':
    main()

