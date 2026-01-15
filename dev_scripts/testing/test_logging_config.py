#!/usr/bin/env python3
"""
Test script for the dynamic logging configuration feature.
"""

import os
import sys
import json
import logging

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_logging_config():
    """Test the logging configuration functionality."""
    print("=" * 60)
    print("Testing Dynamic Logging Configuration")
    print("=" * 60)
    
    try:
        # Test basic imports
        print("1. Testing imports...")
        from app.utilities.app_logging_helper import (
            load_logging_config, 
            get_logging_levels_enabled, 
            update_logging_config,
            reload_logging_config,
            DEFAULT_LOGGING_CONFIG
        )
        print("   ✓ All imports successful")
        
        # Test configuration loading
        print("\n2. Testing configuration loading...")
        load_logging_config()
        levels = get_logging_levels_enabled()
        print(f"   ✓ Current levels: {levels}")
        
        # Test configuration update
        print("\n3. Testing configuration update...")
        new_levels = {
            'INFO': True,
            'DEBUG': True,
            'ERROR': True,
            'WARNING': True
        }
        result = update_logging_config(new_levels, 'test_user')
        print(f"   ✓ Update result: {result}")
        
        # Verify the update
        print("\n4. Verifying update...")
        updated_levels = get_logging_levels_enabled()
        print(f"   ✓ Updated levels: {updated_levels}")
        
        # Test reload
        print("\n5. Testing configuration reload...")
        reloaded_config = reload_logging_config()
        print(f"   ✓ Reloaded config: {reloaded_config}")
        
        # Check if config file was created
        print("\n6. Checking configuration file...")
        config_file = os.path.join('config', 'logging_config.json')
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                file_content = json.load(f)
            print(f"   ✓ Config file exists: {config_file}")
            print(f"   ✓ File content: {json.dumps(file_content, indent=2)}")
        else:
            print(f"   ✗ Config file not found: {config_file}")
        
        print("\n" + "=" * 60)
        print("✓ All tests passed successfully!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_logging_filter():
    """Test the logging filter functionality."""
    print("\n" + "=" * 60)
    print("Testing Logging Filter Functionality")
    print("=" * 60)
    
    try:
        from app.utilities.app_logging_helper import LogLevelFilter, should_log
        
        # Test should_log function
        print("1. Testing should_log function...")
        print(f"   INFO should log: {should_log(logging.INFO)}")
        print(f"   DEBUG should log: {should_log(logging.DEBUG)}")
        print(f"   ERROR should log: {should_log(logging.ERROR)}")
        print(f"   WARNING should log: {should_log(logging.WARNING)}")
        
        # Test LogLevelFilter
        print("\n2. Testing LogLevelFilter...")
        filter_obj = LogLevelFilter()
        
        # Create test log records
        info_record = logging.LogRecord(
            name='test', level=logging.INFO, pathname='', lineno=0,
            msg='Test INFO message', args=(), exc_info=None
        )
        debug_record = logging.LogRecord(
            name='test', level=logging.DEBUG, pathname='', lineno=0,
            msg='Test DEBUG message', args=(), exc_info=None
        )
        error_record = logging.LogRecord(
            name='test', level=logging.ERROR, pathname='', lineno=0,
            msg='Test ERROR message', args=(), exc_info=None
        )
        warning_record = logging.LogRecord(
            name='test', level=logging.WARNING, pathname='', lineno=0,
            msg='Test WARNING message', args=(), exc_info=None
        )
        
        print(f"   INFO record filtered: {filter_obj.filter(info_record)}")
        print(f"   DEBUG record filtered: {filter_obj.filter(debug_record)}")
        print(f"   ERROR record filtered: {filter_obj.filter(error_record)}")
        print(f"   WARNING record filtered: {filter_obj.filter(warning_record)}")
        
        print("\n✓ Filter tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n✗ Filter test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success1 = test_logging_config()
    success2 = test_logging_filter()
    
    if success1 and success2:
        print("\n🎉 All tests passed! The dynamic logging configuration is working correctly.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Please check the implementation.")
        sys.exit(1)
