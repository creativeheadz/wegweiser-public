"""
Snippet: Apply Logging Formatter - Direct code injection approach
Applies StructuredLogFormatter to agent logging by directly modifying _setup_logging
"""
import os
import sys
import platform

# Global variables
debug_mode = False

def find_agent_py():
    """Find agent.py in common installation paths"""
    if platform.system() == 'Windows':
        possible_paths = [
            'c:\\program files (x86)\\Wegweiser\\Agent\\core\\agent.py',
            'c:\\ProgramData\\Wegweiser\\Agent\\core\\agent.py',
            'C:\\Wegweiser\\Agent\\core\\agent.py',
        ]
    else:
        possible_paths = [
            '/opt/Wegweiser/Agent/core/agent.py',
            '/opt/wegweiser/Agent/core/agent.py',
            '/usr/local/Wegweiser/Agent/core/agent.py',
            '/var/lib/Wegweiser/Agent/core/agent.py',
            '/home/agent/Wegweiser/Agent/core/agent.py',
        ]

    for path in possible_paths:
        if os.path.isfile(path):
            return path
    return None

def has_structured_formatter(content):
    """Check if StructuredLogFormatter is already in the code"""
    return 'StructuredLogFormatter' in content

def apply_formatter(agent_py_path):
    """Apply StructuredLogFormatter to agent.py"""
    try:
        # Read the file
        with open(agent_py_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check if already applied
        if has_structured_formatter(content):
            print('[INFO] StructuredLogFormatter already applied')
            return True

        # Insert the formatter class after logger definition
        formatter_class = '''
class StructuredLogFormatter(logging.Formatter):
    """Custom formatter with structured aligned columns"""

    LEVEL_WIDTH = 8
    MODULE_WIDTH = 30

    def format(self, record):
        """Format log record with structured aligned columns"""
        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        level = record.levelname

        # Pad level to fixed width for column alignment
        formatted_level = f"{level:<{self.LEVEL_WIDTH}}"

        module = record.name
        formatted_module = f"{module:<{self.MODULE_WIDTH}}"
        message = record.getMessage()

        if record.exc_info:
            message += f"\\n{self.formatException(record.exc_info)}"

        log_line = (
            f"{timestamp} | "
            f"{formatted_level} | "
            f"{formatted_module} | "
            f"{message}"
        )

        return log_line

'''

        # Find insertion point
        logger_line = 'logger = logging.getLogger(__name__)'
        if logger_line not in content:
            print('[ERROR] Could not find logger initialization')
            return False

        insert_pos = content.find(logger_line) + len(logger_line)
        insert_pos = content.find('\n\n', insert_pos)

        # Insert formatter class
        content = content[:insert_pos] + '\n' + formatter_class + content[insert_pos:]

        # Replace the formatter initialization in _setup_logging
        old_formatter = "formatter = logging.Formatter(\n            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'\n        )"
        new_formatter = "formatter = StructuredLogFormatter()"

        if old_formatter in content:
            content = content.replace(old_formatter, new_formatter)
        else:
            print('[INFO] Formatter line not found in original format, trying alternative')
            if "logging.Formatter(" in content:
                content = content.replace(
                    "formatter = logging.Formatter(",
                    "# Using StructuredLogFormatter\n        formatter = StructuredLogFormatter() if True else logging.Formatter("
                )
            else:
                print('[ERROR] Could not find formatter initialization')
                return False

        # Write back
        with open(agent_py_path, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f'[OK] Applied StructuredLogFormatter to {agent_py_path}')
        return True

    except Exception as e:
        print(f'[ERROR] Failed to apply formatter: {e}')
        return False

def main():
    """Main execution"""
    print('[INFO] Applying StructuredLogFormatter to agent logging...')

    agent_py = find_agent_py()
    if not agent_py:
        print('[ERROR] Could not locate agent.py')
        return 1

    print(f'[INFO] Found agent at: {agent_py}')

    if apply_formatter(agent_py):
        print('[OK] Formatter applied successfully')
        print('[INFO] Please restart the agent for changes to take effect')
        return 0
    else:
        print('[ERROR] Failed to apply formatter')
        return 1

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
