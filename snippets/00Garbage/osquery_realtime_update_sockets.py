# Filepath: snippets/unSigned/osquery_realtime_update_sockets.py
# Filepath: osquery_realtime_update_sockets.py
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

def collect_socket_info():
    # Query combining process and socket information
    query = """
    SELECT 
        p.name as process_name,
        p.pid,
        pos.local_address,
        pos.local_port,
        pos.remote_address,
        pos.remote_port,
        pos.state,
        pos.family,
        p.path
    FROM process_open_sockets pos
    LEFT JOIN processes p ON pos.pid = p.pid
    WHERE pos.state != ''
    """

    try:
        result = run_osquery(query)
        if not result:
            return None

        # List of well-known ports for checking anomalies
        well_known_ports = {80, 443, 53, 22, 21, 25, 110, 143, 989, 990, 993, 995}
        
        # Process the results
        sockets_info = {
            'connections': result,
            'stats': {
                'total_connections': len(result),
                'listening_ports': sum(1 for conn in result if conn['state'] == 'LISTEN'),
                'established_connections': sum(1 for conn in result if conn['state'] == 'ESTABLISHED'),
                'unusual_ports': sum(1 for conn in result if conn['local_port'] not in well_known_ports and conn['state'] == 'LISTEN'),
                'foreign_connections': sum(1 for conn in result if conn['remote_address'] != '0.0.0.0' and conn['remote_address'] != '127.0.0.1')
            }
        }
        
        return sockets_info
            
    except Exception as e:
        logger.error(f"Failed to collect socket info: {e}")
        return None

def main():
    try:
        deviceUuid, host = getDeviceUuid()
        
        socket_data = collect_socket_info()
        if not socket_data:
            logger.error("No socket data collected")
            sys.exit(1)

        payload = {
            'data_type': 'osquery-info-sockets',
            'data_value': socket_data
        }
        
        url = f'https://{host}/widgets/{deviceUuid}/realtime-socket-data'
        headers = {'Content-Type': 'application/json'}
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        logger.info("Socket data sent successfully")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()