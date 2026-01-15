#!/usr/bin/env python3
"""
Debug Update 2 - Write directly to file
"""

import os
import sys
import platform
import hashlib

# Determine agent directory
if platform.system() == 'Windows':
    agent_base_dir = r'C:\Program Files (x86)\Wegweiser\Agent'
    log_file = r'C:\Program Files (x86)\Wegweiser\Logs\debugUpdate.txt'
else:
    agent_base_dir = '/opt/Wegweiser/Agent'
    log_file = '/opt/Wegweiser/Logs/debugUpdate.txt'

def write_log(msg):
    """Write to log file"""
    try:
        with open(log_file, 'a') as f:
            f.write(msg + '\n')
        print(msg)
    except Exception as e:
        print(f"Error writing log: {e}")

def get_file_info(filepath):
    """Get file info"""
    if not os.path.exists(filepath):
        return "NOT_FOUND"
    
    try:
        stat = os.stat(filepath)
        with open(filepath, 'rb') as f:
            content_hash = hashlib.sha256(f.read()).hexdigest()[:16]
        
        readable = "R" if os.access(filepath, os.R_OK) else "-"
        writable = "W" if os.access(filepath, os.W_OK) else "-"
        
        return f"SIZE={stat.st_size} HASH={content_hash} PERMS={readable}{writable}"
    except Exception as e:
        return f"ERROR: {str(e)}"

def main():
    """Debug update"""
    write_log("="*60)
    write_log("DEBUG UPDATE 2")
    write_log("="*60)
    write_log(f"Platform: {platform.system()}")
    write_log(f"Agent base dir: {agent_base_dir}")
    write_log(f"Agent dir exists: {os.path.exists(agent_base_dir)}")
    
    if not os.path.exists(agent_base_dir):
        write_log("ERROR: Agent directory does not exist!")
        return False
    
    # Check key files
    files_to_check = [
        'nats_agent.py',
        'core/nats_service.py',
        'core/agent.py',
        'core/api_client.py'
    ]
    
    write_log("\nCurrent file status:")
    for filename in files_to_check:
        filepath = os.path.join(agent_base_dir, filename)
        info = get_file_info(filepath)
        write_log(f"  {filename}: {info}")
    
    # Check for .new files
    write_log("\nChecking for .new files:")
    for filename in files_to_check:
        new_filepath = os.path.join(agent_base_dir, f"{filename}.new")
        if os.path.exists(new_filepath):
            info = get_file_info(new_filepath)
            write_log(f"  {filename}.new: {info}")
    
    # Check VERSION file
    version_file = os.path.join(agent_base_dir, 'VERSION')
    if os.path.exists(version_file):
        try:
            with open(version_file, 'r') as f:
                version = f.read().strip()
            write_log(f"\nCurrent agent version: {version}")
        except Exception as e:
            write_log(f"Error reading VERSION: {e}")
    else:
        write_log(f"\nVERSION file not found")
    
    # Check directory permissions
    write_log(f"\nDirectory permissions:")
    write_log(f"  Readable: {os.access(agent_base_dir, os.R_OK)}")
    write_log(f"  Writable: {os.access(agent_base_dir, os.W_OK)}")
    write_log(f"  Executable: {os.access(agent_base_dir, os.X_OK)}")
    
    write_log("\nDebug complete")
    return True

if __name__ == '__main__':
    main()

