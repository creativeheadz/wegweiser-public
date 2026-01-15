# Filepath: agent/signFile.py
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pem_private_key, load_pem_public_key
from cryptography.hazmat.backends import default_backend
import base64
import json
import os
import uuid
import time
import socket
from logzero import logger


def loadPrivKey(privateKeyFile, password=None):
	with open(privateKeyFile, 'rb') as keyFile:
		privateKey = load_pem_private_key(keyFile.read(), password=password, backend=default_backend())
	return (privateKey)

def loadPubKey(publicKeyfile):
	with open(publicKeyfile, "rb") as keyFile:
		publicKey = load_pem_public_key(keyFile.read(), backend=default_backend())
	return (publicKey)

def signBase64String(base64String, privateKey):
	decoded_message = base64.b64decode(base64String)
	signature = privateKey.sign(
		decoded_message,
		padding.PKCS1v15(),
		hashes.SHA256()
	)
	b64Sig = base64.b64encode(signature).decode()
	return(b64Sig)

def verifyBase64Signature(base64String, base64Signature, publicKey):
	try:
		decoded_message 	= base64.b64decode(base64String)
	except Exception as e:
		print(f'Failed to decode the message. Reason: {e}')
	try:
		decoded_signature 	= base64.b64decode(base64Signature)
	except Exception as e:
		print(f'Failed to decode the signature. Reason: {e}')
	try:
		publicKey.verify(
			decoded_signature,
			decoded_message,
			padding.PKCS1v15(),
			hashes.SHA256()
		)
		print('Valid signature')
	except Exception as e:
		print('Invalid signature')

def b64encodeFile(filePath):
	with open(filePath, "rb") as f:
		plainText 	= f.read()
		encodedText	= base64.b64encode(plainText)
	return(encodedText)

def buildSnippetSettings(snippetDict, snippetUuid, inFile):
	outFile 								= f'{snippetUuid}.json'
	snippetDict['settings'] 				= {}
	snippetDict['settings']['snippetUuid'] 	= str(snippetUuid)
	snippetDict['settings']['snippetname'] 	= os.path.splitext(os.path.basename(inFile))[0]
	snippetDict['settings']['snippettype'] 	= os.path.splitext(os.path.basename(inFile))[1]
	snippetDict['settings']['created_at'] 	= int(time.time())
	return(snippetDict)

def buildSnippetPayload(snippetDict, privateKeyFile, password):
	privateKey 								= loadPrivKey(privateKeyFile, password=password)
	encodedText								= b64encodeFile(inFile)
	base64Signature							= signBase64String(encodedText, privateKey)
	snippetDict['payload'] 					= {}
	snippetDict['payload']['payloadsig']	= str(base64Signature)
	snippetDict['payload']['payloadb64'] 	= str(encodedText.decode('utf-8'))
	return(snippetDict)

def writeSnippetJson(snippetDir, snippetDict, snippetUuid, tenantUuid):
	outDir =  os.path.join(snippetOutDir, tenantUuid)
	os.makedirs(outDir, exist_ok=True)			
	outFile = os.path.join(outDir, snippetUuid + '.json')
	print(f'Writing to {outFile}')
	with open(outFile, 'w') as f:
		json.dump(snippetDict, f)
	print(f'Saved to {outFile}')
	return(outFile)
		
def validateFile(snippetJsonFile, publicKeyFile):
	print(f'Validating {snippetJsonFile}...')
	with open(snippetJsonFile, 'r') as f:
		snippetDict = json.load(f)
	publicKey 	= loadPubKey(publicKeyFile)
	verifyBase64Signature(snippetDict['payload']['payloadb64'], snippetDict['payload']['payloadsigb64'], publicKey)

def checkInputs(inFilePath):
	if not os.path.isfile(inFilePath):
		logger.error(f'{inFilePath} does nost exist. Quitting.')
		quit()
	if not os.path.isfile(privateKeyFile):
		logger.error(f'{privateKeyFile} does nost exist. Quitting.')
		quit()
	if not os.path.isfile(publicKeyfile):
		logger.error(f'{publicKeyfile} does nost exist. Quitting.')
		quit()

def genSnippetsSql(snippetDict, tenantUuid, maxExecSecs):
	snippetsSql = f"""
INSERT INTO snippets (
	snippetuuid,
	tenantuuid,
	snippetname,
	created_at,
	max_exec_secs
	)
values (
	\'{snippetDict['settings']['snippetUuid']}\',
	\'{tenantUuid}\',
	\'{snippetDict['settings']['snippetname']}{snippetDict['settings']['snippettype']}\',
	{snippetDict['settings']['created_at']},
	{maxExecSecs}
	);"""
	return(snippetsSql)

def genSnippetsScheduleSql(snippetUuid, deviceUuid, recurrence, interval):
	if deviceUuid.upper() == 'ALL':
		snippetsScheduleSql = f"""
INSERT INTO snippetsschedule (
	scheduleuuid,
	snippetuuid,
	deviceuuid,
	recurrence,
	interval,
	nextexecution
)
select 
	uuid_generate_v4(),
	\'{snippetUuid}\',
	deviceuuid,
	{recurrence},
	{interval},
	{int(time.time())}
from
	devices;"""
	elif deviceUuid.upper() == 'TEST':
		snippetsScheduleSql = f"""
INSERT INTO snippetsschedule (
	scheduleuuid,
	snippetuuid,
	deviceuuid,
	recurrence,
	interval,
	nextexecution
)
values (
	\'{str(uuid.uuid4())}\',
	\'{snippetUuid}\',
	'3d6669a8-bdf2-43c6-a635-0051d2eb923a',
	{recurrence},
	{interval},
	{int(time.time())}
);"""
	else:
		snippetsScheduleSql = f"""
INSERT INTO snippetsschedule (
	scheduleuuid,
	snippetuuid,
	deviceuuid,
	recurrence,
	interval,
	nextexecution
)
values (
	\'{str(uuid.uuid4())}\',
	\'{snippetUuid}\',
	\'{deviceUuid}\',
	{recurrence},
	{interval},
	{int(time.time())}
);"""
	return(snippetsScheduleSql)

def writeSql(sql):
	with open('/tmp/snippets.sql', 'a') as f:
		f.write(f'{sql}\n-----------\n')

def clearSqlFile():
	with open ('/tmp/snippets.sql', 'w') as f:
		pass

def getSnippetFiles(remoteDirBase):
	toProcessList = []
	for file in os.listdir(remoteDirBase):
		logger.debug(file)
		if file.endswith('.py') or file.endswith('.ps1'):
			toProcessList.append(file)
	return(toProcessList)

def checkInputs():
	if not os.path.isfile(inFile):
		logger.error(f'{inFile} does not exist. Quitting.')
		quit()
	if not os.path.isfile(privateKeyFile):
		logger.error(f'{privateKeyFile} does not exist. Quitting.')
		quit()
	if not os.path.isfile(publicKeyfile):
		logger.error(f'{publicKeyfile} does not exist. Quitting.')
		quit()

def recStringToSeconds(recString):
	logger.debug(f'{recString} | {type(recString)}')
	if int(recString) == 0:
		recurrence 	= 0
		interval	= 0
	else:
		units = {
			's': 1,         
			'm': 60,
			'h': 3600,
			'd': 86400
		}
		try:
			interval 	= int(''.join(filter(str.isdigit, recString)))
			unit 		= ''.join(filter(str.isalpha, recString))
		except ValueError:
			raise ValueError(f"Invalid time format: {recString}")
		if unit not in units:
			raise ValueError(f"Unknown time unit: {unit}")
		recurrence 	= units[unit]
	print(f'recurrence: {recurrence} | interval: {interval}')
	return(recurrence, interval)


####################### MAIN #######################

inFile 			= input('Enter file to convert to JSON snippet: ')
tenantUuid 		= '00000000-0000-0000-0000-000000000000'
tempDir 		= '/tmp/'
computerName 	= socket.gethostname()
print(f'computerName: {computerName}')

unsignedFolder 	= 'wegweiser/snippets/unSigned/'
signedFolder 	= 'wegweiser/snippets/'

if computerName.upper() == 'WegweiserAppServer':
	snippetInDir 	= f'/opt/{unsignedFolder}'
	snippetOutDir 	= f'/opt/{signedFolder}'
	keyDir 			= f'/opt/wegweiser/includes'
else:
	snippetInDir 	= f'/opt/{unsignedFolder}'
	snippetOutDir 	= f'/opt/{signedFolder}'
	keyDir 			= f'/opt/wegweiser/includes/'


inFile				= os.path.join(snippetInDir, inFile)
privateKeyFile 		= os.path.join(keyDir, 'serverPrivKey.pem')
publicKeyfile 		= os.path.join(keyDir, 'serverPubKey.pem')
password 			= None
snippetUuid			= str(uuid.uuid4())

checkInputs()
maxExecSecs			= input('Enter Maximum execution time: ')

snippetDict 		= {}
snippetDict 		= buildSnippetSettings(snippetDict, snippetUuid, inFile)
snippetDict 		= buildSnippetPayload(snippetDict, privateKeyFile, password)
outFile 			= writeSnippetJson(snippetOutDir, snippetDict, snippetUuid, tenantUuid)

snippetsSql			= genSnippetsSql(snippetDict, tenantUuid, maxExecSecs)
print(f'SQL:\n------------------------\n{snippetsSql}\n')

#deviceUuid 			= input('Enter deviceuuid to schedule on (ALL for all, TEST for test machine): ')
#recString			= input('Enter recurrence. e.g., 1h, 2d, 5m: ')
#recurrence, \
#	interval 		= recStringToSeconds(recString)

#snippetsScheduleSql	= genSnippetsScheduleSql(snippetUuid, deviceUuid, recurrence, interval)

#print(f'SQL:\n------------------------\n{snippetsSql}\n')
#print(f'{snippetsScheduleSql}\n-------------------------\n')
