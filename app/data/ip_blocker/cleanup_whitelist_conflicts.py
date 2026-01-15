#!/usr/bin/env python3
# Filepath: app/data/ip_blocker/cleanup_whitelist_conflicts.py

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
logger = logging.getLogger('cleanup_conflicts')

def cleanup_conflicts():
    """
    Clean up any IPs that are in both whitelist and blacklist
    """
    try:
        # Create Flask app context
        app = create_app()
        
        with app.app_context():
            # Initialize the IP blocker
            blocker = IPBlocker()
            
            print("Checking for whitelist/blacklist conflicts...")
            
            # Get current lists
            lists = blocker.get_lists()
            whitelist = lists["whitelist"]
            blacklist = lists["blacklist"]
            
            print(f"Current whitelist size: {len(whitelist)}")
            print(f"Current blacklist size: {len(blacklist)}")
            
            # Find conflicts
            conflicts = whitelist.intersection(blacklist)
            
            if conflicts:
                print(f"\nFound {len(conflicts)} IPs in both lists:")
                for ip in conflicts:
                    print(f"  - {ip}")
                
                print("\nCleaning up conflicts...")
                result = blocker.cleanup_whitelist_blacklist_conflicts()
                
                if result.get("success"):
                    print(f"✅ {result.get('message')}")
                    if result.get("failed_ips"):
                        print(f"❌ Failed IPs: {', '.join(result.get('failed_ips'))}")
                else:
                    print(f"❌ Cleanup failed: {result.get('message')}")
                    return False
            else:
                print("✅ No conflicts found - all good!")
            
            # Also sync whitelist from file
            print("\nSyncing whitelist from file...")
            if blocker._sync_whitelist_to_storage():
                print("✅ Whitelist sync completed")
            else:
                print("❌ Whitelist sync failed")
                return False
            
            return True
            
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")
        print(f"❌ Error during cleanup: {str(e)}")
        return False

if __name__ == "__main__":
    print("IP Blocker Whitelist/Blacklist Conflict Cleanup Tool")
    print("=" * 55)
    
    if cleanup_conflicts():
        print("\n🎉 Cleanup completed successfully!")
    else:
        print("\n💥 Cleanup failed!")
        sys.exit(1)
