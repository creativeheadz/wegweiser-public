#!/usr/bin/env python3
"""
Standalone Device Registration Script
Simplified registration without full agent initialization
"""

import sys
import os
import json
import socket
import platform
import argparse
import logging
from pathlib import Path

# Add current directory to path so core module can be imported
agent_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, agent_dir)

from core.config import ConfigManager
from core.crypto import CryptoManager
from core.api_client import APIClient

# Setup logging to both console and file
from datetime import datetime

# Determine log directory based on platform
if platform.system() == 'Windows':
    log_dir = Path('C:/Program Files (x86)/Wegweiser/Logs')
else:
    log_dir = Path('/opt/Wegweiser/Logs')

# Create log directory if it doesn't exist
try:
    log_dir.mkdir(parents=True, exist_ok=True)
except Exception as e:
    # Fallback to current directory if we can't create the log directory
    log_dir = Path('.')

log_file = log_dir / f'registration_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'

# Create formatters and handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

file_handler = logging.FileHandler(str(log_file))
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

# Configure root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

logger = logging.getLogger(__name__)


def register_device(group_uuid: str, server_addr: str, config_path: str = None):
    """Register device with server"""
    logger.info("=" * 80)
    logger.info("DEVICE REGISTRATION STARTED")
    logger.info("=" * 80)
    logger.info(f"Group UUID: {group_uuid}")
    logger.info(f"Server Address: {server_addr}")
    logger.info(f"Config Path: {config_path}")
    logger.info(f"Platform: {platform.system()} {platform.release()}")
    logger.info(f"Hostname: {socket.gethostname()}")
    
    try:
        # Initialize config manager
        logger.info("\n[1/6] Initializing configuration manager...")
        config = ConfigManager(config_path)
        logger.info(f"Config file path: {config.config_path}")
        logger.info(f"Base directory: {config.base_dir}")
        
        # Initialize crypto manager
        logger.info("\n[2/6] Initializing crypto manager...")
        crypto = CryptoManager()
        
        # Generate keypair
        logger.info("\n[3/6] Generating RSA keypair (4096-bit)...")
        private_pem, public_pem = crypto.generate_keypair()
        logger.info(f"Private key length: {len(private_pem)} chars")
        logger.info(f"Public key length: {len(public_pem)} chars")
        
        # Initialize API client
        logger.info("\n[4/6] Initializing API client...")
        api = APIClient(server_addr)
        logger.info(f"API client initialized for: https://{server_addr}")
        
        # Get server public key
        logger.info("\n[5/6] Fetching server public key...")
        try:
            server_pub_pem = api.get_server_public_key()
            logger.info(f"Server public key fetched successfully ({len(server_pub_pem)} chars)")
        except Exception as e:
            logger.error(f"Failed to fetch server public key: {e}")
            logger.error("This usually means the server is unreachable or not responding correctly")
            return False
        
        # Register device
        logger.info("\n[6/6] Registering device with server...")
        try:
            device_uuid = api.register_device(
                group_uuid=group_uuid,
                device_name=socket.gethostname(),
                hardware_info=platform.system(),
                agent_pub_pem=public_pem
            )
            logger.info(f"Device registered successfully!")
            logger.info(f"Device UUID: {device_uuid}")
        except Exception as e:
            logger.error(f"Failed to register device: {e}")
            logger.error("This usually means the group UUID is invalid or the server rejected the registration")
            return False
        
        # Save configuration
        logger.info("\nSaving configuration...")
        config.set('deviceuuid', device_uuid)
        config.set('agentprivpem', private_pem)
        config.set('agentpubpem', public_pem)
        config.set('serverpubpem', server_pub_pem)
        config.set('serverAddr', server_addr)
        
        if not config.save():
            logger.error("Failed to save configuration")
            return False
        
        logger.info(f"Configuration saved to: {config.config_path}")
        
        # Verify configuration file exists
        if Path(config.config_path).exists():
            logger.info(f"✓ Configuration file verified at: {config.config_path}")
            with open(config.config_path, 'r') as f:
                saved_config = json.load(f)
                logger.info(f"✓ Saved device UUID: {saved_config.get('deviceuuid', 'N/A')}")
        else:
            logger.error(f"✗ Configuration file not found at: {config.config_path}")
            return False
        
        logger.info("\n" + "=" * 80)
        logger.info("DEVICE REGISTRATION COMPLETED SUCCESSFULLY")
        logger.info("=" * 80)
        return True
    
    except Exception as e:
        logger.error(f"\nFATAL ERROR: {e}")
        import traceback
        logger.error(traceback.format_exc())
        logger.info("\n" + "=" * 80)
        logger.info("DEVICE REGISTRATION FAILED")
        logger.info("=" * 80)
        return False


if __name__ == '__main__':
    try:
        logger.info(f"Registration log file: {log_file}")
        logger.info(f"Log directory: {log_dir}")

        parser = argparse.ArgumentParser(description='Wegweiser Device Registration')
        parser.add_argument('-g', '--groupUuid', required=True, help='Group UUID')
        parser.add_argument('-s', '--serverAddr', required=True, help='Server address')
        parser.add_argument('-c', '--config', help='Config file path (optional)')

        args = parser.parse_args()

        logger.info(f"Arguments parsed successfully")
        logger.info(f"  Group UUID: {args.groupUuid}")
        logger.info(f"  Server Address: {args.serverAddr}")
        logger.info(f"  Config Path: {args.config}")

        success = register_device(args.groupUuid, args.serverAddr, args.config)

        if success:
            logger.info(f"Registration completed successfully. Log file: {log_file}")
        else:
            logger.error(f"Registration failed. Check log file: {log_file}")

        sys.exit(0 if success else 1)

    except Exception as e:
        logger.error(f"Fatal error in main: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

