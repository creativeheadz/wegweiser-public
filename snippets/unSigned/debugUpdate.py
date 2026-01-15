#!/usr/bin/env python3
"""
Debug Update - Check what's happening with file replacement
"""

import os
import sys
import platform
import logging
import hashlib

# Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Determine agent directory
if platform.system() == 'Windows':
    agent_base_dir = r'C:\Program Files (x86)\Wegweiser\Agent'
else:
    agent_base_dir = '/opt/Wegweiser/Agent'

def get_file_info(filepath):
    """Get file info"""
    if not os.path.exists(filepath):
        return None
    
    try:
        stat = os.stat(filepath)
        with open(filepath, 'rb') as f:
            content_hash = hashlib.sha256(f.read()).hexdigest()
        
        return {
            'exists': True,
            'size': stat.st_size,
            'hash': content_hash[:16],
            'readable': os.access(filepath, os.R_OK),
            'writable': os.access(filepath, os.W_OK)
        }
    except Exception as e:
        return {'error': str(e)}

def main():
    """Debug update"""
    logger.info("="*60)
    logger.info("DEBUG UPDATE SCRIPT")
    logger.info("="*60)
    logger.info(f"Platform: {platform.system()}")
    logger.info(f"Agent base dir: {agent_base_dir}")
    logger.info(f"Agent dir exists: {os.path.exists(agent_base_dir)}")
    
    if not os.path.exists(agent_base_dir):
        logger.error(f"Agent directory does not exist!")
        return False
    
    # Check key files
    files_to_check = [
        'nats_agent.py',
        'core/nats_service.py',
        'core/agent.py',
        'core/api_client.py'
    ]
    
    logger.info("\nCurrent file status:")
    for filename in files_to_check:
        filepath = os.path.join(agent_base_dir, filename)
        info = get_file_info(filepath)
        
        if info is None:
            logger.info(f"  {filename}: NOT FOUND")
        elif 'error' in info:
            logger.info(f"  {filename}: ERROR - {info['error']}")
        else:
            logger.info(f"  {filename}: {info['size']} bytes, hash={info['hash']}, r={info['readable']}, w={info['writable']}")
    
    # Check for .new files
    logger.info("\nChecking for .new files (from previous updates):")
    for filename in files_to_check:
        new_filepath = os.path.join(agent_base_dir, f"{filename}.new")
        if os.path.exists(new_filepath):
            info = get_file_info(new_filepath)
            logger.info(f"  {filename}.new: EXISTS - {info['size']} bytes")
        else:
            logger.info(f"  {filename}.new: not found")
    
    # Check backup directory
    backup_dir = os.path.join(agent_base_dir, 'backup')
    logger.info(f"\nBackup directory: {backup_dir}")
    logger.info(f"Backup dir exists: {os.path.exists(backup_dir)}")
    
    if os.path.exists(backup_dir):
        try:
            backups = os.listdir(backup_dir)
            logger.info(f"Backup versions: {backups}")
        except Exception as e:
            logger.error(f"Error listing backups: {e}")
    
    # Check VERSION file
    version_file = os.path.join(agent_base_dir, 'VERSION')
    if os.path.exists(version_file):
        try:
            with open(version_file, 'r') as f:
                version = f.read().strip()
            logger.info(f"\nCurrent agent version: {version}")
        except Exception as e:
            logger.error(f"Error reading VERSION: {e}")
    else:
        logger.info(f"\nVERSION file not found")
    
    # Check directory permissions
    logger.info(f"\nDirectory permissions:")
    logger.info(f"  Agent dir readable: {os.access(agent_base_dir, os.R_OK)}")
    logger.info(f"  Agent dir writable: {os.access(agent_base_dir, os.W_OK)}")
    logger.info(f"  Agent dir executable: {os.access(agent_base_dir, os.X_OK)}")
    
    logger.info("\nDebug complete")
    return True

if __name__ == '__main__':
    main()

