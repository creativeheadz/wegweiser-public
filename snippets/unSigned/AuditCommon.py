# Filepath: snippets/unSigned/AuditCommon.py
"""
Shared utilities for audit collectors (Windows, Linux, macOS)
"""
import os
import json
import math
import sys
import subprocess
import dns.resolver
import requests
from logzero import logger

def convertSize(sizeBytes):
    """Convert bytes to human-readable format"""
    if sizeBytes == 0:
        return "0 B"
    sizeName = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(sizeBytes, 1024)))
    p = math.pow(1024, i)
    s = round(sizeBytes / p, 2)
    return f'{s} {sizeName[i]}'

def sendJsonPayloadFlask(payload, endpoint, host, debugMode=False):
    """Send JSON payload to Flask endpoint"""
    url = f'https://{host}{endpoint}'
    if debugMode:
        logger.debug(f'payload to send: {payload}')
        logger.debug(f'Attempting to connect to {url}')
    headers = {'Content-Type': 'application/json'}
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    return response

def getPublicIpAddr():
    """Get public IP address"""
    odDnsServer = '208.67.222.222'
    httpDnsServer = 'https://icanhazip.com'
    dnsResolver = dns.resolver.Resolver()
    dnsResolver.nameservers = [odDnsServer]
    publicIp = None
    
    try:
        answers = dnsResolver.resolve('myip.opendns.com', 'A')
        for ip in answers:
            publicIp = ip.to_text()
    except Exception as e:
        logger.error(f'Failed to get publicIP from {odDnsServer}. Reason: {e}')
    
    if not publicIp:
        try:
            r = requests.get(httpDnsServer)
            publicIp = r.text.strip()
        except Exception as e:
            logger.error(f'Failed to get publicIP from {httpDnsServer}. Reason: {e}')
    
    if not publicIp:
        publicIp = '0.0.0.0'
    
    return publicIp

def getUserHomePath():
    """Get user home directory path"""
    userHomePath = os.path.expanduser("~")
    logger.info(f'userHomePath: {userHomePath}')
    return userHomePath

def getDeviceUuid(configFile):
    """Get device UUID from config file"""
    logger.info(f'Attempting to read {configFile}')
    try:
        with open(configFile, 'r') as f:
            config = json.load(f)
            deviceUuid = config.get('deviceUuid')
            host = config.get('host', 'app.wegweiser.tech')
            logger.info(f'deviceUuid: {deviceUuid}')
            return deviceUuid, host
    except Exception as e:
        logger.error(f'Failed to read config file: {e}')
        return None, 'app.wegweiser.tech'

def getAppDirs():
    """Get application directories"""
    userHomePath = getUserHomePath()
    appDir = os.path.join(userHomePath, '.wegweiser')
    logDir = os.path.join(appDir, 'logs')
    configDir = os.path.join(appDir, 'config')
    tempDir = os.path.join(appDir, 'temp')
    filesDir = os.path.join(appDir, 'files')
    
    for directory in [appDir, logDir, configDir, tempDir, filesDir]:
        os.makedirs(directory, exist_ok=True)
    
    logger.info(f'appDir: {appDir}')
    return appDir, logDir, configDir, tempDir, filesDir

def delFile(fileToDelete):
    """Delete a file"""
    logger.info(f'Attempting to delete {fileToDelete}...')
    try:
        os.remove(fileToDelete)
        logger.info(f'Successfully deleted {fileToDelete}.')
    except Exception as e:
        logger.error(f'Failed to delete {fileToDelete}. Reason: {e}')

def ensurePsutil():
    """Ensure psutil is installed"""
    try:
        import psutil
        return psutil
    except ImportError:
        logger.info('Installing psutil...')
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'psutil'])
        import psutil
        return psutil

