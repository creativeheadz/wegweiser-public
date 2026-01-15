# IP Blocker Documentation

## Overview

The IP Blocker system is designed to protect the Wegweiser application by automatically detecting and blocking IP addresses that exhibit suspicious behavior, such as repeatedly triggering 404 errors. It integrates with the Flask application and uses iptables for enforcing IP blocking at the network level.

## Architecture

The system consists of two main components:

1. **LMDBStorage**: A persistent key-value storage adapter with Redis-like interface backed by Lightning Memory-Mapped Database (LMDB).

2. **IPBlocker**: The main class that handles detecting suspicious activity, managing whitelists/blacklists, and executing iptables commands to block IPs.

## Whitelist Management

### Whitelist Sources

The IP Blocker uses two sources for managing whitelisted IPs, in order of priority:

1. **whitelist.json file** (Primary/Authoritative Source)
   - Located at: `app/data/ip_blocker/whitelist.json`
   - Contains a JSON array of IP addresses
   - Example: `["81.150.150.132", "109.100.115.135"]`

2. **LMDB Storage** (Secondary Source)
   - Used for runtime operation and persistence
   - Synchronized from the whitelist.json file during initialization

### How Whitelist Checking Works

When determining if an IP is whitelisted:

1. The system first checks the whitelist.json file directly
2. If not found in the file, it checks the LMDB storage
3. If found in either location, the IP is considered whitelisted

This ensures that updates to the whitelist.json file are immediately effective without requiring an application restart.

### Whitelist Synchronization

During IPBlocker initialization, the whitelist.json file is synchronized to LMDB storage:
- IPs in the file but not in storage are added to storage
- IPs in storage but not in the file are kept by default (optional behavior)

## Configuration

The IP Blocker can be configured via environment variables or Flask application config:

| Configuration Key | Default Value | Description |
|------------------|---------------|-------------|
| IP_BLOCKER_DATA_DIR | app/data/ip_blocker | Directory for IP blocker data storage |
| IP_BLOCKER_LMDB_MAP_SIZE | 10485760 (10MB) | Max size of LMDB database |
| ERROR_THRESHOLD | 2 | Number of failed requests before an IP is blocked |

## Failed Request Handling

When a 404 error occurs:

1. The application captures the client's IP address
2. The IP is validated
3. The system checks if the IP is whitelisted (from file then storage)
4. If whitelisted, no action is taken
5. If not whitelisted and not already blocked:
   - The request is recorded in the IP's history
   - The error count for the IP is incremented
   - If the error count exceeds the threshold (default: 2):
     - One final whitelist check is performed
     - If not whitelisted, the IP is added to the blacklist and blocked via iptables

## Blocking and Unblocking IPs

### Blocking Process

When an IP is blocked:
1. It's added to the blacklist in LMDB storage
2. Block information (timestamp, reason) is recorded
3. An iptables rule is added to drop all packets from the IP

### Unblocking Process

To unblock an IP:
1. It's removed from the blacklist in LMDB storage
2. Associated block data is deleted
3. The corresponding iptables rule is removed

## API Reference

### Key Methods

| Method | Description |
|--------|-------------|
| `is_whitelisted(ip)` | Checks if an IP is whitelisted (using file first, then storage) |
| `block_ip(ip)` | Blocks an IP address (adds to blacklist and iptables) |
| `unblock_ip(ip)` | Unblocks an IP address |
| `add_to_whitelist(ip)` | Adds an IP to the whitelist in storage |
| `remove_from_whitelist(ip)` | Removes an IP from the whitelist in storage |
| `get_lists()` | Returns the current whitelist and blacklist |
| `handle_failed_request(ip, url)` | Records a failed request and potentially blocks the IP |

## Maintenance Tasks

### Adding IPs to Whitelist

To add IPs to the whitelist, edit the `app/data/ip_blocker/whitelist.json` file and add the IP to the JSON array. The change will be effective immediately for whitelist checks.

### Manual Whitelist Synchronization

Although not normally required, to manually sync the whitelist.json file to storage:

```python
from app.utilities.ip_blocker import IPBlocker
blocker = IPBlocker()
blocker._sync_whitelist_to_storage()
```

### Checking Current Lists

To view currently blocked and whitelisted IPs:

```python
from app.utilities.ip_blocker import IPBlocker
blocker = IPBlocker()
lists = blocker.get_lists()
print("Whitelisted IPs:", lists["whitelist"])
print("Blocked IPs:", lists["blacklist"])
```

### Direct Iptables Management

If you need to manually manage iptables rules:

```bash
# List all rules
sudo iptables -L INPUT -v -n

# Remove a rule for a specific IP
sudo iptables -D INPUT -s <ip_address> -j DROP
```

## Troubleshooting

### Diagnosing LMDB Storage

For issues with the LMDB storage, you can use the included diagnostic tool:

```bash
cd ~/wegweiser/app/data/ip_blocker
python lmdb_diagnose.py
```

### Common Issues

1. **IP Blocked Despite Being Whitelisted**
   - Check if the IP is in whitelist.json
   - Verify file permissions allow the application to read the whitelist.json file
   - Check iptables rules directly with `sudo iptables -L INPUT -v -n | grep <ip>`

2. **Application Error During IP Blocker Operation**
   - Check application logs for errors
   - Verify the LMDB storage directory exists and has correct permissions
   - Ensure the application has sudo privileges to execute iptables commands

## Best Practices

1. Always update the whitelist.json file rather than only adding IPs to storage
2. Consider increasing the ERROR_THRESHOLD for production environments to avoid blocking legitimate users
3. Regularly review the blocked IPs list for false positives
4. Create a maintenance script to clean up old LMDB data if disk space becomes a concern