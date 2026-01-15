# Filepath: snippets/unSigned/realtime_memory.py
# Filepath: snippets/unSigned/realtime_update_memory.py
import psutil
import json
from logzero import logger
import platform
import os
import requests
import sys

def getDeviceUuid():
    config_path = os.path.join('c:\\program files (x86)\\Wegweiser\\Config\\' if platform.system() == 'Windows' else '/opt/Wegweiser/Config/', 'agent.config')
    with open(config_path) as f:
        config = json.load(f)
    return (config['deviceuuid'], config.get('serverAddr', 'app.wegweiser.tech'))

def collect_memory_info():
    """Collect memory information using psutil"""
    try:
        # Get virtual memory statistics
        memory = psutil.virtual_memory()
        
        return {
            'total_memory': memory.total,
            'used_memory': memory.used,
            'memory_percentage': round(memory.percent, 1)
        }
    except Exception as e:
        logger.error(f"Failed to collect memory info: {e}")
        return None

def main():
    try:
        deviceUuid, host = getDeviceUuid()
        
        memory_data = collect_memory_info()
        if not memory_data:
            logger.error("No memory data collected")
            sys.exit(1)

        payload = {
            'data_type': 'osquery-info-ram',
            'data_value': memory_data
        }
        
        url = f'https://{host}/widgets/{deviceUuid}/realtime-ram-data'
        headers = {'Content-Type': 'application/json'}
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        logger.info("Memory data sent successfully")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()