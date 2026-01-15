#!/usr/bin/env python3
"""
Send Heartbeat Test - Manually send a heartbeat to the server
"""

import os
import json
import time
import requests
import logging

# Configuration
host = os.environ.get('WEGWEISER_HOST', 'app.wegweiser.tech')
device_uuid = os.environ.get('DEVICE_UUID', 'unknown')
tenant_uuid = os.environ.get('TENANT_UUID', 'unknown')

def get_logger():
    """Simple logging setup"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

logger = get_logger()

def main():
    """Send heartbeat"""
    logger.info("="*60)
    logger.info("SEND HEARTBEAT TEST")
    logger.info("="*60)
    logger.info(f"Host: {host}")
    logger.info(f"Device UUID: {device_uuid}")
    logger.info(f"Tenant UUID: {tenant_uuid}")
    
    # Prepare heartbeat payload
    heartbeat_data = {
        'device_uuid': device_uuid,
        'tenant_uuid': tenant_uuid,
        'agent_version': '3.0.1',
        'session_id': 'test-session',
        'timestamp': int(time.time() * 1000),
        'status': {
            'nats_server': 'tls://nats.wegweiser.tech:443',
            'connected': True
        },
        'system_info': {
            'uptime': 3600
        }
    }
    
    # Send heartbeat
    url = f'https://{host}/api/nats/device/{device_uuid}/heartbeat'
    logger.info(f"Sending heartbeat to: {url}")
    logger.info(f"Payload: {json.dumps(heartbeat_data, indent=2)}")
    
    try:
        response = requests.post(
            url,
            json=heartbeat_data,
            timeout=10,
            verify=False
        )
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response: {response.text}")
        
        if response.status_code == 200:
            logger.info("[SUCCESS] Heartbeat sent successfully")
            return True
        else:
            logger.error(f"[FAILED] Unexpected status code: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"[FAILED] Error sending heartbeat: {e}")
        return False

if __name__ == '__main__':
    main()

