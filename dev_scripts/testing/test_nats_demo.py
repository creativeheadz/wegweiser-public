#!/usr/bin/env python3
"""
Test script to manually start NATS demo monitoring
"""

import asyncio
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, '/opt/wegweiser')

from app import create_app
from app.handlers.nats_demo.system_metrics import system_metrics_handler

async def test_nats_monitoring():
    """Test NATS monitoring startup"""
    app = create_app()
    
    with app.app_context():
        print("Testing NATS demo monitoring...")
        
        try:
            print("Starting system metrics handler...")
            await system_metrics_handler.start_monitoring()
            
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_nats_monitoring())
