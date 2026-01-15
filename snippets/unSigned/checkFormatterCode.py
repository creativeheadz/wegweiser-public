"""
Snippet: Check Formatter Code - Verify what's in agent.py
"""
import os
import platform

def check_formatter():
    """Check what formatter code is actually in agent.py"""

    if platform.system() == 'Windows':
        agent_path = 'c:\\program files (x86)\\Wegweiser\\Agent\\core\\agent.py'
    else:
        agent_path = '/opt/Wegweiser/Agent/core/agent.py'

    print(f'[INFO] Checking agent at: {agent_path}')

    if not os.path.isfile(agent_path):
        print(f'[ERROR] File not found')
        return False

    with open(agent_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check for color codes
    if '\\033[' in content or '\033[' in content:
        print('[ERROR] ANSI color codes FOUND in agent.py')
        # Show a snippet
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if 'COLORS' in line or '\033[' in line or '\\033[' in line:
                print(f'  Line {i}: {line[:100]}')
        return False
    else:
        print('[OK] No ANSI color codes found in agent.py')
        return True

if __name__ == '__main__':
    check_formatter()
