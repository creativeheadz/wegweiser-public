# Filepath: snippets/unSigned/updatePersistentAgent.py
import hashlib
from logzero import logger, logfile
import json
import platform
import requests
import subprocess
import os
import sys

def getServerPersistentAgentVersion(localPersistentAgentVersion):
    logger.info(f'Checking persistent agent version')
    logger.info(f'local persistentAgentVersion: {localPersistentAgentVersion}')
    r = requests.get(f'https://{host}/diags/persistentagentversion')
    data = r.json()
    serverPersistentAgentVersion = data['serverPersistentAgentVersion']
    persistentAgentHashPy = data['serverPersistentAgentHashPy']
    logger.info(f'server persistentAgentVersion: {serverPersistentAgentVersion}')
    if int(localPersistentAgentVersion) < int(serverPersistentAgentVersion):
        logger.info('Local persistent agent needs updating...')
        persistentAgentUpdateReqd = True
    else:
        logger.info('Local persistent agent is up to date.')
        persistentAgentUpdateReqd = False
    return(persistentAgentUpdateReqd, persistentAgentHashPy)

def getSha256Hash(fileToHash):
    sha256Hash = hashlib.sha256()
    with open(fileToHash, 'rb') as f:
        for byteBlock in iter(lambda: f.read(4096), b""):
            sha256Hash.update(byteBlock)
    logger.info(f'sha256 of {fileToHash}: {sha256Hash.hexdigest()}')
    return(sha256Hash.hexdigest())

def updatePersistentAgent(persistentAgentHashPy):
    if platform.system() == 'Linux':
        persistentAgentUrl = f'https://{host}/download/persistent_agent.py'
        chunkSize = 4096
        saveToFile = os.path.join(agentDir, 'persistent_agent.new')
        persistentAgentPath = os.path.join(agentDir, 'persistent_agent.py')
        oldPersistentAgent = os.path.join(agentDir, 'persistent_agent.old')
        logger.info(f'Attempting to download {persistentAgentUrl} to {saveToFile}...')
        try:
            r = requests.get(persistentAgentUrl, stream=True)
            if r.status_code != 200:
                logger.error(f'Failed to download {persistentAgentUrl}. Status Code: {r.status_code}')
                return(False)
            with open(saveToFile, 'wb') as f:
                for chunk in r.iter_content(chunk_size=chunkSize):
                    if chunk:
                        f.write(chunk)
        except Exception as e:
            logger.error(f'Failed to download {persistentAgentUrl} to {saveToFile}. Reason: {e}')
        newPersistentAgentHash = getSha256Hash(saveToFile)
        logger.info(f'Downloaded Hash: {newPersistentAgentHash} | Server Hash: {persistentAgentHashPy}')
        if newPersistentAgentHash == persistentAgentHashPy:
            logger.info(f'Attempting to rename {saveToFile} to {persistentAgentPath}')
            try:        # rename the current persistent agent to .old
                if os.path.exists(persistentAgentPath):
                    os.rename(persistentAgentPath, oldPersistentAgent)
            except Exception as e:
                logger.error(f'Failed to rename {persistentAgentPath} to {oldPersistentAgent}. Reason: {e}')
                sys.exit()
            try:        # rename the persistent_agent.new to persistent_agent.py
                os.rename(saveToFile, persistentAgentPath)
                logger.info(f'Successfully upgraded {persistentAgentUrl} to {saveToFile}')
                logger.info('New persistent agent will run on next service restart')
            except Exception as e:
                logger.error(f'Failed to rename {saveToFile} to {persistentAgentPath}. Reason: {e}')
            try:        # remove the .old persistent agent
                if os.path.exists(oldPersistentAgent):
                    os.remove(oldPersistentAgent)
                    logger.info(f'Deleted {oldPersistentAgent}')
            except Exception as e:
                logger.error(f'Failed to remove {oldPersistentAgent}')
            
            # Restart the persistent agent service
            try:
                logger.info('Restarting wegweiser-persistent-agent service...')
                result = subprocess.run(['sudo', 'systemctl', 'restart', 'wegweiser-persistent-agent.service'], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    logger.info('Persistent agent service restarted successfully')
                else:
                    logger.error(f'Failed to restart service: {result.stderr}')
            except Exception as e:
                logger.error(f'Failed to restart persistent agent service: {e}')
        else:
            logger.error('Hashes do not match. Deleting download.')
            try:
                os.remove(saveToFile)
            except Exception as e:
                logger.error(f'Failed to delete {saveToFile}. Reason: {e}')
    else:
        logger.info('Persistent agent update only supported on Linux')

def getDeviceUuid(configFile):
    logger.info(f'Attempting to read config file: {configFile}...')
    if os.path.isfile(configFile):
        try:
            with open(configFile, 'r') as f:
                configDict = json.load(f)
            logger.info(f'Successfully read {configFile}')
        except Exception as e:
            logger.error(f'Failed to read {configFile}')
            sys.exit('Quitting.')
        deviceUuid = configDict['deviceuuid']
        if 'serverAddr' in configDict:
            host = configDict['serverAddr']
        else:
            host = 'app.wegweiser.tech'
    else:
        logger.error(f'{configFile} does not exist. Quitting.')
        sys.exit()
    return(deviceUuid, host)

def getAppDirs():
    if platform.system() == 'Windows':
        appDir = 'c:\\program files (x86)\\Wegweiser\\'
    else:
        appDir = '/opt/Wegweiser/'
    logDir = os.path.join(appDir, 'Logs', '')
    configDir = os.path.join(appDir, 'Config', '')
    agentDir = os.path.join(appDir, 'Agent', '')
    filesDir = os.path.join(appDir, 'files', '')
    scriptsDir = os.path.join(appDir, 'Scripts', '')
    tempDir = os.path.join(appDir, 'Temp', '')

    checkDirs([appDir, logDir, configDir, tempDir, filesDir, agentDir])
    return(appDir, logDir, configDir, tempDir, filesDir, scriptsDir, agentDir)

def getLocalPersistentAgentVersion(configDir):
    versionFile = os.path.join(configDir, 'persistentAgentVersion.txt')
    if os.path.exists(versionFile):
        with open(versionFile, 'r') as f:
            localPersistentAgentVersion = f.read().strip()
    else:
        localPersistentAgentVersion = '0'
    logger.info(f'localPersistentAgentVersion: {localPersistentAgentVersion}')
    return(localPersistentAgentVersion)

def writeLocalPersistentAgentVersion(configDir, version):
    versionFile = os.path.join(configDir, 'persistentAgentVersion.txt')
    with open(versionFile, 'w') as f:
        f.write(version)
    logger.info(f'Updated persistent agent version to: {version}')

def checkDirs(dirsToCheck):
    for dirToCheck in dirsToCheck:
        dirToCheck = os.path.join(dirToCheck, '')
        if not os.path.isdir(dirToCheck):
            logger.info(f'{dirToCheck} does not exist. Creating...')
            try:
                os.makedirs(dirToCheck)
                logger.info(f'{dirToCheck} created.')
            except Exception as e:
                logger.error(f'Failed to create {dirToCheck}. Reason: {e}')
                sys.exit()

####################### MAIN #######################     

# Only run on Linux systems
if platform.system() != 'Linux':
    logger.info('Persistent agent update only supported on Linux systems')
    sys.exit()

appDir, \
    logDir, \
    configDir, \
    tempDir, \
    filesDir, \
    scriptsDir, \
    agentDir = getAppDirs()
configFile = f'{configDir}agent.config'
deviceUuid, \
    host = getDeviceUuid(configFile)
localPersistentAgentVersion = getLocalPersistentAgentVersion(configDir)

try:
    persistentAgentUpdateReqd, \
    persistentAgentHashPy = getServerPersistentAgentVersion(localPersistentAgentVersion)

    if persistentAgentUpdateReqd == True:
        updatePersistentAgent(persistentAgentHashPy)
        # Update local version file after successful update
        try:
            r = requests.get(f'https://{host}/diags/persistentagentversion')
            data = r.json()
            serverPersistentAgentVersion = data['serverPersistentAgentVersion']
            writeLocalPersistentAgentVersion(configDir, serverPersistentAgentVersion)
        except Exception as e:
            logger.error(f'Failed to update local version file: {e}')
        sys.exit('Exiting after persistent agent update.')
except Exception as e:
    logger.error(f'Persistent agent update not available on this server: {e}')
    logger.info('This is normal if the server does not support persistent agent updates yet')
