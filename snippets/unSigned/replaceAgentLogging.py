"""
Snippet: Replace Agent Logging - Direct file replacement
Replaces agent.py with corrected version that has no ANSI color codes
"""
import os
import sys
import platform
import shutil

def replace_agent_logging():
    """Replace agent.py with corrected version"""

    if platform.system() == 'Windows':
        agent_path = 'c:\\program files (x86)\\Wegweiser\\Agent\\core\\agent.py'
        backup_path = agent_path + '.backup'
    else:
        agent_path = '/opt/Wegweiser/Agent/core/agent.py'
        backup_path = agent_path + '.backup'

    print(f'[INFO] Replacing agent at: {agent_path}')

    if not os.path.isfile(agent_path):
        print(f'[ERROR] Agent file not found')
        return False

    # Create the corrected formatter code
    corrected_code = '''class StructuredLogFormatter(logging.Formatter):
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

        return log_line'''

    try:
        # Read the file
        with open(agent_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Find the old formatter class and replace it
        # Look for the class definition
        start_marker = 'class StructuredLogFormatter(logging.Formatter):'
        if start_marker not in content:
            print('[ERROR] StructuredLogFormatter not found in agent.py')
            return False

        # Find the full class by looking for the next class definition
        start_pos = content.find(start_marker)
        next_class_pos = content.find('\nclass ', start_pos + 1)

        if next_class_pos == -1:
            print('[ERROR] Could not find end of StructuredLogFormatter class')
            return False

        # Replace the class
        old_class = content[start_pos:next_class_pos]
        new_content = content[:start_pos] + corrected_code + content[next_class_pos:]

        # Backup the original
        shutil.copy2(agent_path, backup_path)
        print(f'[OK] Backed up original to: {backup_path}')

        # Write the corrected version
        with open(agent_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        print('[OK] Agent logging formatter replaced successfully')
        print('[INFO] Agent will use corrected formatter after restart')
        return True

    except Exception as e:
        print(f'[ERROR] Failed to replace formatter: {e}')
        return False

if __name__ == '__main__':
    success = replace_agent_logging()
    sys.exit(0 if success else 1)
