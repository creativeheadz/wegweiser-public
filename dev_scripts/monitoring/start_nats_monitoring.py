#!/usr/bin/env python3
"""
Manually start NATS demo monitoring
"""

import asyncio
import sys
import os
import threading

# Add the app directory to Python path
sys.path.insert(0, '/opt/wegweiser')

def start_monitoring():
    """Start NATS monitoring in background thread"""
    from app import create_app
    from app.handlers.nats_demo.system_metrics import system_metrics_handler
    
    app = create_app()
    
    def run_monitoring():
        with app.app_context():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                print("Starting NATS demo monitoring...")
                loop.run_until_complete(system_metrics_handler.start_monitoring())
            except Exception as e:
                print(f"Error: {e}")
                import traceback
                traceback.print_exc()
            finally:
                loop.close()
    
    # Start in background thread
    thread = threading.Thread(target=run_monitoring, daemon=True)
    thread.start()
    
    print("NATS monitoring thread started")
    return thread

if __name__ == "__main__":
    thread = start_monitoring()
    
    # Keep the script running for a bit to let monitoring start
    import time
    time.sleep(5)
    
    print("Checking status...")
    
    # Check if monitoring started
    from app import create_app
    from app.handlers.nats_demo.system_metrics import system_metrics_handler
    
    app = create_app()
    with app.app_context():
        print(f"Running: {system_metrics_handler.running}")
        print(f"Buffer keys: {list(system_metrics_handler.metrics_buffer.keys())}")
        print(f"Total metrics: {sum(len(buffer) for buffer in system_metrics_handler.metrics_buffer.values())}")
    
    # Keep running to receive messages
    print("Waiting for messages for 30 seconds...")
    time.sleep(30)
    
    # Check again
    with app.app_context():
        print(f"After 30s - Running: {system_metrics_handler.running}")
        print(f"Buffer keys: {list(system_metrics_handler.metrics_buffer.keys())}")
        print(f"Total metrics: {sum(len(buffer) for buffer in system_metrics_handler.metrics_buffer.values())}")
        
        # Show some sample data
        for key, buffer in system_metrics_handler.metrics_buffer.items():
            if buffer:
                print(f"{key}: {len(buffer)} metrics, latest: {list(buffer)[-1]}")
