# Filepath: snippets/unSigned/realtime_cpu.py
# Filepath: snippets/unSigned/realtime_update.py
import psutil
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
    configDir = os.path.join(appDir, 'Config', '')
    return appDir, configDir

def getDeviceUuid():
    _, configDir = getAppDirs()
    with open(os.path.join(configDir, 'agent.config')) as f:
        agentConfigDict = json.load(f)
    deviceUuid = agentConfigDict['deviceuuid']
    host = agentConfigDict.get('serverAddr', 'app.wegweiser.tech')
    return deviceUuid, host

def collect_realtime_info():
    """Collect CPU information using psutil"""
    try:
        # Get CPU percentage over 1 second interval
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Get CPU status (simplified - 1 if any CPU core is above 80%, 0 otherwise)
        cpu_status = 1 if cpu_percent > 80 else 0
        
        return {
            'load_percentage': str(int(cpu_percent)),
            'cpu_status': str(cpu_status)
        }
    except Exception as e:
        logger.error(f"Failed to collect CPU info: {e}")
        return None

def sendJsonPayloadFlask(payload, endpoint, host, deviceUuid):
    url = f'https://{host}/widgets/{deviceUuid}{endpoint}'
    logger.debug(f'Attempting to call {url}')
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response
    except Exception as e:
        logger.error(f"Failed to send payload: {e}")
        return None

###########################  MAIN ###########################
try:
    deviceUuid, host = getDeviceUuid()
    
    # Collect CPU data using psutil
    realtime_data = collect_realtime_info()
    if not realtime_data:
        logger.error("No real-time CPU data collected")
        sys.exit(1)

    # Prepare the payload
    payload = {
        'data_type': 'osquery-info',
        'data_value': realtime_data
    }
    
    # Send data
    response = sendJsonPayloadFlask(payload, '/realtime-data', host, deviceUuid)
    if response:
        logger.info("Real-time data sent successfully")
    else:
        logger.error("Failed to send real-time data")
    
except Exception as e:
    logger.error(f"Error during execution: {str(e)}")
    sys.exit(1)