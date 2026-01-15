#!/usr/bin/env python3
"""
Test script to verify the drive data fix works correctly
"""

import sys
import os
import json
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Mock test data
def create_test_audit_data():
    """Create test audit data similar to what the agent would send"""
    return {
        'data': {
            'device': {
                'systemtime': int(time.time())
            },
            'drives': [
                {
                    'name': 'C:',
                    'total': 500000000000,  # 500GB
                    'used': 250000000000,   # 250GB
                    'free': 250000000000,   # 250GB
                    'usedPer': 50.0,
                    'freePer': 50.0
                },
                {
                    'name': 'D:',
                    'total': 1000000000000,  # 1TB
                    'used': 300000000000,    # 300GB
                    'free': 700000000000,    # 700GB
                    'usedPer': 30.0,
                    'freePer': 70.0
                }
            ]
        }
    }

def test_upsert_function():
    """Test the upsertDeviceDrives function directly"""
    try:
        from app import create_app
        from app.models import db, DeviceDrives
        from app.routes.payload import upsertDeviceDrives
        import uuid
        
        app = create_app()
        
        with app.app_context():
            # Create a test device UUID
            test_device_uuid = str(uuid.uuid4())
            
            print(f"Testing with device UUID: {test_device_uuid}")
            
            # Create test audit data
            audit_data = create_test_audit_data()
            
            print("Test audit data:")
            print(json.dumps(audit_data, indent=2))
            
            # Clear any existing data for this test device
            db.session.query(DeviceDrives).filter(
                DeviceDrives.deviceuuid == test_device_uuid
            ).delete()
            db.session.commit()
            
            print("\nCalling upsertDeviceDrives function...")
            
            # Call the function
            upsertDeviceDrives(test_device_uuid, audit_data)
            
            # Check the results
            drives = db.session.query(DeviceDrives).filter(
                DeviceDrives.deviceuuid == test_device_uuid
            ).all()
            
            print(f"\nResults: Found {len(drives)} drive entries")
            
            for drive in drives:
                print(f"Drive: {drive.drive_name}")
                print(f"  Total: {drive.drive_total}")
                print(f"  Used: {drive.drive_used}")
                print(f"  Free: {drive.drive_free}")
                print(f"  Used %: {drive.drive_used_percentage}")
                print(f"  Free %: {drive.drive_free_percentage}")
                print()
            
            # Verify we have exactly 2 drives (C: and D:)
            if len(drives) == 2:
                print("✅ SUCCESS: Correct number of drives inserted")
                
                # Check drive names
                drive_names = [drive.drive_name for drive in drives]
                if 'C:' in drive_names and 'D:' in drive_names:
                    print("✅ SUCCESS: Correct drive names found")
                else:
                    print(f"❌ ERROR: Expected C: and D:, found {drive_names}")
                
                # Test updating existing data
                print("\nTesting update functionality...")
                
                # Modify the audit data
                audit_data['data']['drives'][0]['used'] = 300000000000  # Change C: used space
                audit_data['data']['drives'][0]['usedPer'] = 60.0
                audit_data['data']['drives'][0]['freePer'] = 40.0
                
                # Call function again
                upsertDeviceDrives(test_device_uuid, audit_data)
                
                # Check results
                drives_after_update = db.session.query(DeviceDrives).filter(
                    DeviceDrives.deviceuuid == test_device_uuid
                ).all()
                
                if len(drives_after_update) == 2:
                    print("✅ SUCCESS: No duplicate entries created on update")
                    
                    # Check if C: drive was updated
                    c_drive = next((d for d in drives_after_update if d.drive_name == 'C:'), None)
                    if c_drive and c_drive.drive_used == 300000000000:
                        print("✅ SUCCESS: Drive data updated correctly")
                    else:
                        print("❌ ERROR: Drive data not updated correctly")
                else:
                    print(f"❌ ERROR: Expected 2 drives after update, found {len(drives_after_update)}")
                
            else:
                print(f"❌ ERROR: Expected 2 drives, found {len(drives)}")
            
            # Clean up test data
            db.session.query(DeviceDrives).filter(
                DeviceDrives.deviceuuid == test_device_uuid
            ).delete()
            db.session.commit()
            
            print("\nTest completed and cleaned up")
            
    except ImportError as e:
        print(f"❌ ERROR: Could not import required modules: {e}")
        print("Make sure Flask and other dependencies are installed")
    except Exception as e:
        print(f"❌ ERROR: Test failed with exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_upsert_function()
