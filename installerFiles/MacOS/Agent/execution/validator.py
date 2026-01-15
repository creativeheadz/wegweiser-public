"""
Snippet Validator - AST-based code validation
"""

import ast
import logging
from typing import NamedTuple

logger = logging.getLogger(__name__)


class ValidationResult(NamedTuple):
    """Validation result"""
    valid: bool
    error: str = ""
    severity: str = "info"


class SnippetValidator:
    """Validate snippets before execution"""
    
    # Safe modules that can be imported
    SAFE_MODULES = {
        'os', 'sys', 'json', 'requests', 'datetime',
        'subprocess', 'platform', 'socket', 'hashlib',
        'base64', 'uuid', 'time', 'logging', 'pathlib',
        're', 'collections', 'itertools', 'functools',
        'math', 'random', 'string', 'urllib', 'psutil', 'logzero', 'getpass',
        'argparse', 'shutil', 'zipfile', 'io', 'tarfile', 'tempfile',
        # DNS and network
        'dns',
        # Windows-specific modules (pywin32)
        'win32api', 'win32service', 'win32con', 'win32file', 'win32security',
        'win32process', 'win32event', 'win32evtlog', 'win32evtlogutil',
        'win32net', 'win32netcon', 'pywintypes'
    }
    
    # Dangerous function calls to block
    # Note: 'open' is allowed for legitimate file operations
    # Snippets are created by trusted MSPs and agent runs with limited permissions
    DANGEROUS_CALLS = {
        'eval', 'exec', '__import__', 'compile',
        'input', 'globals', 'locals',
        'getattr', 'setattr', 'delattr', 'vars',
        'dir', 'help', 'breakpoint'
    }
    
    @staticmethod
    def validate(code: str) -> ValidationResult:
        """Validate snippet code"""
        logger.debug("Validating snippet code...")
        
        # 1. Syntax check
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            logger.warning(f"Syntax error in snippet: {e}")
            return ValidationResult(
                valid=False,
                error=f"Syntax error: {e}",
                severity='critical'
            )
        
        # 2. Check imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    # Check if the base module or any parent module is safe
                    base_module = alias.name.split('.')[0]
                    if base_module not in SnippetValidator.SAFE_MODULES:
                        logger.warning(f"Unsafe import: {alias.name}")
                        return ValidationResult(
                            valid=False,
                            error=f"Unsafe import: {alias.name}",
                            severity='high'
                        )

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    # Check if the base module or any parent module is safe
                    base_module = node.module.split('.')[0]
                    if base_module not in SnippetValidator.SAFE_MODULES:
                        logger.warning(f"Unsafe import from: {node.module}")
                        return ValidationResult(
                            valid=False,
                            error=f"Unsafe import from: {node.module}",
                            severity='high'
                        )
        
        # 3. Check dangerous calls
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in SnippetValidator.DANGEROUS_CALLS:
                        logger.warning(f"Dangerous call: {node.func.id}")
                        return ValidationResult(
                            valid=False,
                            error=f"Dangerous call: {node.func.id}",
                            severity='critical'
                        )
        
        # 4. Complexity check (prevent infinite loops)
        complexity = SnippetValidator._calculate_complexity(tree)
        if complexity > 1000:
            logger.warning(f"Snippet too complex: {complexity}")
            return ValidationResult(
                valid=False,
                error="Snippet too complex",
                severity='medium'
            )
        
        logger.debug("Snippet validation passed")
        return ValidationResult(valid=True)
    
    @staticmethod
    def _calculate_complexity(tree) -> int:
        """Estimate code complexity"""
        count = 0
        for node in ast.walk(tree):
            if isinstance(node, (ast.For, ast.While, ast.If)):
                count += 1
        return count

