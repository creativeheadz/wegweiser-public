# Filepath: app/utilities/ip_blocker.py
import subprocess
import logging
from flask import current_app
import time
import json
import os
import threading
from typing import Optional, Dict, Set, List, Any, Union
from app.utilities.app_logging_helper import log_with_route
import lmdb
from collections import defaultdict

class LMDBStorage:
    """LMDB storage adapter with Redis-like interface for IP blocker"""
    
    def __init__(self):
        self.env = None
        self.lock = threading.RLock()
        # Add cached DB handles to avoid repeatedly opening new ones
        self._db_cache = {}
        self._initialize_db()
        
    def _initialize_db(self):
        """Initialize the LMDB environment"""
        try:
            storage_path = self._get_storage_path()
            os.makedirs(os.path.dirname(storage_path), exist_ok=True)
            
            # Default map size of 10MB - adjust as needed
            map_size = 10485760
            if hasattr(current_app, 'config'):
                map_size = current_app.config.get('IP_BLOCKER_LMDB_MAP_SIZE', map_size)
                
            self.env = lmdb.open(
                storage_path, 
                map_size=map_size,
                metasync=True,
                sync=True,
                subdir=True,
                writemap=True,
                map_async=False,
                mode=0o644,
                max_dbs=20  # Increase from default 5 to 20
            )
            
            # Pre-open the databases we'll be using to avoid "DBS_FULL" errors
            with self.env.begin(write=True) as txn:
                self._get_db('sets', txn)
                self._get_db('hashes', txn)
                self._get_db('lists', txn)
                self._get_db('counters', txn)
                self._get_db('expire', txn)
            
            log_with_route(logging.INFO, f"Initialized LMDB storage at {storage_path}")
        except Exception as e:
            log_with_route(logging.ERROR, f"Failed to initialize LMDB storage: {str(e)}")
            raise
    
    def _get_storage_path(self):
        """Get path for LMDB storage"""
        if hasattr(current_app, 'config') and 'IP_BLOCKER_DATA_DIR' in current_app.config:
            # Use the path from Flask configuration
            return os.path.join(current_app.config['IP_BLOCKER_DATA_DIR'], 'lmdb_storage')
        else:
            # Fallback to a default path if not in Flask context
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
            return os.path.join(base_dir, 'app', 'data', 'ip_blocker', 'lmdb_storage')
        
    def _get_db(self, db_name, txn):
        """Get a database handle, either from cache or open a new one"""
        if db_name not in self._db_cache:
            try:
                self._db_cache[db_name] = self.env.open_db(db_name.encode('utf-8'), txn=txn)
                log_with_route(logging.DEBUG, f"Opened LMDB database: {db_name}")
            except lmdb.DbsFullError:
                log_with_route(logging.ERROR, f"Failed to open database {db_name}: MDB_DBS_FULL error")
                # Return None if we can't open the database
                return None
        return self._db_cache[db_name]
    
    # Helper methods for serialization
    def _serialize(self, value):
        """Serialize value for storage"""
        if isinstance(value, set):
            # For sets (like IP lists), convert to JSON-compatible list
            return json.dumps(list(value)).encode('utf-8')
        elif isinstance(value, (dict, list, int, float, str, bool, type(None))):
            # JSON-serializable types
            return json.dumps(value).encode('utf-8')
        else:
            # For other types, convert to string
            return json.dumps(str(value)).encode('utf-8')
    
    def _deserialize(self, value):
        """Deserialize value from storage"""
        if value is None:
            return None
            
        try:
            # Decode as JSON 
            decoded = value.decode('utf-8')
            return json.loads(decoded)
        except (UnicodeDecodeError, json.JSONDecodeError):
            # Fall back to string if not JSON
            try:
                return value.decode('utf-8')
            except:
                return str(value)
    
    def ping(self):
        """Test connection"""
        return self.env is not None
    
    def sadd(self, key, *values):
        """Add values to a set"""
        with self.lock:
            added = 0
            
            with self.env.begin(write=True) as txn:
                sets_db = self._get_db('sets', txn)
                if sets_db is None:
                    log_with_route(logging.ERROR, f"Failed to open sets database, cannot add to {key}")
                    return 0
                    
                key_bytes = key.encode('utf-8')
                current_set_bytes = txn.get(key_bytes, db=sets_db)
                
                if current_set_bytes is None:
                    # New set
                    current_set = []
                else:
                    try:
                        # JSON decoding
                        current_set = json.loads(current_set_bytes.decode('utf-8'))
                    except:
                        current_set = []
                
                # Convert to list if it's another iterable
                if not isinstance(current_set, list):
                    current_set = list(current_set) if hasattr(current_set, '__iter__') else []
                
                # Add new values
                for value in values:
                    if value not in current_set:
                        current_set.append(value)
                        added += 1
                
                # Store the updated set
                if added > 0:
                    txn.put(key_bytes, json.dumps(current_set).encode('utf-8'), db=sets_db)
                    log_with_route(logging.INFO, f"Added {added} items to set {key}, new size: {len(current_set)}")
            
            return added
    
    def sismember(self, key, value):
        """Check if value is in a set"""
        with self.env.begin() as txn:
            sets_db = self._get_db('sets', txn)
            if sets_db is None:
                return False
                
            key_bytes = key.encode('utf-8')
            current_set_bytes = txn.get(key_bytes, db=sets_db)
            
            if current_set_bytes is None:
                return False
            
            try:
                current_set = json.loads(current_set_bytes.decode('utf-8'))
            except:
                return False
                
            return value in current_set
    
    def smembers(self, key):
        """Get all members of a set"""
        with self.env.begin() as txn:
            sets_db = self._get_db('sets', txn)
            if sets_db is None:
                return set()
                
            key_bytes = key.encode('utf-8')
            current_set_bytes = txn.get(key_bytes, db=sets_db)
            
            if current_set_bytes is None:
                return set()
            
            try:
                current_set = json.loads(current_set_bytes.decode('utf-8'))
                return set(current_set)
            except:
                return set()
    
    def srem(self, key, *values):
        """Remove values from a set"""
        with self.lock:
            key_bytes = key.encode('utf-8')
            removed = 0
            
            with self.env.begin(write=True) as txn:
                sets_db = self._get_db('sets', txn)
                if sets_db is None:
                    log_with_route(logging.ERROR, f"Failed to open sets database, cannot remove from {key}")
                    return 0
                
                # Get current set
                current_set_bytes = txn.get(key_bytes, db=sets_db)
                if current_set_bytes is None:
                    return 0
                
                current_set = self._deserialize(current_set_bytes)
                if not isinstance(current_set, list):
                    current_set = list(current_set) if hasattr(current_set, '__iter__') else []
                
                # Remove values
                for value in values:
                    if value in current_set:
                        current_set.remove(value)
                        removed += 1
                
                # Store the updated set or delete if empty
                if not current_set:
                    txn.delete(key_bytes, db=sets_db)
                else:
                    txn.put(key_bytes, json.dumps(current_set).encode('utf-8'), db=sets_db)
                
            return removed
    
    def exists(self, key):
        """Check if key exists"""
        with self.env.begin() as txn:
            for prefix in ["set:", "hash:", "list:", "counter:", "expire:"]:
                if txn.get(f"{prefix}{key}".encode('utf-8')) is not None:
                    return True
            return False
    
    def delete(self, key):
        """Delete a key"""
        with self.lock:
            deleted = 0
            
            with self.env.begin(write=True) as txn:
                for prefix in ["set:", "hash:", "list:", "counter:", "expire:"]:
                    key_bytes = f"{prefix}{key}".encode('utf-8')
                    if txn.get(key_bytes) is not None:
                        txn.delete(key_bytes)
                        deleted += 1
            
            return deleted
    
    def hset(self, key, field, value):
        """Set hash field to value"""
        with self.lock:
            with self.env.begin(write=True) as txn:
                hashes_db = self._get_db('hashes', txn)
                if hashes_db is None:
                    log_with_route(logging.ERROR, f"Failed to open hashes database, cannot set field {field} in {key}")
                    return 0
                
                key_bytes = key.encode('utf-8')
                
                # Get current hash
                current_hash_bytes = txn.get(key_bytes, db=hashes_db)
                current_hash = {} if current_hash_bytes is None else self._deserialize(current_hash_bytes)
                
                if not isinstance(current_hash, dict):
                    current_hash = {}
                
                # Set field
                is_new = field not in current_hash
                current_hash[field] = value
                
                # Store the updated hash
                txn.put(key_bytes, self._serialize(current_hash), db=hashes_db)
                
                # Log the key update
                log_with_route(logging.DEBUG, f"Updated hash field {field} in key {key}")
                
            return 1 if is_new else 0
    
    def hmset(self, key, mapping):
        """Set multiple hash fields to values"""
        if not isinstance(mapping, dict):
            return 0
            
        with self.lock:
            with self.env.begin(write=True) as txn:
                hashes_db = self._get_db('hashes', txn)
                if hashes_db is None:
                    log_with_route(logging.ERROR, f"Failed to open hashes database, cannot set fields in {key}")
                    return False
                
                key_bytes = key.encode('utf-8')
                
                # Get current hash
                current_hash_bytes = txn.get(key_bytes, db=hashes_db)
                current_hash = {} if current_hash_bytes is None else self._deserialize(current_hash_bytes)
                
                if not isinstance(current_hash, dict):
                    current_hash = {}
                
                # Update with new values
                current_hash.update(mapping)
                
                # Store the updated hash
                txn.put(key_bytes, self._serialize(current_hash), db=hashes_db)
                
                # Log update
                log_with_route(logging.DEBUG, f"Updated hash {key} with {len(mapping)} fields")
                
            return True
    
    def hgetall(self, key):
        """Get all fields and values in a hash"""
        hash_key = f"hash:{key}".encode('utf-8')
        
        with self.env.begin() as txn:
            current_hash_bytes = txn.get(hash_key)
            if current_hash_bytes is None:
                return {}
            
            return self._deserialize(current_hash_bytes)
    
    def lpush(self, key, *values):
        """Prepend values to a list"""
        with self.lock:
            list_key = f"list:{key}".encode('utf-8')
            
            with self.env.begin(write=True) as txn:
                current_list_bytes = txn.get(list_key)
                current_list = [] if current_list_bytes is None else self._deserialize(current_list_bytes)
                
                # Prepend values in reverse order
                for value in values:
                    current_list.insert(0, value)
                
                txn.put(list_key, self._serialize(current_list))
            
            return len(current_list)
    
    def lrange(self, key, start, end):
        """Get a range of elements from a list"""
        list_key = f"list:{key}".encode('utf-8')
        
        with self.env.begin() as txn:
            current_list_bytes = txn.get(list_key)
            if current_list_bytes is None:
                return []
            
            current_list = self._deserialize(current_list_bytes)
            if end == -1:
                return current_list[start:]
            return current_list[start:end+1]
    
    def ltrim(self, key, start, end):
        """Trim a list to the specified range"""
        with self.lock:
            list_key = f"list:{key}".encode('utf-8')
            
            with self.env.begin(write=True) as txn:
                current_list_bytes = txn.get(list_key)
                if current_list_bytes is None:
                    return True
                
                current_list = self._deserialize(current_list_bytes)
                if end == -1:
                    new_list = current_list[start:]
                else:
                    new_list = current_list[start:end+1]
                
                if not new_list:
                    txn.delete(list_key)
                else:
                    txn.put(list_key, self._serialize(new_list))
            
            return True
    
    def incr(self, key):
        """Increment the integer value of a key"""
        with self.lock:
            counter_key = f"counter:{key}".encode('utf-8')
            
            with self.env.begin(write=True) as txn:
                current_value_bytes = txn.get(counter_key)
                current_value = 0 if current_value_bytes is None else self._deserialize(current_value_bytes)
                
                new_value = current_value + 1
                txn.put(counter_key, self._serialize(new_value))
            
            return new_value

class IPBlocker:
    _instance = None
    IPTABLES_PATH = '/usr/sbin/iptables'
    SUDO_PATH = '/usr/bin/sudo'
    ERROR_THRESHOLD = 2  # Number of failed requests before blocking

    # INTERNAL SERVICES PROTECTION - Never block these IPs
    # If someone can access localhost, they're already on the server and game is over anyway
    INTERNAL_WHITELISTED_IPS = {
        '127.0.0.1',      # IPv4 localhost
        '::1',            # IPv6 localhost
        'localhost',      # Hostname
    }
    INTERNAL_WHITELISTED_PREFIXES = (
        '127.',           # All 127.x.x.x addresses (loopback range)
        '10.',            # Private network
        '172.16.', '172.17.', '172.18.', '172.19.',  # Private network
        '172.20.', '172.21.', '172.22.', '172.23.',
        '172.24.', '172.25.', '172.26.', '172.27.',
        '172.28.', '172.29.', '172.30.', '172.31.',
        '192.168.',       # Private network
    )

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(IPBlocker, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self):
        if self.initialized:
            return
        
        try:
            # Initialize LMDB storage
            self.storage = LMDBStorage()
            log_with_route(logging.INFO, "Using LMDB storage for IP blocking")
            
            # Sync whitelist from file to storage
            self._sync_whitelist_to_storage()
            
        except Exception as e:
            log_with_route(logging.CRITICAL, f"Failed to initialize storage: {str(e)}. IP blocking will not work!")
            # Create a dummy object that won't crash but won't do anything
            class DummyStorage:
                def __getattr__(self, name):
                    return lambda *args, **kwargs: None
            self.storage = DummyStorage()
        
        self.initialized = True
        
    def _load_whitelist_from_file(self):
        """Load whitelisted IPs from whitelist.json file"""
        try:
            # Determine the path to whitelist.json
            if hasattr(current_app, 'config') and 'IP_BLOCKER_DATA_DIR' in current_app.config:
                whitelist_path = os.path.join(current_app.config['IP_BLOCKER_DATA_DIR'], 'whitelist.json')
            else:
                base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
                whitelist_path = os.path.join(base_dir, 'app', 'data', 'ip_blocker', 'whitelist.json')
                
            # Check if the file exists
            if not os.path.exists(whitelist_path):
                log_with_route(logging.WARNING, f"Whitelist file not found at {whitelist_path}")
                return []
                
            # Read and parse the file
            with open(whitelist_path, 'r') as f:
                whitelist = json.load(f)
                
            if not isinstance(whitelist, list):
                log_with_route(logging.ERROR, f"Invalid whitelist format in {whitelist_path}, expected list")
                return []
                
            log_with_route(logging.INFO, f"Loaded {len(whitelist)} IPs from whitelist file")
            return whitelist
        except Exception as e:
            log_with_route(logging.ERROR, f"Error loading whitelist file: {str(e)}")
            return []

    def _sync_whitelist_to_storage(self):
        """Sync whitelist from file to storage and unblock any currently blocked IPs"""
        try:
            # Load whitelist from file
            whitelist_ips = self._load_whitelist_from_file()

            # Get current whitelist from storage
            current_whitelist = self.storage.smembers("wegweiser:ip_blocker:whitelist")

            # Add missing IPs to storage (this will also unblock them if needed)
            for ip in whitelist_ips:
                if ip not in current_whitelist:
                    self.add_to_whitelist(ip)
                    log_with_route(logging.INFO, f"Synced IP {ip} from whitelist.json to storage")
                else:
                    # Even if already in whitelist, check if it's blocked and unblock
                    if self.storage.sismember("wegweiser:ip_blocker:blacklist", ip):
                        log_with_route(logging.WARNING, f"IP {ip} is in both whitelist and blacklist, unblocking...")
                        unblock_result = self.unblock_ip(ip)
                        if unblock_result.get("success"):
                            log_with_route(logging.INFO, f"Unblocked whitelisted IP {ip}")
                        else:
                            log_with_route(logging.ERROR, f"Failed to unblock whitelisted IP {ip}: {unblock_result.get('reason')}")

            # Remove IPs from storage that aren't in file (optional)
            # for ip in current_whitelist:
            #     if ip not in whitelist_ips:
            #         self.remove_from_whitelist(ip)
            #         log_with_route(logging.INFO, f"Removed IP {ip} from storage (not in whitelist.json)")

            return True
        except Exception as e:
            log_with_route(logging.ERROR, f"Error syncing whitelist to storage: {str(e)}")
            return False

    def _is_internal_ip(self, ip: str) -> bool:
        """
        Check if an IP is internal (localhost/private network).
        CRITICAL: These IPs should NEVER be blocked - if someone has localhost access,
        they're already on the server and blocking their IP is pointless.
        """
        if not ip:
            return False

        # Check exact matches first (fastest)
        if ip in self.INTERNAL_WHITELISTED_IPS:
            return True

        # Check IP prefixes (loopback and private networks)
        if any(ip.startswith(prefix) for prefix in self.INTERNAL_WHITELISTED_PREFIXES):
            return True

        return False

    def is_whitelisted(self, ip: str) -> bool:
        """Check if an IP is whitelisted using file as primary source"""
        # FIRST: Check if IP is internal/localhost - HIGHEST PRIORITY
        # These should NEVER be blocked regardless of storage/file state
        if self._is_internal_ip(ip):
            log_with_route(logging.DEBUG, f"IP {ip} is internal/localhost, automatically whitelisted")
            return True

        # Second: Check the JSON file (authoritative source for user-defined whitelist)
        try:
            whitelist_ips = self._load_whitelist_from_file()
            if ip in whitelist_ips:
                return True
        except Exception as e:
            log_with_route(logging.ERROR, f"Error checking whitelist file: {str(e)}")

        # Third: Fallback to storage check
        try:
            return self.storage.sismember("wegweiser:ip_blocker:whitelist", ip)
        except Exception as e:
            log_with_route(logging.ERROR, f"Error checking whitelist in storage: {str(e)}")
            # If all checks fail, assume IP is not whitelisted
            return False

    def _execute_iptables_command(self, action: str, ip: str) -> bool:
        """Execute an iptables command to block or unblock an IP"""
        try:
            cmd = [
                self.SUDO_PATH,
                self.IPTABLES_PATH,
                action,
                'INPUT',
                '-s', ip,
                '-j', 'DROP'
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode != 0:
                log_with_route(
                    logging.ERROR,
                    f"iptables command failed: Command: {' '.join(cmd)}, "
                    f"Return code: {result.returncode}, Stderr: {result.stderr.strip()}"
                )
                return False

            log_with_route(logging.INFO, f"iptables command succeeded: {' '.join(cmd)}")
            return True
        except Exception as e:
            log_with_route(logging.ERROR, f"Error executing iptables command: {str(e)}")
            return False

    def block_ip(self, ip: str) -> Dict[str, bool]:
        """Block an IP address"""
        if self.is_whitelisted(ip):
            return {"success": False, "reason": "IP is whitelisted"}

        if self.storage.sismember("wegweiser:ip_blocker:blacklist", ip):
            return {"success": True, "reason": "IP already blocked"}

        try:
            # Add IP to blacklist
            result = self.storage.sadd("wegweiser:ip_blocker:blacklist", ip)
            log_with_route(logging.INFO, f"Added IP {ip} to blacklist, result: {result}")
            
            # Store block info
            block_data = {
                "block_timestamp": int(time.time()),
                "block_reason": "Manual block or threshold exceeded",
            }
            self.storage.hmset(f"wegweiser:ip_blocker:blacklist_data:{ip}", block_data)

            # Block IP using iptables
            if self._execute_iptables_command('-A', ip):
                log_with_route(logging.INFO, f"Blocked IP: {ip}")
                return {"success": True, "reason": "IP blocked successfully"}

            return {"success": False, "reason": "Failed to execute iptables command"}
        except Exception as e:
            log_with_route(logging.ERROR, f"Error blocking IP: {str(e)}")
            return {"success": False, "reason": str(e)}

    def unblock_ip(self, ip: str) -> Dict[str, bool]:
        """Unblock an IP address"""
        if not self.storage.sismember("wegweiser:ip_blocker:blacklist", ip):
            return {"success": False, "reason": "IP is not blocked"}
        try:
            self.storage.srem("wegweiser:ip_blocker:blacklist", ip)
            self.storage.delete(f"wegweiser:ip_blocker:blacklist_data:{ip}")

            # Unblock IP using iptables
            if self._execute_iptables_command('-D', ip):
                log_with_route(logging.INFO, f"Unblocked IP: {ip}")
                return {"success": True, "reason": "IP unblocked successfully"}

            return {"success": False, "reason": "Failed to execute iptables unblock command"}
        except Exception as e:
            log_with_route(logging.ERROR, f"Error unblocking IP: {str(e)}")
            return {"success": False, "reason": str(e)}

    def add_to_whitelist(self, ip: str) -> Dict[str, bool]:
        """Add an IP to the whitelist and remove from blacklist/iptables if needed"""
        try:
            # Check if IP is currently blocked and unblock it
            if self.storage.sismember("wegweiser:ip_blocker:blacklist", ip):
                log_with_route(logging.INFO, f"IP {ip} is currently blocked, unblocking before adding to whitelist")
                unblock_result = self.unblock_ip(ip)
                if not unblock_result.get("success"):
                    log_with_route(logging.WARNING, f"Failed to unblock IP {ip} before whitelisting: {unblock_result.get('reason')}")
                    # Continue anyway - we'll still add to whitelist
            else:
                # Even if not in blacklist, there might be an orphaned iptables rule
                # Try to remove it (this will fail silently if rule doesn't exist)
                try:
                    self._execute_iptables_command('-D', ip)
                    log_with_route(logging.INFO, f"Removed any existing iptables rule for {ip}")
                except Exception:
                    # Ignore errors - rule probably didn't exist
                    pass

            # Add to whitelist
            self.storage.sadd("wegweiser:ip_blocker:whitelist", ip)
            self.storage.hset(f"wegweiser:ip_blocker:whitelist_data:{ip}", "added_date", str(int(time.time())))

            # Clear any failed request history for this IP
            self.storage.delete(f"wegweiser:ip_blocker:failed:{ip}:count")
            self.storage.delete(f"wegweiser:ip_blocker:failed:{ip}:history")

            log_with_route(logging.INFO, f"Added IP to whitelist: {ip}")
            return {"success": True, "reason": "IP added to whitelist"}
        except Exception as e:
            log_with_route(logging.ERROR, f"Error adding IP to whitelist: {str(e)}")
            return {"success": False, "reason": str(e)}

    def remove_from_whitelist(self, ip: str) -> Dict[str, bool]:
        """Remove an IP from the whitelist"""
        if not self.storage.sismember("wegweiser:ip_blocker:whitelist", ip):
            return {"success": False, "reason": "IP is not whitelisted"}
        try:
            self.storage.srem("wegweiser:ip_blocker:whitelist", ip)
            self.storage.delete(f"wegweiser:ip_blocker:whitelist_data:{ip}")
            log_with_route(logging.INFO, f"Removed IP from whitelist: {ip}")
            return {"success": True, "reason": "IP removed from whitelist"}
        except Exception as e:
            log_with_route(logging.ERROR, f"Error removing IP from whitelist: {str(e)}")
            return {"success": False, "reason": str(e)}

    def get_lists(self) -> Dict[str, Set[str]]:
        """Get the whitelist and blacklist"""
        try:
            # For the whitelist, combine file-based and storage-based whitelists
            whitelist_from_file = set(self._load_whitelist_from_file())
            whitelist_from_storage = self.storage.smembers("wegweiser:ip_blocker:whitelist")
            combined_whitelist = whitelist_from_file.union(whitelist_from_storage)

            blacklist = self.storage.smembers("wegweiser:ip_blocker:blacklist")
            return {"whitelist": combined_whitelist, "blacklist": blacklist}
        except Exception as e:
            log_with_route(logging.ERROR, f"Error fetching lists: {str(e)}")
            return {"whitelist": set(), "blacklist": set()}

    def cleanup_whitelist_blacklist_conflicts(self) -> Dict[str, Any]:
        """Clean up any IPs that are in both whitelist and blacklist"""
        try:
            lists = self.get_lists()
            whitelist = lists["whitelist"]
            blacklist = lists["blacklist"]

            # Find IPs that are in both lists
            conflicts = whitelist.intersection(blacklist)

            if not conflicts:
                return {"success": True, "message": "No conflicts found", "conflicts_resolved": 0}

            resolved_count = 0
            failed_ips = []

            for ip in conflicts:
                log_with_route(logging.WARNING, f"Found IP {ip} in both whitelist and blacklist, unblocking...")
                unblock_result = self.unblock_ip(ip)
                if unblock_result.get("success"):
                    resolved_count += 1
                    log_with_route(logging.INFO, f"Successfully resolved conflict for IP {ip}")
                else:
                    failed_ips.append(ip)
                    log_with_route(logging.ERROR, f"Failed to resolve conflict for IP {ip}: {unblock_result.get('reason')}")

            message = f"Resolved {resolved_count} conflicts"
            if failed_ips:
                message += f", failed to resolve: {', '.join(failed_ips)}"

            return {
                "success": True,
                "message": message,
                "conflicts_resolved": resolved_count,
                "failed_ips": failed_ips,
                "total_conflicts": len(conflicts)
            }

        except Exception as e:
            log_with_route(logging.ERROR, f"Error cleaning up whitelist/blacklist conflicts: {str(e)}")
            return {"success": False, "message": str(e)}

    def handle_failed_request(self, ip: str, url: str) -> Optional[Dict[str, bool]]:
        """Handle a failed request (e.g. 404) and potentially block the IP"""
        # CRITICAL: Check for internal IPs FIRST - before any other checks
        # If someone can access localhost, they're already on the server - blocking is pointless
        if self._is_internal_ip(ip):
            log_with_route(logging.DEBUG, f"INTERNAL IP PROTECTION: {ip} is localhost/internal, ignoring failed request to {url}")
            return {"success": False, "reason": "Internal IP - never blocked"}

        # Validate IP
        if not self._validate_ip(ip):
            log_with_route(logging.ERROR, f"Invalid IP from failed request: {ip}")
            return None

        # ENHANCED WHITELIST CHECK - check file first, then storage
        if self.is_whitelisted(ip):
            log_with_route(logging.INFO, f"WHITELIST PROTECTED: IP {ip} is whitelisted, ignoring 404 on {url}")
            return {"success": False, "reason": "IP is whitelisted"}

        # Check if already blacklisted - with immediate iptables check for race conditions
        if self.storage.sismember("wegweiser:ip_blocker:blacklist", ip):
            # Double-check iptables rule exists (in case of race condition)
            self._execute_iptables_command('-A', ip)  # Will fail silently if rule already exists
            return {"success": True, "reason": "IP already blocked"}

        try:
            now = int(time.time())
            # Create request data and storage keys
            request_data = {
                "timestamp": now,
                "url": url,
                "type": "failed_request"
            }
            history_key = f"wegweiser:ip_blocker:failed:{ip}:history"
            count_key = f"wegweiser:ip_blocker:failed:{ip}:count"
            
            # Update storage with request data - no expiry for faster processing
            self.storage.lpush(history_key, json.dumps(request_data))
            self.storage.ltrim(history_key, 0, 49)  # Keep last 50 requests
            error_count = self.storage.incr(count_key)
            
            log_with_route(logging.INFO, f"IP {ip} failed request count: {error_count}/{self.ERROR_THRESHOLD}")
            
            # Get current history
            try:
                raw_history = self.storage.lrange(history_key, 0, -1)
                history = [json.loads(entry) for entry in raw_history]
            except Exception:
                history = [request_data]
            
            # Handle threshold check
            if error_count >= self.ERROR_THRESHOLD:
                # One final whitelist check before blocking - defense in depth
                if self.is_whitelisted(ip):
                    log_with_route(logging.WARNING, f"Prevented blocking of whitelisted IP {ip} at the last moment")
                    return {"success": False, "reason": "IP is whitelisted (confirmed before blocking)"}
                    
                block_result = self.block_ip(ip)
                if block_result.get("success"):
                    block_data = {
                        "block_timestamp": str(now),
                        "block_reason": f"Failed request threshold exceeded ({error_count} failures)",
                        "block_trigger_url": url,
                        "request_history": json.dumps(history)
                    }
                    
                    self.storage.hmset(f"wegweiser:ip_blocker:blacklist_data:{ip}", block_data)
                    self.storage.delete(count_key)
                    
                    log_with_route(
                        logging.WARNING, 
                        f"Blocked IP {ip} after {error_count} failed requests. Trigger URL: {url}"
                    )
                return block_result
            
            return {
                "success": False,
                "reason": f"Warning {error_count}/{self.ERROR_THRESHOLD}",
                "current_history": history
            }
        except Exception as e:
            log_with_route(logging.ERROR, f"Storage error while handling failed request: {str(e)}")
            return {
                "success": False,
                "reason": f"Error tracking failed request: {str(e)}"
            }

    def _validate_ip(self, ip: str) -> bool:
        """Validate an IP address"""
        try:
            parts = ip.split('.')
            if len(parts) != 4:
                return False
            return all(0 <= int(part) <= 255 for part in parts)
        except (AttributeError, TypeError, ValueError):
            return False