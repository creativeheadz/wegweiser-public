#!/usr/bin/env python3
"""
Wegweiser Agent - Entry point script
Works on Windows, macOS, and Linux
"""

import sys
import os

# Add current directory to path so core module can be imported
agent_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, agent_dir)

# Import from core module (files are flattened in deployment)
from core.agent import main

if __name__ == '__main__':
    main()

