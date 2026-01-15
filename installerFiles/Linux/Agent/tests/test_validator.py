"""
Tests for snippet validator
"""

import pytest
from agent_refactored.execution.validator import SnippetValidator


class TestSnippetValidator:
    """Test snippet validation"""
    
    def test_valid_snippet(self):
        """Test valid snippet passes validation"""
        code = """
import json
import requests

data = {'key': 'value'}
print(json.dumps(data))
"""
        result = SnippetValidator.validate(code)
        assert result.valid
    
    def test_syntax_error(self):
        """Test syntax error detection"""
        code = "import json\nthis is invalid python"
        result = SnippetValidator.validate(code)
        assert not result.valid
        assert "Syntax error" in result.error
    
    def test_unsafe_import(self):
        """Test unsafe import detection"""
        code = "import subprocess\nimport evil_module"
        result = SnippetValidator.validate(code)
        assert not result.valid
        assert "Unsafe import" in result.error
    
    def test_dangerous_call_eval(self):
        """Test dangerous call detection - eval"""
        code = "eval('print(1)')"
        result = SnippetValidator.validate(code)
        assert not result.valid
        assert "Dangerous call" in result.error
    
    def test_dangerous_call_exec(self):
        """Test dangerous call detection - exec"""
        code = "exec('x = 1')"
        result = SnippetValidator.validate(code)
        assert not result.valid
        assert "Dangerous call" in result.error
    
    def test_safe_modules(self):
        """Test safe modules are allowed"""
        code = """
import os
import sys
import json
import requests
import datetime
import platform

print(platform.system())
"""
        result = SnippetValidator.validate(code)
        assert result.valid
    
    def test_complexity_limit(self):
        """Test complexity limit"""
        # Create code with many loops
        code = "for i in range(1000):\n"
        code += "    for j in range(1000):\n"
        code += "        for k in range(1000):\n"
        code += "            pass\n"
        
        result = SnippetValidator.validate(code)
        assert not result.valid
        assert "complex" in result.error.lower()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

