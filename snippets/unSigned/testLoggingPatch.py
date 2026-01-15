"""
Snippet: Test Logging Patch - Simple test to find and verify agent.py
"""
import os
import sys
import platform

def get_logger():
    """Simple logging setup"""
    import logging
    logging.basicConfig(level=logging.INFO)
    return logging.getLogger(__name__)

logger = get_logger()

def main():
    """Main execution"""
    logger.info('[INFO] Starting logging patch test...')

    # Determine paths to check
    if platform.system() == 'Windows':
        possible_paths = [
            'c:\\program files (x86)\\Wegweiser\\Agent\\core\\agent.py',
            'C:\\ProgramData\\Wegweiser\\Agent\\core\\agent.py',
        ]
    else:
        possible_paths = [
            '/opt/Wegweiser/Agent/core/agent.py',
            '/opt/wegweiser/Agent/core/agent.py',
            '/usr/local/Wegweiser/Agent/core/agent.py',
            '/var/lib/Wegweiser/Agent/core/agent.py',
        ]

    agent_path = None
    for path in possible_paths:
        if os.path.isfile(path):
            agent_path = path
            logger.info(f'[OK] Found agent at: {agent_path}')
            break

    if not agent_path:
        logger.info('[ERROR] Agent not found in expected locations')
        logger.info(f'[INFO] Checked: {possible_paths}')
        return 1

    # Check if already patched
    try:
        with open(agent_path, 'r', encoding='utf-8') as f:
            content = f.read()

        if 'StructuredLogFormatter' in content:
            logger.info('[OK] StructuredLogFormatter already present')
            return 0
        else:
            logger.info('[INFO] StructuredLogFormatter NOT found')
            logger.info('[INFO] File exists and is readable, but formatter needs to be added')
            return 1
    except Exception as e:
        logger.error(f'[ERROR] Could not read agent file: {e}')
        return 1

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
