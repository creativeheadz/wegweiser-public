#!/usr/bin/env python3
"""
Update NATS Persistent Agent - v3.0.0+
Downloads and updates the NATS persistent agent with heartbeat functionality
Supports Windows, Linux, and macOS
"""

import hashlib
import json
import platform
import requests
import subprocess
import os
import sys
import shutil
import time
from pathlib import Path

# Configuration
host = os.environ.get('WEGWEISER_HOST', 'app.wegweiser.tech')

# Determine agent directory based on platform
if platform.system() == 'Windows':
    # Try Program Files (x86) first, then Program Files, then fallback
    agent_base_dir = os.environ.get('WEGWEISER_AGENT_DIR')
    if not agent_base_dir:
        if os.path.exists('C:\\Program Files (x86)\\Wegweiser\\Agent'):
            agent_base_dir = 'C:\\Program Files (x86)\\Wegweiser\\Agent'
        elif os.path.exists('C:\\Program Files\\Wegweiser\\Agent'):
            agent_base_dir = 'C:\\Program Files\\Wegweiser\\Agent'
        else:
            agent_base_dir = 'C:\\Program Files (x86)\\Wegweiser\\Agent'
else:
    agent_base_dir = os.environ.get('WEGWEISER_AGENT_DIR', '/opt/Wegweiser/Agent')

def get_logger():
    """Simple logging setup"""
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

logger = get_logger()
logger.info(f"[UPDATE] Agent directory: {agent_base_dir}")
logger.info(f"[UPDATE] Agent directory exists: {os.path.exists(agent_base_dir)}")

def get_server_nats_agent_version():
    """Get NATS agent version and hashes from server"""
    try:
        logger.info('Checking NATS agent version from server')
        url = f'https://{host}/diags/persistentagentversion'
        response = requests.get(url, timeout=10, verify=False)
        response.raise_for_status()
        data = response.json()
        
        if data.get('status') != 'success':
            logger.error(f"Server returned error: {data}")
            return None
        
        return {
            'version': data.get('persistent_agent_version'),
            'hash_py': data.get('persistent_agent_hash_py'),
            'hash_linux': data.get('persistent_agent_hash_linux'),
            'hash_macos': data.get('persistent_agent_hash_macos')
        }
    except Exception as e:
        logger.error(f"Failed to get server version: {e}")
        return None

def get_local_nats_agent_version():
    """Get local NATS agent version"""
    try:
        version_file = os.path.join(agent_base_dir, 'VERSION')
        if os.path.exists(version_file):
            with open(version_file, 'r') as f:
                return f.read().strip()
        # Fallback: check nats_agent.py for VERSION constant
        nats_agent_file = os.path.join(agent_base_dir, 'nats_agent.py')
        if os.path.exists(nats_agent_file):
            with open(nats_agent_file, 'r') as f:
                for line in f:
                    if 'VERSION' in line and '=' in line:
                        version = line.split('=')[1].strip().strip('"\'')
                        return version
        return '0.0.0'
    except Exception as e:
        logger.error(f"Failed to get local version: {e}")
        return '0.0.0'

def compare_versions(local_ver, server_ver):
    """Compare semantic versions"""
    try:
        local_parts = [int(x) for x in local_ver.split('.')]
        server_parts = [int(x) for x in server_ver.split('.')]
        return server_parts > local_parts
    except:
        return False

def get_sha256_hash(filepath):
    """Calculate SHA256 hash of file"""
    sha256_hash = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def download_file(url, save_path):
    """Download file from URL"""
    try:
        logger.info(f"Downloading {url}")
        response = requests.get(url, stream=True, timeout=30, verify=False)
        response.raise_for_status()
        
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        logger.info(f"Downloaded to {save_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to download {url}: {e}")
        return False

def update_nats_agent(server_info):
    """Update NATS agent files"""
    try:
        system = platform.system()
        logger.info(f"[UPDATE] Starting NATS agent update on {system}")
        logger.info(f"[UPDATE] Agent base directory: {agent_base_dir}")
        logger.info(f"[UPDATE] Agent base dir exists: {os.path.exists(agent_base_dir)}")

        # Determine platform and hash
        if system == 'Windows':
            platform_name = 'Windows'
            expected_hash = server_info['hash_py']
        elif system == 'Linux':
            platform_name = 'Linux'
            expected_hash = server_info['hash_linux']
        elif system == 'Darwin':
            platform_name = 'MacOS'
            expected_hash = server_info['hash_macos']
        else:
            logger.error(f"[UPDATE] Unsupported platform: {system}")
            return False

        logger.info(f"[UPDATE] Platform: {platform_name}, Expected hash: {expected_hash}")

        # Create backup directory
        backup_dir = os.path.join(agent_base_dir, 'backup', server_info['version'])
        logger.info(f"[UPDATE] Creating backup directory: {backup_dir}")
        os.makedirs(backup_dir, exist_ok=True)
        logger.info(f"[UPDATE] Backup directory ready")

        # Files to update
        files_to_update = [
            'nats_agent.py',
            'core/nats_service.py',
            'core/agent.py',
            'core/api_client.py'
        ]

        # Download and verify each file
        for filename in files_to_update:
            logger.info(f"[UPDATE] Processing file: {filename}")
            url = f"https://{host}/installerFiles/{platform_name}/Agent/{filename}"
            temp_path = os.path.join(agent_base_dir, f"{filename}.new")

            logger.info(f"[UPDATE] Download URL: {url}")
            logger.info(f"[UPDATE] Temp path: {temp_path}")

            # Create directory if needed
            temp_dir = os.path.dirname(temp_path)
            logger.info(f"[UPDATE] Creating temp directory: {temp_dir}")
            os.makedirs(temp_dir, exist_ok=True)

            if not download_file(url, temp_path):
                logger.error(f"[UPDATE] Failed to download {filename}")
                return False

            logger.info(f"[UPDATE] Downloaded {filename}, verifying...")

            # Verify hash for main file
            if filename == 'nats_agent.py':
                file_hash = get_sha256_hash(temp_path)
                logger.info(f"[UPDATE] File hash: {file_hash}")
                logger.info(f"[UPDATE] Expected hash: {expected_hash}")
                if file_hash != expected_hash:
                    logger.error(f"[UPDATE] Hash mismatch for {filename}: {file_hash} != {expected_hash}")
                    os.remove(temp_path)
                    return False
                logger.info(f"[UPDATE] Hash verified for {filename}")
        
        # Backup current files
        for filename in files_to_update:
            src = os.path.join(agent_base_dir, filename)
            if os.path.exists(src):
                dst = os.path.join(backup_dir, filename)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
                logger.info(f"Backed up {filename}")
        
        # Replace files
        for filename in files_to_update:
            temp_path = os.path.join(agent_base_dir, f"{filename}.new")
            target_path = os.path.join(agent_base_dir, filename)

            logger.info(f"[REPLACE] Processing {filename}")
            logger.info(f"[REPLACE] Temp path: {temp_path}")
            logger.info(f"[REPLACE] Target path: {target_path}")
            logger.info(f"[REPLACE] Temp exists: {os.path.exists(temp_path)}")
            logger.info(f"[REPLACE] Target exists: {os.path.exists(target_path)}")

            if os.path.exists(temp_path):
                try:
                    logger.info(f"[REPLACE] Attempting to move {temp_path} to {target_path}")

                    # Check if target exists and try to remove it first
                    if os.path.exists(target_path):
                        logger.info(f"[REPLACE] Target exists, attempting to remove it first")
                        try:
                            os.remove(target_path)
                            logger.info(f"[REPLACE] Successfully removed old {filename}")
                        except Exception as e:
                            logger.error(f"[REPLACE] Failed to remove old {filename}: {e}")
                            return False

                    # Now move the new file
                    shutil.move(temp_path, target_path)
                    logger.info(f"[REPLACE] Successfully moved {temp_path} to {target_path}")
                    logger.info(f"[REPLACE] Verifying file exists at target: {os.path.exists(target_path)}")

                except Exception as e:
                    logger.error(f"[REPLACE] Failed to replace {filename}: {e}")
                    logger.error(f"[REPLACE] Exception type: {type(e).__name__}")
                    return False
            else:
                logger.error(f"[REPLACE] Temp file not found: {temp_path}")
                return False

        # Write version file
        version_file = os.path.join(agent_base_dir, 'VERSION')
        with open(version_file, 'w') as f:
            f.write(server_info['version'])
        logger.info(f"[SUCCESS] Wrote VERSION file: {version_file}")

        logger.info(f"[SUCCESS] NATS agent updated to {server_info['version']}")
        return True
        
    except Exception as e:
        logger.error(f"Update failed: {e}")
        return False

def update_server_public_key():
    """Update server public key in agent config"""
    try:
        logger.info("Updating server public key in agent config")

        # Get config file path
        system = platform.system()
        if system == 'Windows':
            config_dir = 'C:\\Wegweiser\\Config'
        else:
            config_dir = '/opt/Wegweiser/Config'

        config_file = os.path.join(config_dir, 'agent.config')

        if not os.path.exists(config_file):
            logger.warning(f"Config file not found: {config_file}")
            return False

        # Read current config
        with open(config_file, 'r') as f:
            config = json.load(f)

        # Get new server public key from server
        try:
            url = f'https://{host}/diags/serverpubkey'
            response = requests.get(url, timeout=10, verify=False)
            response.raise_for_status()
            data = response.json()
            new_pubkey = data.get('serverpubpem')

            if new_pubkey:
                config['serverpubpem'] = new_pubkey

                # Write updated config
                with open(config_file, 'w') as f:
                    json.dump(config, f, indent=2)

                logger.info("Server public key updated successfully")
                return True
            else:
                logger.warning("Server did not return public key")
                return False
        except Exception as e:
            logger.warning(f"Failed to fetch new server public key: {e}")
            # Continue anyway - old key might still work
            return True

    except Exception as e:
        logger.error(f"Failed to update server public key: {e}")
        return False

def restart_nats_agent():
    """Restart NATS agent service"""
    try:
        system = platform.system()

        if system == 'Windows':
            # Restart Windows service
            subprocess.run(['net', 'stop', 'WegweiserServiceHost'], check=False)
            time.sleep(2)
            subprocess.run(['net', 'start', 'WegweiserServiceHost'], check=False)
            logger.info("Restarted WegweiserServiceHost")
        else:
            # Restart systemd service
            subprocess.run(['sudo', 'systemctl', 'restart', 'wegweiser-persistent-agent'], check=False)
            logger.info("Restarted wegweiser-persistent-agent")

        return True
    except Exception as e:
        logger.error(f"Failed to restart agent: {e}")
        return False

def main():
    """Main update logic"""
    logger.info("Starting NATS agent update check")

    # Update server public key first (for signature verification)
    update_server_public_key()

    # Get versions
    local_version = get_local_nats_agent_version()
    server_info = get_server_nats_agent_version()

    if not server_info:
        logger.error("Failed to get server version info")
        sys.exit(1)

    logger.info(f"Local version: {local_version}")
    logger.info(f"Server version: {server_info['version']}")

    # Check if update needed
    if not compare_versions(local_version, server_info['version']):
        logger.info("NATS agent is up to date")
        sys.exit(0)

    logger.info("NATS agent update required")

    # Perform update
    if not update_nats_agent(server_info):
        logger.error("Update failed")
        sys.exit(1)

    # Write VERSION file to mark successful update
    try:
        version_file = os.path.join(agent_base_dir, 'VERSION')
        with open(version_file, 'w') as f:
            f.write(server_info['version'])
        logger.info(f"Wrote VERSION file: {version_file}")
    except Exception as e:
        logger.warning(f"Failed to write VERSION file: {e}")

    # Restart agent
    if not restart_nats_agent():
        logger.warning("Failed to restart agent (may restart on next cycle)")

    logger.info("NATS agent update completed successfully")
    sys.exit(0)

if __name__ == '__main__':
    main()

