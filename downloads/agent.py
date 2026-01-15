# Filepath: downloads/agent.py
# Filepath: agent/agent.py
import os
import json
import base64
import argparse
import platform
import sys
import socket
import subprocess
import io
import importlib
import contextlib
try:
	from logzero import logger, logfile
except:
	subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'logzero'])
	from logzero import logger, logfile
try:
	from cryptography.hazmat.primitives.asymmetric import rsa, padding
	from cryptography.hazmat.primitives import serialization, hashes
	from cryptography.hazmat.primitives.serialization import load_pem_public_key, load_pem_private_key
	from cryptography.hazmat.backends import default_backend
except:
	subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'cryptography'])
	from cryptography.hazmat.primitives.asymmetric import rsa, padding
	from cryptography.hazmat.primitives import serialization, hashes
	from cryptography.hazmat.primitives.serialization import load_pem_public_key, load_pem_private_key
	from cryptography.hazmat.backends import default_backend
try:
	import requests
except:
	subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'requests'])
	import requests


####### KEY MANAGEMENT START #######
def genPrivatePem():
	logger.info('Generating private key...')
	privateKey = rsa.generate_private_key(
		public_exponent=65537,
		key_size=1024,
		backend=default_backend
	)
	privatePem = privateKey.private_bytes(
		encoding				=serialization.Encoding.PEM,
		format					=serialization.PrivateFormat.TraditionalOpenSSL,
		encryption_algorithm	=serialization.NoEncryption()
	).decode('utf-8')
	return(privatePem, privateKey)

def genPublicPem(privateKey):
	logger.info('Generating public key...')
	publicKey 	= privateKey.public_key()
	publicPem	= publicKey.public_bytes(
		encoding=serialization.Encoding.PEM,
		format=serialization.PublicFormat.SubjectPublicKeyInfo
	).decode('utf-8')
	return(publicPem)
####### KEY MANAGEMENT END #######


def parseArgs():
	parser = argparse.ArgumentParser()
	parser.add_argument("-g", "--groupUuid",	help = "Enter groupUuid",		required=False)		 
	parser.add_argument("-v", "--version",		help = "Display the version", 	action='store_true')
	parser.add_argument("-d", "--debugMode",	help = "Enable debug Mode", 	action='store_true')
	args = parser.parse_args()	
	return(args)

def obfuscateUuid(uuid):
	uuidPartList 	= uuid.split('-')
	obUuid 			= f'{uuidPartList[4]}'
	return(obUuid)

def getAppDirs():
	if platform.system() == 'Windows':
		appDir 		= 'c:\\program files (x86)\\Wegweiser\\'
	else:
		appDir 		= '/opt/Wegweiser/'
	logDir		= os.path.join(appDir, 'Logs', '')
	configDir	= os.path.join(appDir, 'Config', '')
	agentDir	= os.path.join(appDir, 'Agent', '')
	filesDir	= os.path.join(appDir, 'Files', '')
	snippetsDir = os.path.join(appDir, 'Snippets', '')
	checkDirs([appDir,logDir,configDir,agentDir,filesDir,snippetsDir])
	return(appDir, logDir, configDir, agentDir, filesDir, snippetsDir)

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

def getServerPubPem():
	endpoint 		= '/diags/getserverpublickey'
	url 			= f'https://{host}{endpoint}'
	if debugMode == True:
		logger.debug(f'Attempting to GET {url}...')
	response 		= requests.get(url)
	if debugMode == True:
		logger.debug(f'{url} response: {response.text}')
	serverPubPem	= base64.b64decode(json.loads(response.text)['serverpublickey']).decode('utf-8')
	if debugMode == True:
		logger.debug(f'serverPubPem: {serverPubPem}')
	return(serverPubPem)

def registerDevice(groupuuid, agentPubPem):
	endpoint 		= '/devices/register'
	deviceName 		= socket.gethostname()
	hardwareInfo 	= platform.system()
	payload 		= {'groupuuid': groupuuid, 'devicename': deviceName, 'hardwareinfo': hardwareInfo, 'agentpubpem':agentPubPem}
	response 		= sendJsonPayloadFlask(payload, endpoint)
	if debugMode == True:
		logger.debug(f'response: {response}')
	deviceUuid 		= json.loads(response.text)['deviceuuid']
	logger.info(f'Device issued new deviceUuid: {obfuscateUuid(deviceUuid)}')
	return(deviceUuid)

def writeAgentConfigFile(deviceUuid, agentPrivPem, agentPubPem, serverPubPem, agentConfigFile):
	configDict = {
		'deviceuuid':	deviceUuid, 
		'agentprivpem':	agentPrivPem,
		'agentpubpem':	agentPubPem,
		'serverpubpem':	serverPubPem
		}
	logger.info(f'Attempting to write to {agentConfigFile}')
	try:
		with open(agentConfigFile, 'w') as f:
			f.write(json.dumps(configDict, indent=4))
		logger.info(f'{agentConfigFile} written successfully.')
		return(True)
	except Exception as e:
		logger.error(f'Failed to write to {agentConfigFile}')
		return(False)

def sendJsonPayloadFlask(payload, endpoint):
	url 		= f'https://{host}{endpoint}'
	headers 	= {'Content-Type': 'application/json'}
	if debugMode == True:
		logger.debug(f'Attempting to call {url} | headers: {headers} | payload: {payload}')
	response 	= requests.post(url, headers=headers, data=json.dumps(payload))
	if debugMode == True:
		logger.debug(f'response: {response.text}')
	return(response)

def getAgentConfigDict(agentConfigFile):
	with open(agentConfigFile, 'r') as f:
		agentConfigDict = json.load(f)
	return(agentConfigDict)

def getSignedMessageFromServer():
	endpoint 	= '/diags/testserversigning'
	host 		= 'app.wegweiser.tech'
	url 		= f'https://{host}{endpoint}'
	response 	= requests.get(url)
	return(response.text)

def verifyBase64Signature(snippet, publicKey):
	logger.info('Validating signature...')
	payloadDict 	= json.loads(snippet)
#	logger.debug(f'payloadDict: {payloadDict}')
	payloadb64 		= payloadDict['data']['payload']['payloadb64'].encode()
	payloadsigb64	= payloadDict['data']['payload']['payloadsig'].encode()
	payload 		= base64.b64decode(payloadb64)
	payloadsig 		= base64.b64decode(payloadsigb64)
	try:
		publicKey.verify(
			payloadsig,
			payload,
			padding.PKCS1v15(),
			hashes.SHA256()
		)
		logger.info('Valid signature')
		return(True)
	except Exception as e:
		logger.error(f'Invalid signature. Reason: {e}')
		return(False)

def keysAreInSync(agentConfigDict):
	logger.info('Getting server public key...')
	serverPubPemServer 	= getServerPubPem()
	serverPubPemAgent	= agentConfigDict['serverpubpem']
	if serverPubPemServer == serverPubPemAgent:
		logger.info('The agents copy of the server\'s public key is up to date.')
		return(True)
	else:
		logger.warning('The agents copy of the server\'s public key is different.')
		return(False)
	
def resyncServersPubKey(agentConfigDict):
	agentConfigDict['serverpubpem'] = getServerPubPem()
	with open(agentConfigFile, 'w') as f:
		f.write(json.dumps(agentConfigDict, indent=4))
	logger.info(f'{agentConfigFile} written successfully.')
	return(True)

def checkAgentConfigFile():
	if not os.path.isfile(agentConfigFile):
		logger.warning(f'Agent config file {agentConfigFile} does not exist. Attempting to register...')
		if not args.groupUuid:
			logger.error('GroupUUID not specified with -g switch. Unable to register device.')
			sys.exit()
		agentPrivPem, \
			privateKey 	= genPrivatePem()
		agentPubPem 	= genPublicPem(privateKey)
		serverPubPem 	= getServerPubPem()
		groupUuid 		= args.groupUuid
		agentUuid 		= registerDevice(groupUuid, agentPubPem)
		writeSuccess 	= writeAgentConfigFile(agentUuid, agentPrivPem, agentPubPem, serverPubPem, agentConfigFile)

def getServerPubKey(serverPubPem):
	try:
		serverPubKey 	= serialization.load_pem_public_key(serverPubPem.encode())
	except Exception as e:
		logger.error(f'Failed to validate server Public Key. Reason: {e}\nQuitting.')
		sys.exit()
	return(serverPubKey)

def testKeys():
	responseJson 		= getSignedMessageFromServer()
	serverPubKey 		= getServerPubKey(agentConfigDict['serverpubpem'])
	if not verifyBase64Signature(responseJson, serverPubKey):
		logger.error(f'Agent cannot validate server messages. This is either due to {agentConfigFile} ')
		if keysAreInSync(agentConfigDict):
			logger.error(f'Agent cannot validate server messages. Keys are in sync, but something else is wrong.')
			return(False)
		else:
			logger.error(f'The agent key does not match the server\'s key. Re-syncing...')
			if resyncServersPubKey(agentConfigDict) == True:
				return(True)
			else:
				return(False)
			
def getPendingSnippetsFromServer(deviceUuid):
	scheduleUuidList	= []
	snippetDict			= {}
	logger.info(f'Getting pending snippets from server...')
	endpoint 			= f"/snippets/pendingsnippets/{deviceUuid}"
	url 				= f'https://{host}{endpoint}'
	response 			= requests.get(url)
	snippetDict			= json.loads(response.text)
	scheduleUuidList 	= snippetDict['data']['scheduleList']
	if len(scheduleUuidList) == 0:
		logger.info('No pending snippets.')
	else:
		logger.debug(f'Found {len(scheduleUuidList)} pending snippet(s)...')
	return(scheduleUuidList)

def downloadSnippet(scheduleUuid, snippetsDir):
	endpoint 		= f'/snippets/getsnippetfromscheduleuuid/{scheduleUuid}'
	if debugMode == True:
		logger.debug(f'Attempting to download snippet from: https://{host}{endpoint}')
	try:
		responseJson	= requests.get(f'https://{host}{endpoint}').text
		downloadSnippetSuccess = True
	except Exception as e:
		logger.error(f'Failed to download: https://{host}{endpoint}')
		sys.exit()
	if debugMode == True:
		logger.debug(f'Attempting to save to {os.path.join(snippetsDir, scheduleUuid)}')
	with open(os.path.join(snippetsDir, scheduleUuid), 'w') as f:
		f.write(responseJson)

def decodeSnippet(responseJson):
	snippetCode = base64.b64decode(json.loads(responseJson)['data']['payload']['payloadb64']).decode('utf-8')
	snippetName = json.loads(responseJson)['data']['settings']['snippetname']
	return(snippetCode, snippetName)

def runSnippet(snippetCode, snippetName, scheduleUuid):
	logger.info(f'Running snippet \"{snippetName}\" ({obfuscateUuid(scheduleUuid)})')
	execComplete	= False
	result 			= 'No output generated'
	if platform.system() == 'Windows':
		pythonAppPath = 'c:\\program files (x86)\\Wegweiser\\Agent\\python-weg\\python.exe'
	elif platform.system() == 'Linux':
		pythonAppPath = '/opt/Wegweiser/Agent/python-weg/bin/python3'
	elif platform.system() == 'Darwin':
		pythonAppPath = '/opt/Wegweiser/Agent/python-weg/bin/python3'
	else:
		logger.error(f'Unsupported platform: {platform.system()}')
	
	currentSnippetPath = os.path.join(snippetsDir, f'current-{scheduleUuid}')
	with open(currentSnippetPath, 'w') as f:
		f.write(snippetCode)
	try:
		result = subprocess.run([pythonAppPath, currentSnippetPath], capture_output=True, text=True)
		result = result.stderr
		execStatus = 'SUCCESS'
		logger.info(f'{snippetName} ({obfuscateUuid(scheduleUuid)}) execution SUCCESS')
		os.remove(currentSnippetPath)
	except Exception as e:
		logger.error(f'Failed running snippet ({snippetName}). Reason: {e}')
		execStatus = 'EXECFAIL'
	finally:
		execComplete = True
		logger.info(f'Running snippet end.')
	return(execComplete, execStatus, result)

def sendSnippetCompleteMessage(scheduleUuid, execStatus):
	endpoint 	= f'/snippets/sendscheduleresult/{scheduleUuid}'
	url 		= f'https://{host}{endpoint}'
	body = {
		'scheduleuuid': scheduleUuid,
		'execstatus': execStatus
	}
	headers 	= {'Content-Type': 'application/json'}
	logger.info('Sending completed message.')
	response 	= requests.post(url, headers=headers, data=json.dumps(body))
	return(response)	

def formatAppVersion(appVersion):
	friendlyVersion = f'Version: {appVersion[:4]}.{appVersion[4:6]}.{appVersion[6:8]}.{appVersion[8:]}'
	return(friendlyVersion)

def getImports(snippet):
	importsList = []
	for line in snippet.splitlines():
		print(f'line: {line}')
		if 'import' in line:
			print(f'import line: {line}')
			importsList.append(line.split('import')[1].strip())
	logger.debug(f'Imported: {importsList}')	
	for importItem in importsList:
		globals()[importItem] = importlib.import_module(importItem)
	logger.debug(f'getImports completed.')

def writeLocalAgentVersion(configDir, appVersion):
	agentVersionFile = f'{configDir}agentVersion.txt'
	if os.path.isfile(agentVersionFile):
		logger.debug(f'{agentVersionFile} exists...')
		with open(agentVersionFile, 'r') as f:
			try:
				localAgentVersion = f.read().strip()
				logger.debug(f'localAgentVersion: {localAgentVersion}')
			except Exception as e:
				logger.error(f'Failed to read the agentversion from {agentVersionFile}')
				localAgentVersion = '0'
	else:
		localAgentVersion = '0'
	if localAgentVersion != appVersion:
		with open(agentVersionFile, 'w') as f:
			logger.info(f'Updating {agentVersionFile} from {localAgentVersion} to {appVersion}')
			f.write(f'{appVersion}')
	else:
		logger.info(f'{agentVersionFile} up to date. Version: {localAgentVersion}')

def isDownloadNeeded(snippetPath):
	if os.path.isfile(snippetPath):
		return(False)
	else:
		return(True)

############################# MAIN #############################


appName 		= 'wegweiserAgent'
appVersion		= '202410161430'
host 			= 'app.wegweiser.tech'
port 			= 443
args			= parseArgs()
debugMode 		= args.debugMode

if args.version:
	print(f'{appName}\n{formatAppVersion(appVersion)}')
	sys.exit()

appDir, \
	logDir, \
	configDir, \
	agentDir, \
	filesDir, \
	snippetsDir	= getAppDirs()

logfile(f'{logDir}{appName}.log')
logger.info(f'{appName} {formatAppVersion(appVersion)}')
logger.info(f'logFile: {logDir}{appName}.log')
logger.info(f'debugMode: {debugMode}')

writeLocalAgentVersion(configDir, appVersion)

agentConfigFile 	= f'{configDir}agent.config'
checkAgentConfigFile()
agentConfigDict 	= getAgentConfigDict(agentConfigFile)
serverPubKey 		= getServerPubKey(agentConfigDict['serverpubpem'])
deviceUuid 			= agentConfigDict['deviceuuid']
keysAreGood 		= keysAreInSync(agentConfigDict)

if keysAreGood == False:
	logger.error('There is a problem with the keys. Quitting.')
	sys.exit()

############################# RUN SNIPPETS #############################


scheduleUuidList	= getPendingSnippetsFromServer(deviceUuid)

for scheduleUuid in scheduleUuidList:
	snippetPath 	= os.path.join(snippetsDir, scheduleUuid)
	if isDownloadNeeded(snippetPath) == True:
		logger.info(f'{snippetPath} does not exist. Downloading...')
		downloadSnippet(scheduleUuid, snippetsDir)
	else:
		logger.info(f'{snippetPath} already downloaded.')

	with open(snippetPath, 'r') as f:
		snippet = f.read()

	if verifyBase64Signature(snippet, serverPubKey) == True:
		snippetCode, \
		snippetName 	= decodeSnippet(snippet)

		execComplete, \
		execStatus, \
		execOutput		= runSnippet(snippetCode, snippetName, scheduleUuid)
		spaceLength 	= 49 + len(snippetName)
		logger.debug('\n' + '='*spaceLength + f'\n=== Snippet: {snippetName} ({obfuscateUuid(scheduleUuid)}) execOutput ===\n' + '='*spaceLength + '\n' + f'{execOutput}\n' + '='*spaceLength)
		logger.info(f'execResult: {execComplete} | execStatus: {execStatus}')
		sendSnippetCompleteMessage(scheduleUuid, execStatus)
	









