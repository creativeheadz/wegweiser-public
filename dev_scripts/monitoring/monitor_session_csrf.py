#!/usr/bin/env python3
"""
Monitor for session and CSRF token issues
Detects the specific problem that caused login failures
"""

import requests
import redis
import re
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/opt/wegweiser/wlog/session_csrf_monitor.log'),
        logging.StreamHandler()
    ]
)

def check_csrf_token_availability():
    """Check if CSRF tokens are available in the login page"""
    try:
        response = requests.get('https://app.wegweiser.tech/login', timeout=10)
        
        if response.status_code != 200:
            return False, f"HTTP {response.status_code}"
        
        # Look for CSRF token in the response
        csrf_patterns = [
            r'csrf_token',
            r'name="csrf_token"',
            r'<input[^>]*csrf[^>]*>',
            r'_token',
            r'authenticity_token'
        ]
        
        csrf_found = False
        for pattern in csrf_patterns:
            if re.search(pattern, response.text, re.IGNORECASE):
                csrf_found = True
                break
        
        # Check for session cookie
        session_cookie = None
        for cookie in response.cookies:
            if 'session' in cookie.name.lower():
                session_cookie = cookie
                break
        
        if not session_cookie:
            return False, "No session cookie set"
        
        if not csrf_found:
            return False, "CSRF token not found in page"
        
        return True, "CSRF token and session cookie present"
        
    except Exception as e:
        return False, f"Request failed: {str(e)}"

def check_session_backend():
    """Determine which session backend is being used"""
    try:
        # Check Redis
        redis_client = redis.Redis(host='localhost', port=6379, db=1)
        redis_client.ping()
        
        # Check for Redis sessions
        redis_sessions = redis_client.keys("wegweiser:session:*")
        if redis_sessions:
            return "redis", len(redis_sessions)
        
        # Check for filesystem sessions
        import os
        session_dir = "/opt/flask_session"
        if os.path.exists(session_dir):
            session_files = [f for f in os.listdir(session_dir) if f.startswith('session:')]
            if session_files:
                return "filesystem", len(session_files)
        
        return "unknown", 0
        
    except Exception as e:
        return "error", str(e)

def check_application_logs():
    """Check for session-related errors in application logs"""
    try:
        with open('/opt/wegweiser/wlog/wegweiser.log', 'r') as f:
            # Read last 100 lines
            lines = f.readlines()[-100:]
        
        error_indicators = [
            "Redis not available for sessions",
            "falling back to filesystem", 
            "CSRF session token is missing",
            "session corruption",
            "UnicodeDecodeError",
            "AttributeError: 'NoneType' object has no attribute 'sid'"
        ]
        
        recent_errors = []
        for line in lines:
            for indicator in error_indicators:
                if indicator in line:
                    recent_errors.append(line.strip())
                    break
        
        return recent_errors
        
    except Exception as e:
        return [f"Failed to read logs: {str(e)}"]

def main():
    """Run session and CSRF monitoring"""
    print(f"🔍 Session & CSRF Monitor - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Check 1: CSRF token availability
    csrf_ok, csrf_message = check_csrf_token_availability()
    print(f"CSRF Token Check: {'✅ PASS' if csrf_ok else '❌ FAIL'} - {csrf_message}")
    
    # Check 2: Session backend
    backend, count = check_session_backend()
    print(f"Session Backend: {backend.upper()} ({count} active sessions)")
    
    # Check 3: Application logs
    log_errors = check_application_logs()
    if log_errors:
        print(f"Recent Errors: {len(log_errors)} found")
        for error in log_errors[-3:]:  # Show last 3 errors
            print(f"  - {error}")
    else:
        print("Recent Errors: None found")
    
    # Overall assessment
    overall_status = "HEALTHY"
    alerts = []
    
    if not csrf_ok:
        overall_status = "CRITICAL"
        alerts.append("CSRF tokens not available - login will fail")
    
    if backend == "filesystem":
        overall_status = "DEGRADED" if overall_status == "HEALTHY" else overall_status
        alerts.append("Using filesystem sessions - Redis may be down")
    
    if backend == "error":
        overall_status = "CRITICAL"
        alerts.append(f"Session backend error: {count}")
    
    if "CSRF session token is missing" in str(log_errors):
        overall_status = "CRITICAL"
        alerts.append("CSRF token errors detected in logs")
    
    print(f"\n🎯 Overall Status: {overall_status}")
    
    if alerts:
        print("🚨 Alerts:")
        for alert in alerts:
            print(f"  - {alert}")
        
        # Log critical issues
        if overall_status == "CRITICAL":
            logging.error(f"CRITICAL session issue detected: {'; '.join(alerts)}")
    else:
        print("✅ No issues detected")
        logging.info("Session and CSRF monitoring: All checks passed")
    
    return overall_status == "HEALTHY"

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
