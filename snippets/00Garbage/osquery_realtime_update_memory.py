# Filepath: snippets/unSigned/osquery_realtime_update_memory.py
# Filepath: osquery_realtime_update_memory.py
import subprocess
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

def run_osquery(query):
    """Run osquery and return results"""
    try:
        osquery_path = r'C:\Program Files\osquery\osqueryi.exe' if platform.system() == 'Windows' else '/usr/bin/osqueryi'
        result = subprocess.run([osquery_path, '--json', query], capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"osquery error: {result.stderr}")
            return None
        return json.loads(result.stdout)
    except Exception as e:
        logger.error(f"Failed to run osquery: {e}")
        return None

def collect_memory_info():
    queries = {
        'used_memory': 'SELECT SUM(resident_size) AS total_memory_used FROM processes WHERE resident_size > 0',
        'total_memory': 'SELECT physical_memory FROM system_info'
    }

    try:
        # Get total physical memory
        total_result = run_osquery(queries['total_memory'])
        if not total_result or len(total_result) == 0:
            return None
        total_memory = int(total_result[0]['physical_memory'])
            
        # Get used memory
        used_result = run_osquery(queries['used_memory'])
        if not used_result or len(used_result) == 0:
            return None
        used_memory = int(used_result[0]['total_memory_used'])
                
        # Calculate percentage
        memory_percentage = (used_memory / total_memory) * 100 if total_memory > 0 else 0
                
        return {
            'total_memory': total_memory,
            'used_memory': used_memory,
            'memory_percentage': round(memory_percentage, 1)
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