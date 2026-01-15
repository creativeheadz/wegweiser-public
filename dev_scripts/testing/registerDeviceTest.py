# Filepath: tools/registerDeviceTest.py
import requests
from logzero import logger
import time
import json
import socket

def sendJsonPayloadFlask(endpoint, payload):
	url 		= f'https://{host}{endpoint}'
	logger.info(f'Attempting to connect to {url}')
	logger.info(f'sending: {json.dumps(payload)}')
	headers 	= {'Content-Type': 'application/json'}
	response 	= requests.post(url, headers=headers, data=json.dumps(payload))
	return(response)

debugMode 		= True
host 			= 'app.wegweiser.tech'
endpoint 		= '/devices/register'
payload 		= {'groupuuid':'f1a037a7-6a2c-4c37-a6df-03491fad89cf', 'devicename': socket.gethostname()}


response 		= sendJsonPayloadFlask(endpoint, payload)

logger.info(f'response: {response}')
logger.info(f"respose.content: {response.content.decode('utf-8')}")