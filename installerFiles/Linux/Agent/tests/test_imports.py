#!/usr/bin/env python3
"""
Test script to verify all imports work correctly
"""

import sys
import os

# Add parent directory to path so agent_refactored can be imported as a package
agent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
parent_dir = os.path.dirname(agent_dir)
sys.path.insert(0, parent_dir)

def test_imports():
    """Test that all imports work correctly"""
    print("Testing imports...")
    
    try:
        print("  - Importing agent_refactored.core.config...")
        from agent_refactored.core.config import ConfigManager
        print("    ✓ ConfigManager imported")
        
        print("  - Importing agent_refactored.core.crypto...")
        from agent_refactored.core.crypto import CryptoManager
        print("    ✓ CryptoManager imported")
        
        print("  - Importing agent_refactored.core.api_client...")
        from agent_refactored.core.api_client import APIClient
        print("    ✓ APIClient imported")
        
        print("  - Importing agent_refactored.core.nats_service...")
        from agent_refactored.core.nats_service import NATSService
        print("    ✓ NATSService imported")
        
        print("  - Importing agent_refactored.execution.executor...")
        from agent_refactored.execution.executor import SnippetExecutor
        print("    ✓ SnippetExecutor imported")
        
        print("  - Importing agent_refactored.monitoring.health...")
        from agent_refactored.monitoring.health import HealthMonitor
        print("    ✓ HealthMonitor imported")
        
        print("  - Importing agent_refactored.core.agent...")
        from agent_refactored.core.agent import WegweiserAgent
        print("    ✓ WegweiserAgent imported")
        
        print("\n✓ All imports successful!")
        return True
        
    except Exception as e:
        print(f"\n✗ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = test_imports()
    sys.exit(0 if success else 1)

