"""
Snippet: Update Agent Logging Configuration
Updates agent logging to use structured, columnar format with proper indentation
"""
import json
import os
import sys
import logging
import time
from logzero import logger

# Global variables
debug_mode = False

class StructuredLogFormatter(logging.Formatter):
    """Custom formatter with structured columns and color support"""
    
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    LEVEL_WIDTH = 8
    MODULE_WIDTH = 30
    
    def format(self, record):
        """Format log record with structured columns"""
        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        level = record.levelname
        
        is_terminal = sys.stdout.isatty() if hasattr(sys.stdout, 'isatty') else False
        if is_terminal:
            colored_level = f"{self.COLORS.get(level, '')}{level:<{self.LEVEL_WIDTH}}{self.COLORS['RESET']}"
        else:
            colored_level = f"{level:<{self.LEVEL_WIDTH}}"
        
        module = record.name
        formatted_module = f"{module:<{self.MODULE_WIDTH}}"
        message = record.getMessage()
        
        if record.exc_info:
            message += f"\n{self.formatException(record.exc_info)}"
        
        log_line = (
            f"{timestamp} | "
            f"{colored_level} | "
            f"{formatted_module} | "
            f"{message}"
        )
        
        return log_line


def get_app_dirs():
    """Setup application directories based on OS platform"""
    import platform
    if platform.system() == 'Windows':
        app_dir = 'c:\\program files (x86)\\Wegweiser\\'
        log_dir = f'{app_dir}Logs\\'
        config_dir = f'{app_dir}Config\\'
    else:
        app_dir = '/opt/Wegweiser/'
        log_dir = f'{app_dir}Logs/'
        config_dir = f'{app_dir}Config/'
    
    return app_dir, log_dir, config_dir


def check_dir(dir_to_check):
    """Create directory if it doesn't exist"""
    dir_to_check = os.path.join(dir_to_check, '')
    if not os.path.isdir(dir_to_check):
        logger.info(f'{dir_to_check} does not exist. Creating...')
        try:
            os.makedirs(dir_to_check)
            logger.info(f'{dir_to_check} created.')
        except Exception as e:
            logger.error(f'Failed to create {dir_to_check}. Reason: {e}')
            return False
    return True


def update_logging_config():
    """Update agent logging configuration"""
    try:
        app_dir, log_dir, config_dir = get_app_dirs()
        check_dir(log_dir)
        
        # Read current config
        config_file = os.path.join(config_dir, 'agent.config')
        if not os.path.isfile(config_file):
            logger.error(f'Agent config not found at {config_file}')
            return False
        
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        # Add logging configuration
        current_time = int(time.time())
        config['logging'] = {
            'format': 'structured',
            'level': 'DEBUG' if debug_mode else 'INFO',
            'formatter': 'StructuredLogFormatter',
            'color_enabled': True,
            'updated_at': current_time
        }
        
        # Write updated config
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info('[OK] Logging configuration updated successfully')
        logger.info('[OK] Format: Structured columns with indentation')
        logger.info('[OK] Color: Enabled')
        logger.info('[OK] Level: %s', config["logging"]["level"])
        return True
        
    except Exception as e:
        logger.error(f'Failed to update logging config: {e}')
        return False


def main():
    """Main execution"""
    logger.info('Updating agent logging configuration...')
    
    success = update_logging_config()
    
    if success:
        logger.info('Logging configuration update completed successfully')
        return 0
    else:
        logger.error('Failed to update logging configuration')
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
