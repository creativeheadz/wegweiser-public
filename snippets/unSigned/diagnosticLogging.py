"""
Snippet: Diagnostic Logging - Check agent logging setup and paths
"""
import os
import sys
import platform
import json

def get_logger():
    """Simple logging setup"""
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

logger = get_logger()

def find_agent_paths():
    """Find agent installation paths"""
    paths = {}

    if platform.system() == 'Windows':
        possible_paths = [
            'c:\\program files (x86)\\Wegweiser\\Agent',
            'C:\\Program Files\\Wegweiser\\Agent',
            'C:\\ProgramData\\Wegweiser\\Agent',
        ]
    else:
        possible_paths = [
            '/opt/Wegweiser/Agent',
            '/opt/wegweiser/Agent',
            '/usr/local/Wegweiser/Agent',
            '/var/lib/Wegweiser/Agent',
        ]

    for path in possible_paths:
        if os.path.isdir(path):
            paths['found'] = path
            paths['core_agent'] = os.path.join(path, 'core', 'agent.py')
            paths['core_agent_exists'] = os.path.isfile(paths['core_agent'])
            return paths

    paths['found'] = None
    return paths

def check_agent_formatter():
    """Check if agent has StructuredLogFormatter"""
    paths = find_agent_paths()

    logger.info('=== Agent Path Diagnostic ===')
    logger.info(f'Platform: {platform.system()}')
    logger.info(f'Agent directory found: {paths.get("found")}')

    if paths.get('core_agent_exists'):
        agent_path = paths['core_agent']
        logger.info(f'Agent file: {agent_path}')

        try:
            with open(agent_path, 'r', encoding='utf-8') as f:
                content = f.read()

            has_formatter = 'StructuredLogFormatter' in content
            logger.info(f'Has StructuredLogFormatter: {has_formatter}')

            if has_formatter:
                logger.info('[OK] Agent already has StructuredLogFormatter')
                return True
            else:
                logger.info('[INFO] Agent needs StructuredLogFormatter patch')
                return False
        except Exception as e:
            logger.error(f'Error reading agent file: {e}')
            return False
    else:
        logger.error('Agent directory not found')
        logger.error(f'Checked paths: {", ".join(possible_paths if platform.system() != "Windows" else ["C:\\Program Files*\\Wegweiser\\Agent"])}')
        return False

def main():
    """Main execution"""
    logger.info('Running diagnostic check...')

    has_formatter = check_agent_formatter()

    if has_formatter:
        logger.info('[OK] Logging formatter already applied')
        return 0
    else:
        logger.info('[INFO] Formatter not found - manual patching may be needed')
        return 1

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
