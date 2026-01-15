# Filepath: snippets/unSigned/updateAgent.py
import hashlib
from logzero import logger, logfile
import json
import platform
import requests
import subprocess
import os
import sys

def getServerCollVersion(localAgentVersion):
	logger.info(f'Checking agent version')
	logger.info(f'local agentVersion: {localAgentVersion}')
	r 					= requests.get(f'https://{host}/diags/agentversion')
	data 				= r.json()
	serverAgentVersion 	= data['serverAgentVersion']
	collHashPy 			= data['serverAgentHashPy']
	collHashWin			= data['serverAgentHashWin']
	logger.info(f'server agentVersion: {serverAgentVersion}')
	if int(localAgentVersion) < int(serverAgentVersion):
		logger.info('Local agent needs updating...')
		agentUpdateReqd = True
	else:
		logger.info('Local agent is up to date.')
		agentUpdateReqd = False
	return(agentUpdateReqd, collHashPy, collHashWin)

def getSha256Hash(fileToHash):
	sha256Hash = hashlib.sha256()
	with open(fileToHash, 'rb') as f:
		for byteBlock in iter(lambda: f.read(4096), b""):
			sha256Hash.update(byteBlock)
	logger.info(f'sha256 of {fileToHash}: {sha256Hash.hexdigest()}')
	return(sha256Hash.hexdigest())

def updateAgent(collHashPy, collHashWin):
	if platform.system() == 'Linux' or platform.system() == 'Windows':
		agentUrl = f'https://{host}/download/agent.py'
		chunkSize = 4096
		saveToFile 	= os.path.join(scriptsDir, 'agent.new')
		agentPath 	= os.path.join(scriptsDir, 'agent.py')
		oldAgent 	= os.path.join(scriptsDir, 'agent.old')
		logger.info(f'Attempting to download {agentUrl} to {saveToFile}...')
		try:
			r = requests.get(agentUrl, stream=True)
			if r.status_code != 200:
				logger.error(f'Failed to download {agentUrl}. Status Code: {r.status_code}')
				return(False)
			with open(saveToFile, 'wb') as f:
				for chunk in r.iter_content(chunk_size=chunkSize):
					if chunk:
						f.write(chunk)
		except Exception as e:
			logger.error(f'Failed to download {agentUrl} to {saveToFile}. Reason: {e}')
		newCollHash = getSha256Hash(saveToFile)
		logger.info(f'Downloaded Hash: {newCollHash} | Server Hash: {collHashPy}')
		if newCollHash == collHashPy:
			logger.info(f'Attempting to rename {saveToFile} to {agentPath}')
			try:		# rename the current agent to .old
				os.rename(agentPath, oldAgent)
			except Exception as e:
				logger.error(f'Failed to rename {agentPath} to {oldAgent}. Reason: {e}')
				sys.exit()
			try:		# rename the agent.new to agent.py
				os.rename(saveToFile, agentPath)
				logger.info(f'Successfully upgraded {agentUrl} to {saveToFile}')
				logger.info('New agent will run on next cycle')
			except Exception as e:
				logger.error(f'Failed to rename {saveToFile} to {agentPath}. Reason: {e}')
			try:		# remove the .old agent
				os.remove(oldAgent)
				logger.info(f'Deleted {oldAgent}')
			except Exception as e:
				logger.error(f'Failed to remove {oldAgent}')
		else:
			logger.error('Hashes do not match. Deleting download.')
			try:
				os.remove(saveToFile)
			except Exception as e:
				logger.error(f'Failed to delete {saveToFile}. Reason: {e}')
		
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
		deviceUuid 	= configDict['deviceuuid']
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
		appDir 		= 'c:\\program files (x86)\\Wegweiser\\'
	else:
		appDir 		= '/opt/Wegweiser/'
	logDir 		= os.path.join(appDir, 'Logs', '')
	configDir 	= os.path.join(appDir, 'Config', '')
	filesDir	= os.path.join(appDir, 'files', '')
	scriptsDir	= os.path.join(appDir, 'Scripts', '')
	tempDir 	= os.path.join(appDir, 'Temp', '')

	checkDirs([appDir, logDir, configDir, tempDir, filesDir])
	return(appDir, logDir, configDir, tempDir, filesDir, scriptsDir)

def getLocalAgentVersion(configDir):
	with open(os.path.join(configDir, 'agentVersion.txt'), 'r') as f:
		localAgentVersion = f.read().strip()
	logger.info(f'localAgentVersion: {localAgentVersion}')
	return(localAgentVersion)

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

appDir, \
	logDir, \
	configDir, \
	tempDir, \
	filesDir, \
	scriptsDir		= getAppDirs()
configFile 			= f'{configDir}agent.config'
deviceUuid, \
	host			= getDeviceUuid(configFile)
localAgentVersion	= getLocalAgentVersion(configDir)

agentUpdateReqd, \
collHashPy, \
collHashWin		= getServerCollVersion(localAgentVersion)

if agentUpdateReqd == True:
	updateAgent(collHashPy, collHashWin)
	sys.exit('Exiting after update.')