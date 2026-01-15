#!/usr/bin/env python3
# Test script to debug persistent agent download and hash issues

import hashlib
import requests
import json
import os
import sys
from logzero import logger

def getSha256Hash(fileToHash):
    sha256Hash = hashlib.sha256()
    with open(fileToHash, 'rb') as f:
        for byteBlock in iter(lambda: f.read(4096), b""):
            sha256Hash.update(byteBlock)
    return sha256Hash.hexdigest()

def test_download_and_hash():
    """Test downloading the persistent agent and checking hashes"""
    
    # Default server
    host = 'app.wegweiser.tech'
    
    # If config exists, use that server
    config_file = '/opt/Wegweiser/Config/agent.config'
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            if 'serverAddr' in config:
                host = config['serverAddr']
        except Exception as e:
            logger.warning(f'Could not read config: {e}, using default server')
    
    logger.info(f'Testing with server: {host}')
    
    # Get server version info
    try:
        logger.info('Getting server version information...')
        r = requests.get(f'https://{host}/diags/persistentagentversion', timeout=30)
        r.raise_for_status()
        data = r.json()
        
        server_version = data['serverPersistentAgentVersion']
        server_hash = data['serverPersistentAgentHashPy']
        
        logger.info(f'Server version: {server_version}')
        logger.info(f'Server expected hash: {server_hash}')
        
    except Exception as e:
        logger.error(f'Failed to get server version info: {e}')
        return False
    
    # Download the file
    try:
        logger.info('Downloading persistent agent...')
        download_url = f'https://{host}/download/persistent_agent.py'
        temp_file = '/tmp/persistent_agent_test.py'
        
        r = requests.get(download_url, stream=True, timeout=60)
        r.raise_for_status()
        
        with open(temp_file, 'wb') as f:
            for chunk in r.iter_content(chunk_size=4096):
                if chunk:
                    f.write(chunk)
        
        file_size = os.path.getsize(temp_file)
        logger.info(f'Downloaded file size: {file_size} bytes')
        
        if file_size == 0:
            logger.error('Downloaded file is empty!')
            return False
            
    except Exception as e:
        logger.error(f'Failed to download file: {e}')
        return False
    
    # Calculate hash
    try:
        logger.info('Calculating hash of downloaded file...')
        actual_hash = getSha256Hash(temp_file)
        logger.info(f'Actual file hash: {actual_hash}')
        logger.info(f'Expected hash:    {server_hash}')
        
        if actual_hash == server_hash:
            logger.info('✅ HASH MATCH - Download is valid!')
            result = True
        else:
            logger.error('❌ HASH MISMATCH - Download may be corrupted or server info is outdated!')
            result = False
            
        # Show first few lines of the file for inspection
        try:
            with open(temp_file, 'r') as f:
                first_lines = [f.readline().strip() for _ in range(5)]
            logger.info('First 5 lines of downloaded file:')
            for i, line in enumerate(first_lines, 1):
                logger.info(f'  {i}: {line}')
        except Exception as e:
            logger.warning(f'Could not read file content: {e}')
        
        # Cleanup
        try:
            os.remove(temp_file)
        except Exception as e:
            logger.warning(f'Could not remove temp file: {e}')
            
        return result
        
    except Exception as e:
        logger.error(f'Failed to calculate hash: {e}')
        return False

if __name__ == '__main__':
    logger.info('=== Persistent Agent Download Test ===')
    success = test_download_and_hash()
    if success:
        logger.info('Test completed successfully - download should work')
        sys.exit(0)
    else:
        logger.error('Test failed - there may be server issues')
        sys.exit(1)
