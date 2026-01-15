# Filepath: snippets/unSigned/osquery_realtime_update.py
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
    return (appDir, logDir, configDir, tempDir, filesDir, scriptsDir)

def getDeviceUuid():
    appDir, logDir, configDir, tempDir, filesDir, scriptsDir = getAppDirs()
    with open(os.path.join(configDir, 'agent.config')) as f:
        agentConfigDict = json.load(f)
    deviceUuid = agentConfigDict['deviceuuid']
    if 'serverAddr' in agentConfigDict:
        host = agentConfigDict['serverAddr']
    else:
        host = 'app.wegweiser.tech'
    return (deviceUuid, host)

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

def sendJsonPayloadFlask(payload, endpoint, host, device_uuid):
    url = f'https://{host}/widgets/{device_uuid}{endpoint}'
    logger.debug(f'Attempting to call {url}')
    logger.debug(f'payload: {payload}')
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        logger.info(f"Payload sent successfully. Response: {response.status_code}")
        return response
    except requests.RequestException as e:
        logger.error(f"Failed to send payload. Reason: {e}")
        return None

def collect_realtime_info():
    queries = {
        'load_percentage': 'SELECT load_percentage FROM cpu_info LIMIT 1',
        'cpu_status': 'SELECT cpu_status FROM cpu_info LIMIT 1'
    }

    results = {}
    for name, query in queries.items():
        logger.info(f'Running {name} query...')
        try:
            result = run_osquery(query)
            if result and len(result) > 0:
                results[name] = result[0][name]
            else:
                logger.warning(f"No results for query: {name}")
        except Exception as e:
            logger.error(f"Failed to run query '{name}'. Reason: {e}")
        
        time.sleep(1)  # Small delay between queries to avoid overwhelming the system
    
    return results

###########################  MAIN ###########################
try:
    deviceUuid, host = getDeviceUuid()
    
    # Collect limited osquery data
    realtime_data = collect_realtime_info()
    if not realtime_data:
        logger.error("No real-time osquery data collected")
        sys.exit(1)

    # Prepare the payload for the new endpoint
    payload = {
        'data_type': 'osquery-info',
        'data_value': realtime_data
    }
    
    # Send data to the new endpoint
    response = sendJsonPayloadFlask(payload, '/realtime-data', host, deviceUuid)
    if response:
        logger.info(f"Real-time data collected and sent. Response: {response.status_code}")
    else:
        logger.error("Failed to send real-time data.")
    
except Exception as e:
    logger.error(f"Error during execution: {str(e)}")
    sys.exit(1)
