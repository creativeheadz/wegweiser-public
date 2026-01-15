# Filepath: snippets/unSigned/osquery_collect.py
# Filepath: snippets/osquery_collect.py
import subprocess
import json
from logzero import logger
import platform
import os
import time
import requests
import sys

def getAppDirs():
    if platform.system() == 'Windows':
        appDir = 'c:\\program files (x86)\\Wegweiser\\'
    else:
        appDir = '/opt/Wegweiser/'
    logDir = os.path.join(appDir, 'Logs', '')
    configDir = os.path.join(appDir, 'Config', '')
    filesDir = os.path.join(appDir, 'files', '')
    scriptsDir = os.path.join(appDir, 'Scripts', '')
    tempDir = os.path.join(appDir, 'Temp', '')
    return(appDir, logDir, configDir, tempDir, filesDir, scriptsDir)

def getDeviceUuid():
    appDir, logDir, configDir, tempDir, filesDir, scriptsDir = getAppDirs()
    with open(os.path.join(configDir, 'agent.config')) as f:
        agentConfigDict = json.load(f)
    deviceUuid = agentConfigDict['deviceuuid']
    if 'serverAddr' in agentConfigDict:
        host = agentConfigDict['serverAddr']
    else:
        host = 'app.wegweiser.tech'
    return(deviceUuid, host)

def run_osquery(query):
    """Run osquery and return results"""
    try:
        if platform.system() == 'Windows':
            osquery_path = r'C:\Program Files\osquery\osqueryi.exe'
        else:
            osquery_path = '/usr/bin/osqueryi'

        cmd = [osquery_path, '--json', query]
        logger.debug(f"Running osquery: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"osquery error: {result.stderr}")
            return None
            
        return json.loads(result.stdout)
    except Exception as e:
        logger.error(f"Failed to run osquery. Reason: {e}")
        return None

def sendJsonPayloadFlask(payload, endpoint, host):
    url = f'https://{host}{endpoint}'
    logger.debug(f'Attempting to call {url}')
    logger.debug(f'payload: {payload}')
    headers = {'Content-Type': 'application/json'}
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    return response

def collect_basic_info():
    queries = {
        'os_info': 'SELECT * FROM os_version LIMIT 1',
        'system_info': 'SELECT * FROM system_info LIMIT 1',
        'cpu_info': 'SELECT * FROM cpu_info LIMIT 1',
        'memory_info': 'SELECT * FROM memory_info LIMIT 1',
        'disk_info': 'SELECT * FROM disk_info',
        'network_info': 'SELECT * FROM interface_details',
        'logged_in_users': 'SELECT * FROM logged_in_users',
        'installed_software': 'SELECT name, version, install_date FROM programs',
        'services': 'SELECT name, display_name, status, path FROM services',
        'startup_items': 'SELECT name, path, args FROM startup_items',
        'windows_patches': 'SELECT hotfix_id, description, installed_on FROM patches',
        'processes': 'SELECT name, pid, path, start_time FROM processes LIMIT 10',
        'scheduled_tasks': 'SELECT name, path, enabled FROM scheduled_tasks',
        'drivers': 'SELECT description, service, image, path FROM drivers'
    }

    results = {}
    for name, query in queries.items():
        logger.info(f'Running {name} query...')
        try:
            result = run_osquery(query)
            if result:
                results[name] = result
            else:
                logger.warning(f"No results for query: {name}")
        except Exception as e:
            logger.error(f"Failed to run query '{name}'. Reason: {e}")
        
        time.sleep(1)  # Small delay between queries to avoid overwhelming the system
    
    return results


###########################  MAIN ###########################
try:
    deviceUuid, host = getDeviceUuid()
    
    # Collect osquery data
    osquery_data = collect_basic_info()
    if not osquery_data:
        logger.error("No osquery data collected")
        sys.exit(1)

    # Send data as device metadata
    body = {
        'deviceuuid': deviceUuid,
        'metalogos_type': 'osquery-info',
        'metalogos': osquery_data
    }
    
    response = sendJsonPayloadFlask(body, '/ai/device/metadata', host)
    logger.info(f"Data collected and sent. Response: {response.status_code}")
    
except Exception as e:
    logger.error(f"Error during execution: {str(e)}")
    sys.exit(1)