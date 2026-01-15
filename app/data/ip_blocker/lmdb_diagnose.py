#!/usr/bin/env python3
# Filepath: app/data/ip_blocker/lmdb_diagnose.py

import os
import sys
import lmdb
import json
import argparse
import logging
import time
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('lmdb_diagnose')

def format_size(size_bytes):
    """Format size in bytes to human-readable format"""
    if size_bytes < 1024:
        return f"{size_bytes} bytes"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes/1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes/(1024*1024):.2f} MB"
    else:
        return f"{size_bytes/(1024*1024*1024):.2f} GB"

def diagnose_lmdb(db_path):
    """Run diagnostic tests on LMDB database"""
    logger.info(f"Diagnosing LMDB database at {db_path}")
    
    # Check if directory exists
    if not os.path.exists(db_path):
        logger.error(f"Database directory {db_path} does not exist")
        return False
    
    # Check data.mdb file
    data_path = os.path.join(db_path, 'data.mdb')
    if not os.path.exists(data_path):
        logger.error(f"data.mdb file not found at {data_path}")
        return False
    
    # Check file permissions
    data_perms = oct(os.stat(data_path).st_mode)[-3:]
    logger.info(f"data.mdb permissions: {data_perms}")
    data_size = os.path.getsize(data_path)
    logger.info(f"data.mdb size: {format_size(data_size)} ({data_size} bytes)")
    
    # Check lock file
    lock_path = os.path.join(db_path, 'lock.mdb')
    if os.path.exists(lock_path):
        lock_perms = oct(os.stat(lock_path).st_mode)[-3:]
        logger.info(f"lock.mdb permissions: {lock_perms}")
        lock_size = os.path.getsize(lock_path)
        logger.info(f"lock.mdb size: {format_size(lock_size)} ({lock_size} bytes)")
    else:
        logger.warning("lock.mdb file not found")
    
    # Try basic LMDB operations
    try:
        logger.info("Attempting to open LMDB environment (read-only)...")
        env = lmdb.open(
            db_path,
            readonly=True,
            lock=False,
            max_dbs=5
        )
        
        logger.info("LMDB environment opened successfully")
        
        # Get env info
        env_info = env.info()
        logger.info(f"Environment info: {env_info}")
        
        # Try to open databases
        logger.info("Trying to list database names...")
        
        # Try to create a transaction
        try:
            with env.begin() as txn:
                logger.info("Successfully created a read transaction")
                
                # Attempt basic operation with main DB
                try:
                    cursor = txn.cursor()
                    if cursor.first():
                        key, value = cursor.item()
                        logger.info(f"Successfully read first key from main DB: {key}")
                    else:
                        logger.info("Main database is empty")
                except Exception as e:
                    logger.error(f"Error reading from main DB: {e}")
                
                # Try to access named DBs
                try:
                    sets_db = env.open_db(b'sets', txn=txn)
                    logger.info("Successfully opened 'sets' database")
                    
                    # Try to read from sets DB
                    cursor = txn.cursor(db=sets_db)
                    if cursor.first():
                        key, value = cursor.item()
                        key_str = key.decode('utf-8') if isinstance(key, bytes) else str(key)
                        logger.info(f"First key in sets DB: {key_str}")
                        
                        # Try to decode value
                        try:
                            if isinstance(value, bytes):
                                value_str = value.decode('utf-8')
                                try:
                                    value_json = json.loads(value_str)
                                    logger.info(f"Value is valid JSON with {len(value_json)} items")
                                except json.JSONDecodeError:
                                    logger.info(f"Value is not JSON: {value_str[:50]}...")
                            else:
                                logger.info(f"Value is not bytes: {type(value)}")
                        except Exception as e:
                            logger.error(f"Error decoding value: {e}")
                    else:
                        logger.info("Sets database is empty")
                except Exception as e:
                    logger.error(f"Error working with sets DB: {e}")
                
                # Try to list all keys in main DB
                try:
                    cursor = txn.cursor()
                    key_count = 0
                    if cursor.first():
                        key_count = 1
                        while cursor.next():
                            key_count += 1
                    logger.info(f"Found {key_count} keys in main DB")
                except Exception as e:
                    logger.error(f"Error counting keys in main DB: {e}")
                
        except Exception as e:
            logger.error(f"Error creating transaction: {e}")
        
        # Close environment
        env.close()
        logger.info("Closed LMDB environment")
        
    except Exception as e:
        logger.error(f"Error opening LMDB environment: {e}")
        return False
    
    # Try opening again with different flags
    try:
        logger.info("Attempting to open LMDB environment (read-write)...")
        env = lmdb.open(
            db_path,
            readonly=False,
            lock=True,
            max_dbs=5,
            map_size=10 * 1024 * 1024  # 10 MB
        )
        logger.info("LMDB environment opened successfully in read-write mode")
        env.close()
        logger.info("Closed read-write environment")
    except Exception as e:
        logger.error(f"Error opening LMDB environment in read-write mode: {e}")

    return True

def get_blocked_ips(db_path, search_term=None, limit=None):
    """
    Get blocked IPs from the database
    
    Args:
        db_path: Path to the LMDB database
        search_term: Optional search term to filter IPs
        limit: Optional limit on the number of IPs to return
    
    Returns:
        List of blocked IPs (or dict with details if available)
    """
    blocked_ips = []
    
    try:
        env = lmdb.open(db_path, readonly=True, lock=False, max_dbs=5)
        
        with env.begin() as txn:
            # Try to get IPs from the blacklist set
            sets_db = env.open_db(b'sets', txn=txn)
            cursor = txn.cursor(db=sets_db)
            
            # Look for the blacklist key
            if cursor.set_key(b'wegweiser:ip_blocker:blacklist'):
                key, value = cursor.item()
                value_str = value.decode('utf-8') if isinstance(value, bytes) else str(value)
                
                try:
                    ip_list = json.loads(value_str)
                    
                    # Apply search filter if provided
                    if search_term:
                        ip_list = [ip for ip in ip_list if search_term in ip]
                    
                    # Apply limit if provided
                    if limit and len(ip_list) > limit:
                        ip_list = ip_list[:limit]
                        
                    blocked_ips = ip_list
                except json.JSONDecodeError:
                    logger.error("Failed to decode blacklist JSON")
            
            # Try to get detailed information about blocked IPs
            blocked_ip_details = {}
            hash_db = env.open_db(b'hashes', txn=txn)
            cursor = txn.cursor(db=hash_db)
            
            # Look for detailed IP information
            if cursor.first():
                while True:
                    key, value = cursor.item()
                    key_str = key.decode('utf-8') if isinstance(key, bytes) else str(key)
                    
                    # Check if this is an IP detail key
                    if key_str.startswith('wegweiser:ip_blocker:ip:'):
                        ip = key_str.split(':')[-1]
                        
                        # Apply search filter if provided
                        if search_term and search_term not in ip:
                            if not cursor.next():
                                break
                            continue
                        
                        try:
                            value_str = value.decode('utf-8')
                            ip_info = json.loads(value_str)
                            blocked_ip_details[ip] = ip_info
                        except (json.JSONDecodeError, UnicodeDecodeError):
                            blocked_ip_details[ip] = {"raw_data": str(value)}
                    
                    if not cursor.next():
                        break
            
            # If we found detailed information, use it instead of just IPs
            if blocked_ip_details:
                # If we have a list of IPs, filter the details to match
                if blocked_ips:
                    filtered_details = {ip: details for ip, details in blocked_ip_details.items() 
                                     if ip in blocked_ips}
                    blocked_ips = filtered_details
                else:
                    # Apply limit if provided
                    if limit and len(blocked_ip_details) > limit:
                        blocked_ips = dict(list(blocked_ip_details.items())[:limit])
                    else:
                        blocked_ips = blocked_ip_details
            
        env.close()
    except Exception as e:
        logger.error(f"Error retrieving blocked IPs: {e}")
    
    return blocked_ips

def get_whitelisted_ips(db_path, search_term=None, limit=None):
    """
    Get whitelisted IPs from the database
    
    Args:
        db_path: Path to the LMDB database
        search_term: Optional search term to filter IPs
        limit: Optional limit on the number of IPs to return
    
    Returns:
        List of whitelisted IPs
    """
    whitelisted_ips = []
    
    # First try to get from LMDB
    try:
        env = lmdb.open(db_path, readonly=True, lock=False, max_dbs=5)
        
        with env.begin() as txn:
            # Try to get IPs from the whitelist set
            sets_db = env.open_db(b'sets', txn=txn)
            cursor = txn.cursor(db=sets_db)
            
            # Look for the whitelist key
            if cursor.set_key(b'wegweiser:ip_blocker:whitelist'):
                key, value = cursor.item()
                value_str = value.decode('utf-8') if isinstance(value, bytes) else str(value)
                
                try:
                    ip_list = json.loads(value_str)
                    logger.info(f"Found {len(ip_list)} whitelisted IPs in LMDB")
                    
                    # Apply search filter if provided
                    if search_term:
                        ip_list = [ip for ip in ip_list if search_term in ip]
                    
                    # Apply limit if provided
                    if limit and len(ip_list) > limit:
                        ip_list = ip_list[:limit]
                        
                    whitelisted_ips = ip_list
                except json.JSONDecodeError:
                    logger.error("Failed to decode whitelist JSON from LMDB")
        
        env.close()
    except Exception as e:
        logger.error(f"Error retrieving whitelisted IPs from LMDB: {e}")
    
    # If no IPs found in LMDB, check whitelist.json file
    if not whitelisted_ips:
        logger.info("No whitelisted IPs found in LMDB, checking whitelist.json")
        
        # Try multiple possible locations for whitelist.json
        possible_paths = [
            # Direct path in the ip_blocker directory
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'whitelist.json'),
            # One level up from the LMDB storage directory
            os.path.join(os.path.dirname(db_path), '..', 'whitelist.json'),
            # Absolute path
            '/opt/wegweiser/app/data/ip_blocker/whitelist.json',
            # Current directory
            os.path.join(os.getcwd(), 'app/data/ip_blocker/whitelist.json')
        ]
        
        for whitelist_path in possible_paths:
            logger.info(f"Checking whitelist path: {whitelist_path}")
            if os.path.exists(whitelist_path):
                logger.info(f"Found whitelist.json at: {whitelist_path}")
                try:
                    with open(whitelist_path, 'r') as f:
                        content = f.read().strip()
                        logger.info(f"Whitelist content (first 100 chars): {content[:100]}...")
                        
                        # Check if the content is directly a JSON array
                        if content.startswith('[') and content.endswith(']'):
                            try:
                                whitelist_data = json.loads(content)
                                # If it's already a list of IPs
                                if isinstance(whitelist_data, list):
                                    logger.info(f"Parsed whitelist.json as array with {len(whitelist_data)} IPs")
                                    whitelisted_ips = whitelist_data
                                else:
                                    logger.error(f"Whitelist file contains invalid format: {whitelist_data}")
                            except json.JSONDecodeError as e:
                                logger.error(f"Error parsing whitelist.json as array: {e}")
                        else:
                            # Try parsing as a regular JSON object with an 'ips' key
                            try:
                                whitelist_data = json.loads(content)
                                if 'ips' in whitelist_data:
                                    logger.info(f"Parsed whitelist.json as object with {len(whitelist_data.get('ips', []))} IPs")
                                    whitelisted_ips = whitelist_data.get('ips', [])
                                else:
                                    logger.error("No 'ips' key found in whitelist.json object")
                            except json.JSONDecodeError as e:
                                logger.error(f"Error parsing whitelist.json as object: {e}")
                    
                    # If we found IPs, no need to check other paths
                    if whitelisted_ips:
                        break
                        
                except Exception as e:
                    logger.error(f"Error reading whitelist.json at {whitelist_path}: {e}")
            else:
                logger.info(f"Whitelist.json not found at: {whitelist_path}")
    
    # Apply search filter if provided
    if search_term and whitelisted_ips:
        whitelisted_ips = [ip for ip in whitelisted_ips if search_term in ip]
    
    # Apply limit if provided
    if limit and whitelisted_ips and len(whitelisted_ips) > limit:
        whitelisted_ips = whitelisted_ips[:limit]
    
    return whitelisted_ips

def add_whitelist_from_json(db_path):
    """
    Add whitelist IPs from whitelist.json to LMDB
    
    Args:
        db_path: Path to the LMDB database
    
    Returns:
        Tuple of (success, message, count)
    """
    # First find the whitelist.json file
    possible_paths = [
        # Direct path in the ip_blocker directory
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'whitelist.json'),
        # One level up from the LMDB storage directory
        os.path.join(os.path.dirname(db_path), '..', 'whitelist.json'),
        # Absolute path
        '/opt/wegweiser/app/data/ip_blocker/whitelist.json',
        # Current directory
        os.path.join(os.getcwd(), 'app/data/ip_blocker/whitelist.json')
    ]
    
    whitelist_ips = []
    whitelist_path = None
    
    # Find and load the whitelist.json file
    for path in possible_paths:
        logger.info(f"Checking whitelist path: {path}")
        if os.path.exists(path):
            whitelist_path = path
            logger.info(f"Found whitelist.json at: {path}")
            try:
                with open(path, 'r') as f:
                    content = f.read().strip()
                    
                    # Check if the content is directly a JSON array
                    if content.startswith('[') and content.endswith(']'):
                        try:
                            whitelist_data = json.loads(content)
                            if isinstance(whitelist_data, list):
                                whitelist_ips = whitelist_data
                                logger.info(f"Loaded {len(whitelist_ips)} IPs from whitelist.json")
                            else:
                                return False, f"Whitelist file contains invalid format: {whitelist_data}", 0
                        except json.JSONDecodeError as e:
                            return False, f"Error parsing whitelist.json: {e}", 0
                    else:
                        # Try parsing as a regular JSON object with an 'ips' key
                        try:
                            whitelist_data = json.loads(content)
                            if 'ips' in whitelist_data:
                                whitelist_ips = whitelist_data.get('ips', [])
                                logger.info(f"Loaded {len(whitelist_ips)} IPs from whitelist.json object format")
                            else:
                                return False, "No 'ips' key found in whitelist.json object", 0
                        except json.JSONDecodeError as e:
                            return False, f"Error parsing whitelist.json as object: {e}", 0
                    
                    break  # Stop after finding a valid file
            except Exception as e:
                return False, f"Error reading whitelist.json at {path}: {e}", 0
    
    if not whitelist_path:
        return False, "Could not find whitelist.json file", 0
    
    if not whitelist_ips:
        return False, "No IPs found in whitelist.json", 0
    
    # Now add the IPs to LMDB
    try:
        env = lmdb.open(db_path, readonly=False, lock=True, max_dbs=5)
        
        with env.begin(write=True) as txn:
            sets_db = env.open_db(b'sets', txn=txn)
            
            # Check if whitelist key already exists
            current_whitelist = []
            if txn.get(b'wegweiser:ip_blocker:whitelist', db=sets_db):
                try:
                    value = txn.get(b'wegweiser:ip_blocker:whitelist', db=sets_db)
                    value_str = value.decode('utf-8') if isinstance(value, bytes) else str(value)
                    current_whitelist = json.loads(value_str)
                    logger.info(f"Found existing whitelist with {len(current_whitelist)} IPs")
                except Exception as e:
                    logger.error(f"Error reading existing whitelist: {e}")
            
            # Merge the lists without duplicates
            updated_whitelist = list(set(current_whitelist + whitelist_ips))
            added_count = len(updated_whitelist) - len(current_whitelist)
            
            # Only update if there are new IPs
            if added_count > 0:
                # Store the updated whitelist
                txn.put(
                    b'wegweiser:ip_blocker:whitelist',
                    json.dumps(updated_whitelist).encode('utf-8'),
                    db=sets_db
                )
                logger.info(f"Added {added_count} new IPs to whitelist in LMDB")
                
                # Also add a timestamp entry for when the whitelist was last updated
                now = int(time.time())
                txn.put(
                    b'wegweiser:ip_blocker:whitelist_updated',
                    str(now).encode('utf-8'),
                    db=sets_db
                )
            else:
                logger.info("No new IPs to add to whitelist")
        
        env.close()
        return True, f"Successfully added {added_count} IPs to whitelist in LMDB", added_count
    except Exception as e:
        logger.error(f"Error adding whitelist IPs to LMDB: {e}")
        return False, f"Error adding whitelist IPs to LMDB: {e}", 0

def display_ip_lists(db_path, search_term=None, limit=None, show_blocked=True, show_whitelist=True):
    """Display information about blocked and whitelisted IPs"""
    if show_blocked:
        blocked_ips = get_blocked_ips(db_path, search_term, limit)
        
        print("\n==== BLOCKED IPs ====")
        print(f"Total blocked IPs found: {len(blocked_ips)}")
        
        if isinstance(blocked_ips, dict):
            # Display IP details
            for i, (ip, details) in enumerate(blocked_ips.items(), 1):
                print(f"\n{i}. IP: {ip}")
                
                # Format the details nicely
                if isinstance(details, dict):
                    for key, value in details.items():
                        if key == 'timestamp':
                            try:
                                date_str = datetime.fromtimestamp(value).strftime('%Y-%m-%d %H:%M:%S')
                                print(f"   {key}: {date_str} ({value})")
                            except:
                                print(f"   {key}: {value}")
                        elif key == 'expiry' and value:
                            try:
                                date_str = datetime.fromtimestamp(value).strftime('%Y-%m-%d %H:%M:%S')
                                print(f"   {key}: {date_str} ({value})")
                            except:
                                print(f"   {key}: {value}")
                        else:
                            print(f"   {key}: {value}")
                else:
                    print(f"   Details: {details}")
                
                if i % 20 == 0 and i < len(blocked_ips) and input("\nContinue? (y/n): ").lower() != 'y':
                    break
        else:
            # Display simple IP list
            for i, ip in enumerate(blocked_ips, 1):
                print(f"{i}. {ip}")
                
                if i % 20 == 0 and i < len(blocked_ips) and input("\nContinue? (y/n): ").lower() != 'y':
                    break
    
    if show_whitelist:
        whitelisted_ips = get_whitelisted_ips(db_path, search_term, limit)
        
        print("\n==== WHITELISTED IPs ====")
        print(f"Total whitelisted IPs found: {len(whitelisted_ips)}")
        
        for i, ip in enumerate(whitelisted_ips, 1):
            print(f"{i}. {ip}")
            
            if i % 20 == 0 and i < len(whitelisted_ips) and input("\nContinue? (y/n): ").lower() != 'y':
                break

def summarize_ip_data(db_path):
    """
    Generate a summary of IP data in the LMDB database
    
    Args:
        db_path: Path to the LMDB database
    """
    # Get all IPs
    blocked_ips = get_blocked_ips(db_path)
    whitelisted_ips = get_whitelisted_ips(db_path)
    
    # Convert to list if it's a dictionary
    if isinstance(blocked_ips, dict):
        blocked_ip_list = list(blocked_ips.keys())
    else:
        blocked_ip_list = blocked_ips
    
    # Group IPs by first octet
    blocked_by_octet = {}
    for ip in blocked_ip_list:
        try:
            first_octet = ip.split('.')[0]
            if first_octet not in blocked_by_octet:
                blocked_by_octet[first_octet] = []
            blocked_by_octet[first_octet].append(ip)
        except:
            # Handle non-standard IPs
            if 'other' not in blocked_by_octet:
                blocked_by_octet['other'] = []
            blocked_by_octet['other'].append(ip)
    
    whitelist_by_octet = {}
    for ip in whitelisted_ips:
        try:
            first_octet = ip.split('.')[0]
            if first_octet not in whitelist_by_octet:
                whitelist_by_octet[first_octet] = []
            whitelist_by_octet[first_octet].append(ip)
        except:
            # Handle non-standard IPs
            if 'other' not in whitelist_by_octet:
                whitelist_by_octet['other'] = []
            whitelist_by_octet['other'].append(ip)
    
    # Print summary
    print("\n===== IP BLOCKER SUMMARY =====")
    print(f"Database location: {db_path}")
    
    print(f"\nBLOCKED IPs: {len(blocked_ip_list)}")
    print("---------------------------")
    # Sort by first octet (numerically)
    #for octet in sorted(blocked_by_octet.keys(), key=lambda x: int(x) if x.isdigit() else float('inf')):
    #    print(f"  Octet {octet}: {len(blocked_by_octet[octet])} IPs")
    
    print(f"\nWHITELISTED IPs: {len(whitelisted_ips)}")
    print("---------------------------")
    # Sort by first octet (numerically)
    # for octet in sorted(whitelist_by_octet.keys(), key=lambda x: int(x) if x.isdigit() else float('inf')):
    #     print(f"  Octet {octet}: {len(whitelist_by_octet[octet])} IPs")
    #     for ip in sorted(whitelist_by_octet[octet]):
    #        print(f"    - {ip}")
    
    # Get database stats
    try:
        env = lmdb.open(db_path, readonly=True, lock=False, max_dbs=5)
        with env.begin() as txn:
            # Try to count keys in main databases
            dbs = {
                'main': None,  # Main database
                'sets': env.open_db(b'sets', txn=txn),
                'hashes': env.open_db(b'hashes', txn=txn),
                'lists': env.open_db(b'lists', txn=txn),
                'expiry': env.open_db(b'expiry', txn=txn)
            }
            
            counts = {}
            for db_name, db in dbs.items():
                cursor = txn.cursor(db=db)
                count = 0
                if cursor.first():
                    count = 1
                    while cursor.next():
                        count += 1
                counts[db_name] = count
            
            # Get some sample data from each database type
            print("\nDATA SAMPLES")
            print("---------------------------")
            
            # Sample from sets
            cursor = txn.cursor(db=dbs['sets'])
            if cursor.first():
                key, value = cursor.item()
                key_str = key.decode('utf-8') if isinstance(key, bytes) else str(key)
                print(f"  Set key sample: {key_str}")
            
            # Sample from hashes
            cursor = txn.cursor(db=dbs['hashes'])
            if cursor.first():
                key, value = cursor.item()
                key_str = key.decode('utf-8') if isinstance(key, bytes) else str(key)
                print(f"  Hash key sample: {key_str}")
            
            # Get environmental info
            env_info = env.info()
            data_path = os.path.join(db_path, 'data.mdb')
            data_size = os.path.getsize(data_path) if os.path.exists(data_path) else 0
            
            print("\nDATABASE STATISTICS")
            print("---------------------------")
            print(f"  Total storage size: {format_size(data_size)}")
            print(f"  Map size: {format_size(env_info['map_size'])}")
            print(f"  Last transaction ID: {env_info['last_txnid']}")
            print(f"  Maximum readers: {env_info['max_readers']}")
            print(f"  Current readers: {env_info['num_readers']}")
            
            print("\nKEY COUNTS BY DATABASE")
            print("---------------------------")
            for db_name, count in counts.items():
                print(f"  {db_name.capitalize()}: {count} keys")
        
        env.close()
    except Exception as e:
        logger.error(f"Error getting database statistics: {e}")
    
    print("\n===== END OF SUMMARY =====\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Diagnose LMDB database issues and explore IP data")
    parser.add_argument("--path", help="Path to LMDB database directory")
    parser.add_argument("--repair", action="store_true", help="Attempt to repair the database (EXPERIMENTAL)")
    parser.add_argument("--list-blocked", action="store_true", help="List all blocked IPs")
    parser.add_argument("--list-whitelist", action="store_true", help="List all whitelisted IPs")
    parser.add_argument("--search", help="Search for an IP (partial matches supported)")
    parser.add_argument("--limit", type=int, help="Limit the number of IPs displayed")
    parser.add_argument("--show-all", action="store_true", help="Show both blocked and whitelisted IPs")
    parser.add_argument("--list-whitelist-addfromjson", action="store_true", 
                        help="Add whitelist IPs from whitelist.json to LMDB and display the whitelist")
    parser.add_argument("--summary", action="store_true", 
                        help="Show summary of IP data including counts and grouping by first octet")
    
    args = parser.parse_args()
    
    # Get database path
    if args.path:
        db_path = args.path
    else:
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lmdb_storage')
    
    # Handle special case for adding whitelist from JSON
    if args.list_whitelist_addfromjson:
        success, message, count = add_whitelist_from_json(db_path)
        print(f"\n{message}")
        
        # Display the whitelist after adding
        display_ip_lists(db_path, None, None, False, True)
    # Show summary if requested
    elif args.summary:
        summarize_ip_data(db_path)
    # Regular IP list flags
    elif args.list_blocked or args.list_whitelist or args.search or args.show_all:
        show_blocked = args.list_blocked or args.search or args.show_all
        show_whitelist = args.list_whitelist or args.search or args.show_all
        display_ip_lists(db_path, args.search, args.limit, show_blocked, show_whitelist)
    else:
        # Run diagnostics by default and show summary
        diagnose_lmdb(db_path)
        summarize_ip_data(db_path)
