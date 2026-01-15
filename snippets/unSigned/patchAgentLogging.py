"""
Snippet: Patch Agent Logging - Inject StructuredLogFormatter into agent.py
This snippet patches the agent.py file to use structured columnar logging format
"""
import os
import sys
import platform
from pathlib import Path

# Global variables
debug_mode = False

def get_agent_core_path():
    """Get the path to the agent core directory based on OS platform"""
    if platform.system() == 'Windows':
        possible_paths = [
            'c:\\program files (x86)\\Wegweiser\\Agent\\core',
            'c:\\Wegweiser\\Agent\\core',
            'c:\\ProgramData\\Wegweiser\\Agent\\core',
        ]
    else:
        possible_paths = [
            '/opt/Wegweiser/Agent/core',
            '/opt/wegweiser/Agent/core',
            '/opt/Wegweiser/Agent/core',
            '/usr/local/Wegweiser/Agent/core',
            '/var/lib/Wegweiser/Agent/core',
            '/home/*/Wegweiser/Agent/core',
        ]

    for path in possible_paths:
        if os.path.isdir(path):
            return path

    # If no installation found, return None
    return None

def get_formatted_logging_code():
    """Return the StructuredLogFormatter class definition and updated _setup_logging method"""

    formatter_class = '''
class StructuredLogFormatter(logging.Formatter):
    """Custom formatter with structured columns and color support"""

    COLORS = {
        'DEBUG': '\\033[36m',      # Cyan
        'INFO': '\\033[32m',       # Green
        'WARNING': '\\033[33m',    # Yellow
        'ERROR': '\\033[31m',      # Red
        'CRITICAL': '\\033[35m',   # Magenta
        'RESET': '\\033[0m'        # Reset
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
            message += f"\\n{self.formatException(record.exc_info)}"

        log_line = (
            f"{timestamp} | "
            f"{colored_level} | "
            f"{formatted_module} | "
            f"{message}"
        )

        return log_line

'''

    setup_logging_method = '''    def _setup_logging(self):
        """Setup logging with structured formatter"""
        log_level = logging.DEBUG if self.debug else logging.INFO

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)

        # File handler
        log_file = self.config.log_dir / 'agent.log'
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)

        # Formatter - use StructuredLogFormatter for aligned columns
        formatter = StructuredLogFormatter()
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        # Root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)

        logger.info(f"Wegweiser Agent {self.VERSION} started")
        logger.info(f"Platform: {platform.system()} {platform.release()}")
'''

    return formatter_class, setup_logging_method

def patch_agent_logging():
    """Patch agent.py to use StructuredLogFormatter"""

    try:
        agent_core_path = get_agent_core_path()
        if not agent_core_path:
            print('[ERROR] Could not locate agent core directory')
            return False

        agent_py_path = os.path.join(agent_core_path, 'agent.py')
        if not os.path.isfile(agent_py_path):
            print(f'[ERROR] agent.py not found at {agent_py_path}')
            return False

        # Read the original file
        with open(agent_py_path, 'r', encoding='utf-8') as f:
            original_content = f.read()

        # Check if already patched
        if 'StructuredLogFormatter' in original_content:
            print('[INFO] Agent already patched with StructuredLogFormatter')
            return True

        # Get the new code
        formatter_class, setup_logging_method = get_formatted_logging_code()

        # Find the insertion point - after the logger = logging.getLogger(__name__) line
        logger_line = 'logger = logging.getLogger(__name__)'
        if logger_line not in original_content:
            print('[ERROR] Could not find logger initialization in agent.py')
            return False

        # Find where to insert the class (after logger definition, before class WegweiserAgent)
        insert_pos = original_content.find(logger_line)
        insert_pos = original_content.find('\n', insert_pos) + 1

        # Insert the StructuredLogFormatter class
        patched_content = (
            original_content[:insert_pos] +
            formatter_class +
            original_content[insert_pos:]
        )

        # Find and replace the _setup_logging method
        # Look for "def _setup_logging(self):" and find the entire method
        method_start = patched_content.find('    def _setup_logging(self):')
        if method_start == -1:
            print('[ERROR] Could not find _setup_logging method')
            return False

        # Find the end of the method (next method or end of class)
        method_end = patched_content.find('\n    def ', method_start + 1)
        if method_end == -1:
            # It might be the last method, search for next async def or class
            method_end = patched_content.find('\n    async def ', method_start + 1)

        if method_end == -1:
            print('[ERROR] Could not find end of _setup_logging method')
            return False

        # Replace the method
        patched_content = (
            patched_content[:method_start] +
            setup_logging_method +
            patched_content[method_end:]
        )

        # Write the patched file back
        with open(agent_py_path, 'w', encoding='utf-8') as f:
            f.write(patched_content)

        print(f'[OK] Successfully patched agent.py at {agent_py_path}')
        print('[OK] StructuredLogFormatter class injected')
        print('[OK] _setup_logging method updated to use new formatter')
        print('[INFO] Agent will use structured columnar format after restart')

        return True

    except Exception as e:
        print(f'[ERROR] Failed to patch agent logging: {e}')
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main execution"""
    print('[INFO] Starting agent logging formatter patch...')

    success = patch_agent_logging()

    if success:
        print('[OK] Agent logging patch completed successfully')
        print('[INFO] Please restart the agent to apply the new logging format')
        return 0
    else:
        print('[ERROR] Failed to patch agent logging')
        return 1

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
