#!/usr/bin/env python3
"""
Test session fallback mechanism
Simulates Redis failure to test filesystem fallback
"""

import requests
import redis
import time
import subprocess
import sys

def test_redis_sessions():
    """Test that Redis sessions work normally"""
    print("🔍 Testing Redis sessions...")
    
    try:
        # Test Redis connectivity
        redis_client = redis.Redis(host='localhost', port=6379, db=1)
        redis_client.ping()
        print("  ✅ Redis is accessible")
        
        # Test application with Redis
        response = requests.get('https://app.wegweiser.tech/login', timeout=10)
        if response.status_code == 200:
            print("  ✅ Application responds with Redis sessions")
            
            # Check if session cookie is set
            session_cookie = None
            for cookie in response.cookies:
                if 'session' in cookie.name.lower():
                    session_cookie = cookie
                    break
            
            if session_cookie:
                print(f"  ✅ Session cookie set: {session_cookie.name}")
                return True
            else:
                print("  ❌ No session cookie found")
                return False
        else:
            print(f"  ❌ Application error: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"  ❌ Redis session test failed: {str(e)}")
        return False

def test_filesystem_fallback():
    """Test filesystem fallback when Redis is unavailable"""
    print("\n🔍 Testing filesystem fallback...")
    
    try:
        # Stop Redis temporarily
        print("  🛑 Stopping Redis temporarily...")
        subprocess.run(['sudo', 'systemctl', 'stop', 'redis'], check=True, capture_output=True)
        time.sleep(2)
        
        # Restart application to trigger fallback
        print("  🔄 Restarting application...")
        subprocess.run(['sudo', 'systemctl', 'restart', 'wegweiser'], check=True, capture_output=True)
        time.sleep(5)
        
        # Test application with filesystem sessions
        print("  🧪 Testing application with filesystem fallback...")
        response = requests.get('https://app.wegweiser.tech/login', timeout=15)
        
        if response.status_code == 200:
            print("  ✅ Application responds with filesystem sessions")
            
            # Check if session cookie is set
            session_cookie = None
            for cookie in response.cookies:
                if 'session' in cookie.name.lower():
                    session_cookie = cookie
                    break
            
            if session_cookie:
                print(f"  ✅ Session cookie set: {session_cookie.name}")
                
                # Test CSRF token (this was the issue)
                if 'csrf' in response.text.lower() or 'token' in response.text.lower():
                    print("  ✅ CSRF token appears to be present")
                    return True
                else:
                    print("  ⚠️  CSRF token may be missing")
                    return False
            else:
                print("  ❌ No session cookie found")
                return False
        else:
            print(f"  ❌ Application error: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"  ❌ Filesystem fallback test failed: {str(e)}")
        return False
    
    finally:
        # Always restart Redis
        print("  🔄 Restarting Redis...")
        try:
            subprocess.run(['sudo', 'systemctl', 'start', 'redis'], check=True, capture_output=True)
            time.sleep(2)
            print("  ✅ Redis restarted")
        except Exception as e:
            print(f"  ❌ Failed to restart Redis: {str(e)}")

def restore_redis_sessions():
    """Restore Redis sessions after testing"""
    print("\n🔄 Restoring Redis sessions...")
    
    try:
        # Restart application to use Redis again
        subprocess.run(['sudo', 'systemctl', 'restart', 'wegweiser'], check=True, capture_output=True)
        time.sleep(5)
        
        # Test that Redis sessions are working again
        response = requests.get('https://app.wegweiser.tech/login', timeout=10)
        if response.status_code == 200:
            print("  ✅ Redis sessions restored")
            return True
        else:
            print(f"  ❌ Failed to restore Redis sessions: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"  ❌ Failed to restore Redis sessions: {str(e)}")
        return False

def main():
    """Run complete session fallback test"""
    print("🧪 Session Fallback Test Suite")
    print("=" * 50)
    
    # Test 1: Redis sessions work normally
    redis_ok = test_redis_sessions()
    
    # Test 2: Filesystem fallback works when Redis fails
    fallback_ok = test_filesystem_fallback()
    
    # Test 3: Redis sessions can be restored
    restore_ok = restore_redis_sessions()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print(f"  Redis Sessions: {'✅ PASS' if redis_ok else '❌ FAIL'}")
    print(f"  Filesystem Fallback: {'✅ PASS' if fallback_ok else '❌ FAIL'}")
    print(f"  Redis Restoration: {'✅ PASS' if restore_ok else '❌ FAIL'}")
    
    overall_success = redis_ok and fallback_ok and restore_ok
    print(f"\n🎯 Overall: {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")
    
    if not overall_success:
        print("\n⚠️  Session fallback mechanism needs attention!")
    
    return overall_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
