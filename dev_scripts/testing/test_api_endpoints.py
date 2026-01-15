#!/usr/bin/env python3
"""
Test script for the logging configuration API endpoints.
"""

import requests
import json
import sys

def test_api_endpoints():
    """Test the logging configuration API endpoints."""
    base_url = "http://localhost"
    
    print("=" * 60)
    print("Testing Logging Configuration API Endpoints")
    print("=" * 60)
    
    # Note: These tests would require authentication in a real scenario
    # For now, we'll just test if the endpoints are accessible
    
    try:
        # Test GET /api/logging-config
        print("1. Testing GET /api/logging-config...")
        response = requests.get(f"{base_url}/api/logging-config", timeout=10)
        print(f"   Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ Response: {json.dumps(data, indent=2)}")
        elif response.status_code == 403:
            print("   ⚠ Access forbidden (authentication required)")
        else:
            print(f"   ✗ Unexpected status code: {response.status_code}")
            print(f"   Response: {response.text}")
        
        # Test POST /api/logging-config
        print("\n2. Testing POST /api/logging-config...")
        test_data = {
            "levels": {
                "INFO": True,
                "DEBUG": False,
                "ERROR": True,
                "WARNING": True
            }
        }
        response = requests.post(
            f"{base_url}/api/logging-config", 
            json=test_data,
            timeout=10
        )
        print(f"   Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ Response: {json.dumps(data, indent=2)}")
        elif response.status_code == 403:
            print("   ⚠ Access forbidden (authentication required)")
        else:
            print(f"   ✗ Unexpected status code: {response.status_code}")
            print(f"   Response: {response.text}")
        
        # Test POST /api/logging-config/reload
        print("\n3. Testing POST /api/logging-config/reload...")
        response = requests.post(f"{base_url}/api/logging-config/reload", timeout=10)
        print(f"   Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ Response: {json.dumps(data, indent=2)}")
        elif response.status_code == 403:
            print("   ⚠ Access forbidden (authentication required)")
        else:
            print(f"   ✗ Unexpected status code: {response.status_code}")
            print(f"   Response: {response.text}")
        
        # Test GET /admin/logging-config (HTML page)
        print("\n4. Testing GET /admin/logging-config...")
        response = requests.get(f"{base_url}/admin/logging-config", timeout=10)
        print(f"   Status Code: {response.status_code}")
        if response.status_code == 200:
            print("   ✓ HTML page accessible")
            if "Logging Configuration" in response.text:
                print("   ✓ Page contains expected content")
            else:
                print("   ⚠ Page content may not be correct")
        elif response.status_code == 403:
            print("   ⚠ Access forbidden (authentication required)")
        elif response.status_code == 302:
            print("   ⚠ Redirected (likely to login page)")
        else:
            print(f"   ✗ Unexpected status code: {response.status_code}")
        
        print("\n" + "=" * 60)
        print("API endpoint tests completed!")
        print("Note: 403 errors are expected if authentication is required.")
        print("=" * 60)
        
    except requests.exceptions.RequestException as e:
        print(f"\n✗ Network error: {str(e)}")
        return False
    except Exception as e:
        print(f"\n✗ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = test_api_endpoints()
    if success:
        print("\n🎉 API endpoint tests completed!")
    else:
        print("\n❌ API endpoint tests failed!")
        sys.exit(1)
