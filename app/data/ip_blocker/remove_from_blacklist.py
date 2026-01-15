#!/usr/bin/env python3
# Filepath: app/data/ip_blocker/remove_from_blacklist.py

import os
import sys
import lmdb
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('remove_blacklist')

def remove_ip_from_blacklist(db_path, ip_address):
    """
    Remove an IP from the blacklist in LMDB
    
    Args:
        db_path: Path to the LMDB database
        ip_address: IP address to remove from blacklist
    
    Returns:
        Tuple of (success, message)
    """
    try:
        env = lmdb.open(db_path, readonly=False, lock=True, max_dbs=5)
        
        with env.begin(write=True) as txn:
            # Get the sets database
            sets_db = env.open_db(b'sets', txn=txn)
            
            # Get current blacklist
            blacklist_key = b'wegweiser:ip_blocker:blacklist'
            current_blacklist_bytes = txn.get(blacklist_key, db=sets_db)
            
            if current_blacklist_bytes is None:
                return False, "Blacklist not found in database"
            
            try:
                current_blacklist = json.loads(current_blacklist_bytes.decode('utf-8'))
            except json.JSONDecodeError:
                return False, "Failed to decode blacklist JSON"
            
            # Check if IP is in blacklist
            if ip_address not in current_blacklist:
                return False, f"IP {ip_address} is not in blacklist"
            
            # Remove IP from blacklist
            current_blacklist.remove(ip_address)
            logger.info(f"Removed {ip_address} from blacklist")
            
            # Update the blacklist in database
            txn.put(blacklist_key, json.dumps(current_blacklist).encode('utf-8'), db=sets_db)
            
            # Also remove any blacklist data for this IP
            hashes_db = env.open_db(b'hashes', txn=txn)
            ip_data_key = f'wegweiser:ip_blocker:blacklist_data:{ip_address}'.encode('utf-8')
            if txn.get(ip_data_key, db=hashes_db):
                txn.delete(ip_data_key, db=hashes_db)
                logger.info(f"Removed blacklist data for {ip_address}")
        
        env.close()
        return True, f"Successfully removed {ip_address} from blacklist"
        
    except Exception as e:
        logger.error(f"Error removing IP from blacklist: {e}")
        return False, f"Error removing IP from blacklist: {e}"

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 remove_from_blacklist.py <ip_address>")
        sys.exit(1)
    
    ip_address = sys.argv[1]
    
    # Get database path
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lmdb_storage')
    
    print(f"Attempting to remove {ip_address} from blacklist in LMDB...")
    
    success, message = remove_ip_from_blacklist(db_path, ip_address)
    
    if success:
        print(f"SUCCESS: {message}")
    else:
        print(f"FAILED: {message}")
        sys.exit(1)
