#!/usr/bin/env python3
"""
Test Update Snippet - Verifies update mechanism works
"""

import os
import platform
import logging
from datetime import datetime

# Configuration
agent_base_dir = os.environ.get('WEGWEISER_AGENT_DIR', '/opt/Wegweiser/Agent')
if platform.system() == 'Windows':
    agent_base_dir = os.environ.get('WEGWEISER_AGENT_DIR', 'C:\\Wegweiser\\Agent')

def get_logger():
    """Simple logging setup"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

logger = get_logger()

def main():
    """Test update mechanism"""
    logger.info("="*60)
    logger.info("TEST UPDATE SNIPPET EXECUTED")
    logger.info("="*60)
    logger.info(f"Platform: {platform.system()}")
    logger.info(f"Agent dir: {agent_base_dir}")
    logger.info(f"Agent dir exists: {os.path.exists(agent_base_dir)}")

    # Check if we can read nats_agent.py
    nats_agent_file = os.path.join(agent_base_dir, 'nats_agent.py')
    logger.info(f"Looking for: {nats_agent_file}")
    logger.info(f"File exists: {os.path.exists(nats_agent_file)}")

    if os.path.exists(nats_agent_file):
        try:
            with open(nats_agent_file, 'r') as f:
                first_line = f.readline()
                logger.info(f"[SUCCESS] First line: {first_line.strip()}")
        except Exception as e:
            logger.error(f"[FAILED] Failed to read file: {e}")
    else:
        logger.error(f"[FAILED] nats_agent.py NOT found")

    logger.info("Test update snippet completed")
    return True

if __name__ == '__main__':
    main()

