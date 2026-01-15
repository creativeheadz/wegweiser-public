# Filepath: snippets/unSigned/quickCheckin.py
# Filepath: snippets/quickCheckin.py
import requests
import json
from logzero import logger
import platform
import os

def sendJsonPayloadFlask(payload, endpoint):
	url 		= f'https://{host}{endpoint}'
	if debugMode == True:
		logger.debug(f'payload to send: {payload}')
		logger.debug(f'Attempting to connect to {url}')
	headers 	= {'Content-Type': 'application/json'}
	response 	= requests.post(url, headers=headers, data=json.dumps(payload))
	return(response)


def getDeviceUuid():
	with open(os.path.join(configDir, 'agent.config')) as f:
		agentConfigDict = json.load(f)
	deviceUuid = agentConfigDict['deviceuuid']
	if 'serverAddr' in agentConfigDict:
		host = agentConfigDict['serverAddr']
	else:
		host 	= 'app.wegweiser.tech'
	return(deviceUuid, host)

def getLocalAgentVersion(agentVersionFile):
	with open(agentVersionFile, 'r') as f:
		localAgentVersion = f.read().strip()
	logger.info(f'localAgentVersion: {localAgentVersion}')
	return(localAgentVersion)


def doQuickCheckin(host, deviceUuid, localAgentVersion, appDir):
	endpoint	= f'/diags/checkin/{deviceUuid}'
	url 		= f'https://{host}{endpoint}'
	payload 	= {'agentVersion' : localAgentVersion, 'agentInstDir' : appDir}

	logger.info(f'Attempting to call {url}')
	try:
		sendJsonPayloadFlask(payload, endpoint)
		logger.info('Quick Check-in complete.')
	except Exception as e:
		logger.error(f'Failed to perform Quick Check-in. Reason: {e}')

def getAppDirs():
	if platform.system() == 'Windows':
		appDir 		= 'c:\\program files (x86)\\Wegweiser\\'
	else:
		appDir 		= '/opt/Wegweiser/'
	logDir 		= os.path.join(appDir, 'Logs', '')
	configDir 	= os.path.join(appDir, 'Config', '')
	filesDir	= os.path.join(appDir, 'files', '')
	scriptsDir	= os.path.join(appDir, 'Scripts', '')
	tempDir 	= os.path.join(appDir, 'Temp', '')
	return(appDir, logDir, configDir, tempDir, filesDir, scriptsDir)

###########################  MAIN ###########################

debugMode = True

appDir, \
	logDir, \
	configDir, \
	tempDir, \
	filesDir, \
	scriptsDir		= getAppDirs()

	

agentVersionFile	= os.path.join(configDir, 'agentVersion.txt')

localAgentVersion	= getLocalAgentVersion(agentVersionFile)
deviceUuid, \
	host 			= getDeviceUuid()

doQuickCheckin(host, deviceUuid, localAgentVersion, appDir)