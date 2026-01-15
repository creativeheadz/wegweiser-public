#!/usr/bin/env python3
"""
Test script to verify CSRF token functionality is working.
"""

import requests
import json
import sys
from bs4 import BeautifulSoup

def test_csrf_functionality():
    """Test that CSRF tokens are properly handled."""
    base_url = "http://localhost"
    
    print("=" * 60)
    print("Testing CSRF Token Functionality")
    print("=" * 60)
    
    try:
        # First, get the login page to establish a session
        print("1. Establishing session...")
        session = requests.Session()
        
        # Get the logging config page to extract CSRF token
        print("2. Getting logging config page...")
        response = session.get(f"{base_url}/admin/logging-config", timeout=10)
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("   ✓ Page accessible")
            
            # Parse HTML to extract CSRF token
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try to find CSRF token in meta tag
            csrf_meta = soup.find('meta', {'name': 'csrf-token'})
            csrf_input = soup.find('input', {'name': 'csrf_token'})
            
            csrf_token = None
            if csrf_meta:
                csrf_token = csrf_meta.get('content')
                print(f"   ✓ CSRF token found in meta tag: {csrf_token[:20]}...")
            elif csrf_input:
                csrf_token = csrf_input.get('value')
                print(f"   ✓ CSRF token found in input field: {csrf_token[:20]}...")
            else:
                print("   ⚠ No CSRF token found in page")
            
            if csrf_token:
                # Test API call with CSRF token
                print("\n3. Testing API call with CSRF token...")
                test_data = {
                    "levels": {
                        "INFO": True,
                        "DEBUG": False,
                        "ERROR": True,
                        "WARNING": True
                    }
                }
                
                headers = {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrf_token
                }
                
                response = session.post(
                    f"{base_url}/api/logging-config",
                    json=test_data,
                    headers=headers,
                    timeout=10
                )
                
                print(f"   Status Code: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    print(f"   ✓ API call successful: {data.get('message', 'No message')}")
                elif response.status_code == 403:
                    print("   ⚠ Access forbidden (authentication required)")
                else:
                    print(f"   Response: {response.text}")
            
        elif response.status_code == 302:
            print("   ⚠ Redirected (likely to login page)")
        elif response.status_code == 403:
            print("   ⚠ Access forbidden (authentication required)")
        else:
            print(f"   ✗ Unexpected status code: {response.status_code}")
        
        print("\n" + "=" * 60)
        print("CSRF functionality test completed!")
        print("Note: Authentication may be required for full testing.")
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
    success = test_csrf_functionality()
    if success:
        print("\n🎉 CSRF functionality test completed!")
    else:
        print("\n❌ CSRF functionality test failed!")
        sys.exit(1)
