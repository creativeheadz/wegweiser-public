#!/usr/bin/env python3
# Filepath: app/data/ip_blocker/unblock_whitelisted_ip.py

import sys
import os

# Add the parent directories to the path so we can import from app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

# Import Flask app to create application context
from app import create_app
from app.utilities.ip_blocker import IPBlocker
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('unblock_whitelisted')

def unblock_whitelisted_ip(ip_address):
    """
    Unblock an IP that should be whitelisted but is currently blocked in iptables
    """
    try:
        # Initialize the IP blocker
        blocker = IPBlocker()
        
        # Check if IP is whitelisted
        if blocker.is_whitelisted(ip_address):
            logger.info(f"IP {ip_address} is confirmed to be whitelisted")
            
            # Check if it's in the blacklist
            if blocker.storage.sismember("wegweiser:ip_blocker:blacklist", ip_address):
                logger.info(f"IP {ip_address} is in blacklist, attempting to unblock...")
                
                # Use the unblock_ip method to remove from blacklist and iptables
                result = blocker.unblock_ip(ip_address)
                
                if result.get("success"):
                    logger.info(f"Successfully unblocked IP {ip_address}: {result.get('reason')}")
                    return True
                else:
                    logger.error(f"Failed to unblock IP {ip_address}: {result.get('reason')}")
                    return False
            else:
                logger.info(f"IP {ip_address} is not in blacklist, but may still have iptables rule")
                
                # Try to remove iptables rule directly
                if blocker._execute_iptables_command('-D', ip_address):
                    logger.info(f"Successfully removed iptables rule for {ip_address}")
                    return True
                else:
                    logger.warning(f"Could not remove iptables rule for {ip_address} (may not exist)")
                    return False
        else:
            logger.error(f"IP {ip_address} is NOT whitelisted, cannot unblock")
            return False
            
    except Exception as e:
        logger.error(f"Error unblocking IP {ip_address}: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 unblock_whitelisted_ip.py <ip_address>")
        sys.exit(1)
    
    ip_address = sys.argv[1]
    
    print(f"Attempting to unblock whitelisted IP: {ip_address}")
    
    if unblock_whitelisted_ip(ip_address):
        print(f"SUCCESS: IP {ip_address} has been unblocked")
    else:
        print(f"FAILED: Could not unblock IP {ip_address}")
        sys.exit(1)
