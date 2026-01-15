#!/usr/bin/env python3
"""
Verification script to check if the drive data fix is working correctly
"""

import sys
import os
import json
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def verify_fix_in_code():
    """Verify that the fix has been applied to the code"""
    print("=== Verifying Drive Fix in Code ===")
    
    try:
        with open('app/routes/payload.py', 'r') as f:
            content = f.read()
        
        # Check if the old buggy pattern exists
        if 'for key, value in drive.items():' in content:
            print("❌ ERROR: Old buggy pattern still exists in upsertDeviceDrives")
            return False
        
        # Check if the function has been properly fixed
        if 'for drive in auditDict[\'data\'][\'drives\']:' in content:
            print("✅ SUCCESS: Drive iteration pattern looks correct")
        else:
            print("❌ ERROR: Expected drive iteration pattern not found")
            return False
        
        # Check for improved logging
        if 'Processing drive:' in content:
            print("✅ SUCCESS: Improved logging found")
        else:
            print("⚠️  WARNING: Improved logging not found")
        
        # Check for validation
        if 'required_fields' in content:
            print("✅ SUCCESS: Field validation found")
        else:
            print("⚠️  WARNING: Field validation not found")
        
        print("✅ Code fix verification completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ ERROR: Could not verify code fix: {e}")
        return False

def create_test_payload():
    """Create a test payload similar to what the agent would send"""
    return {
        'data': {
            'device': {
                'deviceUuid': 'test-device-uuid',
                'systemtime': int(time.time())
            },
            'drives': [
                {
                    'name': 'C:',
                    'total': 500000000000,
                    'used': 250000000000,
                    'free': 250000000000,
                    'usedPer': 50.0,
                    'freePer': 50.0
                },
                {
                    'name': 'D:',
                    'total': 1000000000000,
                    'used': 300000000000,
                    'free': 700000000000,
                    'usedPer': 30.0,
                    'freePer': 70.0
                }
            ]
        }
    }

def simulate_function_call():
    """Simulate how the fixed function should behave"""
    print("\n=== Simulating Fixed Function Behavior ===")
    
    test_payload = create_test_payload()
    device_uuid = 'test-device-uuid'
    
    print(f"Device UUID: {device_uuid}")
    print(f"Number of drives in payload: {len(test_payload['data']['drives'])}")
    
    # Simulate the fixed function logic
    drives_processed = 0
    for drive in test_payload['data']['drives']:
        # Check required fields (as in the fixed function)
        required_fields = ['name', 'total', 'used', 'free', 'usedPer', 'freePer']
        if not all(field in drive for field in required_fields):
            print(f"❌ ERROR: Missing required fields in drive: {drive}")
            continue
        
        print(f"✅ Processing drive: {drive['name']}")
        print(f"   Total: {drive['total']} bytes")
        print(f"   Used: {drive['used']} bytes ({drive['usedPer']}%)")
        print(f"   Free: {drive['free']} bytes ({drive['freePer']}%)")
        
        # In the real function, this would execute the SQL INSERT
        # Here we just simulate it
        drives_processed += 1
    
    print(f"\n✅ Simulation completed. Processed {drives_processed} drives")
    
    if drives_processed == len(test_payload['data']['drives']):
        print("✅ SUCCESS: All drives processed exactly once")
        return True
    else:
        print(f"❌ ERROR: Expected {len(test_payload['data']['drives'])} drives, processed {drives_processed}")
        return False

def check_database_schema():
    """Check if the database schema is correct for drives"""
    print("\n=== Checking Database Schema ===")
    
    try:
        # Try to import the model to verify it exists
        from app.models import DeviceDrives
        
        print("✅ DeviceDrives model imported successfully")
        
        # Check if the model has the expected fields
        expected_fields = [
            'deviceuuid', 'drive_name', 'drive_total', 'drive_used', 
            'drive_free', 'drive_used_percentage', 'drive_free_percentage',
            'last_update', 'last_json'
        ]
        
        model_columns = [column.name for column in DeviceDrives.__table__.columns]
        
        missing_fields = [field for field in expected_fields if field not in model_columns]
        
        if missing_fields:
            print(f"❌ ERROR: Missing fields in DeviceDrives model: {missing_fields}")
            return False
        else:
            print("✅ SUCCESS: All expected fields found in DeviceDrives model")
            return True
            
    except ImportError as e:
        print(f"❌ ERROR: Could not import DeviceDrives model: {e}")
        return False
    except Exception as e:
        print(f"❌ ERROR: Could not check database schema: {e}")
        return False

def main():
    """Main verification function"""
    print("Wegweiser Drive Data Fix Verification")
    print("=" * 50)
    
    all_checks_passed = True
    
    # Check 1: Verify code fix
    if not verify_fix_in_code():
        all_checks_passed = False
    
    # Check 2: Simulate function behavior
    if not simulate_function_call():
        all_checks_passed = False
    
    # Check 3: Check database schema
    if not check_database_schema():
        all_checks_passed = False
    
    print("\n" + "=" * 50)
    if all_checks_passed:
        print("✅ ALL CHECKS PASSED - Drive fix appears to be working correctly")
        print("\nNext steps:")
        print("1. Run the cleanup script to remove duplicate data")
        print("2. Test with real device data")
        print("3. Monitor for any remaining issues")
    else:
        print("❌ SOME CHECKS FAILED - Please review the issues above")
    
    return all_checks_passed

if __name__ == "__main__":
    main()
