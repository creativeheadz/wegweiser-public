#!/usr/bin/env python3
"""
Session Health Monitor
Detects session corruption and encoding issues before they cause outages
"""

import redis
import requests
import json
import time
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/opt/wegweiser/wlog/session_monitor.log'),
        logging.StreamHandler()
    ]
)

def check_redis_session_health():
    """Check Redis session storage health"""
    try:
        # Connect to session Redis
        redis_client = redis.Redis(
            host='localhost',
            port=6379,
            db=1,
            decode_responses=False,
            socket_timeout=5
        )
        
        # Test basic connectivity
        redis_client.ping()
        
        # Get session keys
        session_keys = redis_client.keys("wegweiser:session:*")
        
        # Test session data integrity
        corrupted_sessions = 0
        for key in session_keys[:5]:  # Check first 5 sessions
            try:
                data = redis_client.get(key)
                if data is None:
                    continue
                    
                # Try to decode as Flask-Session would
                if isinstance(data, str):
                    logging.warning(f"Session {key} stored as string - potential encoding issue")
                    corrupted_sessions += 1
                elif len(data) < 10:
                    logging.warning(f"Session {key} suspiciously small: {len(data)} bytes")
                    corrupted_sessions += 1
                    
            except Exception as e:
                logging.error(f"Failed to read session {key}: {str(e)}")
                corrupted_sessions += 1
        
        return {
            'status': 'healthy' if corrupted_sessions == 0 else 'degraded',
            'total_sessions': len(session_keys),
            'corrupted_sessions': corrupted_sessions,
            'redis_connected': True
        }
        
    except Exception as e:
        logging.error(f"Redis health check failed: {str(e)}")
        return {
            'status': 'failed',
            'error': str(e),
            'redis_connected': False
        }

def check_application_session_health():
    """Check if the application can create and use sessions"""
    try:
        # Make request to login page
        response = requests.get(
            'https://app.wegweiser.tech/login',
            timeout=10,
            verify=True
        )
        
        if response.status_code != 200:
            return {
                'status': 'failed',
                'error': f"HTTP {response.status_code}",
                'app_responding': False
            }
        
        # Check if session cookie is set
        session_cookie = None
        for cookie in response.cookies:
            if 'session' in cookie.name.lower():
                session_cookie = cookie
                break
        
        if not session_cookie:
            return {
                'status': 'degraded',
                'error': "No session cookie set",
                'app_responding': True
            }
        
        return {
            'status': 'healthy',
            'app_responding': True,
            'session_cookie': session_cookie.name,
            'cookie_secure': session_cookie.secure,
            'cookie_httponly': getattr(session_cookie, 'httponly', False)
        }
        
    except Exception as e:
        logging.error(f"Application health check failed: {str(e)}")
        return {
            'status': 'failed',
            'error': str(e),
            'app_responding': False
        }

def main():
    """Run health checks and report status"""
    logging.info("Starting session health check")
    
    # Check Redis health
    redis_health = check_redis_session_health()
    logging.info(f"Redis health: {redis_health}")
    
    # Check application health
    app_health = check_application_session_health()
    logging.info(f"Application health: {app_health}")
    
    # Overall status
    overall_status = 'healthy'
    if redis_health['status'] == 'failed' or app_health['status'] == 'failed':
        overall_status = 'failed'
    elif redis_health['status'] == 'degraded' or app_health['status'] == 'degraded':
        overall_status = 'degraded'
    
    # Alert if issues detected
    if overall_status != 'healthy':
        alert_message = f"Session health issue detected: {overall_status}"
        if redis_health.get('corrupted_sessions', 0) > 0:
            alert_message += f" - {redis_health['corrupted_sessions']} corrupted sessions"
        if not app_health.get('app_responding', True):
            alert_message += " - Application not responding"
        
        logging.error(alert_message)
        
        # Could add email/Slack notification here
        
    else:
        logging.info(f"Session health check passed - {redis_health.get('total_sessions', 0)} active sessions")
    
    return overall_status == 'healthy'

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
