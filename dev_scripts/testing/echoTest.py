# Filepath: tools/echoTest.py
import requests
from logzero import logger
import time
import json

def sendJsonPayloadFlask(endpoint, payload):
	url 		= f'https://{host}{endpoint}'
	logger.info(f'Attempting to connect to {url}')
	logger.info(f'sending: {json.dumps(payload)}')
	headers 	= {'Content-Type': 'application/json'}
	response 	= requests.post(url, headers=headers, data=json.dumps(payload))
	return(response)

debugMode 		= True
host 			= 'app.wegweiser.tech'
endpoint 		= '/diags/echo'
payload 		= {'currentTime':int(time.time()),'name':'bonnie'}


response 		= sendJsonPayloadFlask(endpoint, payload)

logger.info(f'response: {response}')
logger.info(f"respose.content: {response.content.decode('utf-8')}")