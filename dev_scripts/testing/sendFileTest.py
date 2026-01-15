# Filepath: tools/sendFileTest.py
import requests
from logzero import logger
import os
import uuid
import zipfile


def createDummyFile(dummyFile):
	with open (dummyFile, 'wb') as f:
		f.write(os.urandom(1024*1024))
	return(dummyFile)

def zipFile(filetoZip):
	zippedDummy	= filetoZip + '.zip'
	logger.info(f'Zipping {dummyFile} to {zippedDummy}')
	with zipfile.ZipFile(zippedDummy, 'w', compression=zipfile.ZIP_DEFLATED) as zipf:
		zipf.write(dummyFile, os.path.basename(dummyFile))
	logger.info(f'Successfully zipped {dummyFile} to {zippedDummy}')
	return(zippedDummy)

def sendJsonPayloadFlask(endpoint, fileToSend, deviceUuid):
	payloadName = os.path.basename(fileToSend)						# this is the name of the file that you are sending (not the path)
	logger.debug(f'payloadName: {payloadName}')						# print the payloadName
	url 		= f'https://{host}{endpoint}'						# build the URL with the host and the endpoint
	headers 	= {'deviceuuid': deviceUuid}						# the head needs to contain a valid deviceUuid
	logger.debug(f'Attempting to connect to {url}')					# print the url
	with open(fileToSend, 'rb') as f:								# open the file that you are going to send for reading
		files = {'file': (payloadName, f)}							# specify the "files" part of the request
		response = requests.post(url, files=files, headers=headers)	# make the POST call with the "files" and the "header"
	return(response)


debugMode 		= True
host 			= 'app.wegweiser.tech'
endpoint 		= '/payload/sendfile'
dummyFile 		= '/tmp/jimy123.txt.old'							# dummy file name
deviceUuid 		= 'bc4e78c5-fa47-4f7d-b070-f1b5976be22c'			# valid deviceUuid

filetoZip		= createDummyFile(dummyFile)
fileToSend 		= zipFile(filetoZip)


response 		= sendJsonPayloadFlask(endpoint, fileToSend, deviceUuid)


logger.info(f'response: {response}')
logger.info(f"respose.content: {response.content.decode('utf-8')}")


