# Filepath: tools/sendEventTest.py
import requests
from logzero import logger
import os
import uuid
import zipfile


def createDummyZip():
	dummyFile = '/tmp/dummy.txt'
	with open (dummyFile, 'wb') as f:
		f.write(os.urandom(1024*1024*30))

def zipDummyFile():
	logger.info(f'Zipping {dummyFile} to {zippedDummy}')
	with zipfile.ZipFile(zippedDummy, 'w', compression=zipfile.ZIP_DEFLATED) as zipf:
		zipf.write(dummyFile, os.path.basename(dummyFile))
	logger.info(f'Successfully zipped {dummyFile} to {zippedDummy}')

def sendJsonPayloadFlask(endpoint, dummyFile):
	payloadName = f'{dummyDeviceUuid}.zip'
	url 		= f'https://{host}{endpoint}'
	logger.info(f'Attempting to connect to {url}')
	with open(dummyFile, 'rb') as f:
		files = {'file': (payloadName, f)}
		response = requests.post(url, files=files)
	return(response)


debugMode 		= True
host 			= 'app.wegweiser.tech'
endpoint 		= '/payload/sendeventlog'
dummyFile 		= '/tmp/dummy.txt'
zippedDummy		= '/tmp/dummy.txt.zip'

dummyDeviceUuid = str(uuid.uuid4())
createDummyZip()
zipDummyFile()

response 		= sendJsonPayloadFlask(endpoint, zippedDummy)

logger.info(f'response: {response}')
logger.info(f"respose.content: {response.content.decode('utf-8')}")


