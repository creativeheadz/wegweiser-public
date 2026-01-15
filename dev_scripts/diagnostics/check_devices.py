#!/usr/bin/env python3
"""
Quick script to check device names for the UUIDs we're seeing in NATS logs
"""

import sys
sys.path.insert(0, '/opt/wegweiser')

from app import create_app
from app.models import Devices

def check_devices():
    app = create_app()
    
    with app.app_context():
        # UUIDs we're seeing in NATS logs
        uuids_to_check = [
            '59e617d6-6caf-4afe-b5bb-eab81c06e6b4',
            'b8feb0e8-22a9-4c17-94da-a73ee30b5aea', 
            '84c1a49a-5064-4886-b588-9a9545b12fb3',
            '4cd41e01-f1da-4a91-850e-fb797cab8596'  # Your Mac device
        ]
        
        print("Device UUID -> Device Name mapping:")
        print("=" * 60)
        
        for uuid in uuids_to_check:
            device = Devices.query.filter_by(deviceuuid=uuid).first()
            if device:
                print(f"{uuid} -> {device.devicename} ({device.hardwareinfo})")
            else:
                print(f"{uuid} -> NOT FOUND")
        
        print("\nAll devices in database:")
        print("=" * 60)
        all_devices = Devices.query.all()
        for device in all_devices:
            print(f"{device.deviceuuid} -> {device.devicename} ({device.hardwareinfo})")

if __name__ == "__main__":
    check_devices()
