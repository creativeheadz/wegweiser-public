#!/usr/bin/env python3
"""
Emergency fix: Update all analyzers to use JSON-only parsing
"""
import os
import re
from pathlib import Path

def fix_analyzer_file(file_path):
    """Fix a single analyzer file"""
    print(f"Fixing {file_path}...")
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    original_content = content
    
    # 1. Remove parse_ai_response import
    content = re.sub(r'from app\.tasks\.utils import parse_ai_response\n?', '', content)
    
    # 2. Remove unused imports that might be left over
    content = re.sub(r'import re\n?', '', content)
    content = re.sub(r'import bleach\n?', '', content)
    content = re.sub(r'from datetime import datetime\n?', '', content)
    
    # 3. Fix parse_response method to use JSON-only parsing
    old_parse_pattern = r'def parse_response\(self, response: str\) -> Dict\[str, Any\]:\s*"""[^"]*"""\s*allowed_tags = \[[^\]]+\]\s*return parse_ai_response\(response(?:, allowed_tags)?\)'
    
    new_parse_method = '''def parse_response(self, response: str) -> Dict[str, Any]:
        """Parse AI response into structured format - JSON ONLY"""
        return self.parse_json_response(response)'''
    
    content = re.sub(old_parse_pattern, new_parse_method, content, flags=re.DOTALL)
    
    # 4. Alternative pattern for simpler cases
    simple_pattern = r'return parse_ai_response\(response(?:, allowed_tags)?\)'
    content = re.sub(simple_pattern, 'return self.parse_json_response(response)', content)
    
    # 5. Clean up any double newlines
    content = re.sub(r'\n\n\n+', '\n\n', content)
    
    if content != original_content:
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"  ✅ Fixed {file_path}")
        return True
    else:
        print(f"  ⚠️  No changes needed for {file_path}")
        return False

def main():
    """Fix all analyzer files"""
    
    # List of analyzer files to fix
    analyzer_files = [
        'app/tasks/organizations/analyzer.py',
        'app/tasks/software/analyzer.py',
        'app/tasks/groups/analyzer.py',
        'app/tasks/kernel/analyzer.py',
        'app/tasks/storage/analyzer.py',
        'app/tasks/hardware/analyzer.py',
        'app/tasks/network/analyzer.py',
        'app/tasks/system/analyzer.py',
        'app/tasks/programs/analyzer.py',
        'app/tasks/crashes/analyzer.py',
        'app/tasks/application/analyzer.py',
        'app/tasks/auth/analyzer.py',
        'app/tasks/drivers/analyzer.py',
        'app/tasks/macos_os/analyzer.py',
        'app/tasks/security/analyzer.py',
        'app/tasks/syslog/analyzer.py',
        'app/tasks/macos_logs/analyzer.py',
        'app/tasks/macos_hardware/analyzer.py'
    ]
    
    print("🚨 EMERGENCY FIX: Converting all analyzers to JSON-only parsing")
    print("=" * 70)
    
    fixed_count = 0
    total_count = len(analyzer_files)
    
    for file_path in analyzer_files:
        if os.path.exists(file_path):
            if fix_analyzer_file(file_path):
                fixed_count += 1
        else:
            print(f"  ❌ File not found: {file_path}")
    
    print("=" * 70)
    print(f"Results: {fixed_count}/{total_count} analyzers fixed")
    
    if fixed_count == total_count:
        print("🎉 ALL ANALYZERS FIXED! Legacy parsing eliminated!")
    else:
        print("⚠️  Some analyzers need manual attention")
    
    return fixed_count == total_count

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
