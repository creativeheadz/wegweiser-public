#!/usr/bin/env python3
"""
Utility to determine Celery worker log level from logging_config.json

This script reads the logging configuration and determines the appropriate
log level for Celery workers. It respects the centralized logging configuration.

Usage:
    python get_celery_log_level.py
    
Output:
    Prints one of: DEBUG, INFO, WARNING, ERROR, CRITICAL
"""

import json
import os
import sys

def get_config_file_path():
    """Get the path to the logging configuration file."""
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up to app, then to root, then to config
    root_dir = os.path.dirname(os.path.dirname(script_dir))
    config_path = os.path.join(root_dir, 'config', 'logging_config.json')
    return config_path

def get_celery_log_level():
    """
    Determine the appropriate Celery log level based on logging_config.json
    
    Returns the highest enabled log level:
    - If DEBUG is enabled: DEBUG
    - Else if INFO is enabled: INFO
    - Else if WARNING is enabled: WARNING
    - Else if ERROR is enabled: ERROR
    - Else: CRITICAL (most restrictive)
    """
    config_path = get_config_file_path()
    
    # Default to WARNING if config doesn't exist
    if not os.path.exists(config_path):
        return "WARNING"
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        levels = config.get('levels', {})
        
        # Check levels in order of verbosity (most verbose first)
        if levels.get('DEBUG', False):
            return "DEBUG"
        elif levels.get('INFO', False):
            return "INFO"
        elif levels.get('WARNING', True):  # Default to True
            return "WARNING"
        elif levels.get('ERROR', True):  # Default to True
            return "ERROR"
        else:
            return "CRITICAL"
    
    except Exception as e:
        # If there's any error reading the config, default to WARNING
        print(f"Error reading logging config: {e}", file=sys.stderr)
        return "WARNING"

if __name__ == '__main__':
    print(get_celery_log_level())

