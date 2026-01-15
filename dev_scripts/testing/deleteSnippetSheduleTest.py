# Filepath: tools/deleteSnippetSheduleTest.py
# Filepath: tools/sendEventTest.py
import requests
from logzero import logger
import json



def sendJsonPayloadFlask(payload, endpoint):
	url 		= f'https://{host}{endpoint}'
	if debugMode == True:
		logger.debug(f'payload to send: {payload}')
		logger.debug(f'Attempting to connect to {url}')
	headers 	= {'Content-Type': 'application/json'}
	response 	= requests.get(url)
	return(response)


debugMode 		= True
host 			= 'app.wegweiser.tech'

scheduleUuid    = 'd6dcadac-12b9-4891-94db-95c75d12836f'
endpoint 		= f'/snippets/deleteschedule/{scheduleUuid}'
url 		    = f'https://{host}{endpoint}'


response 	    = requests.get(url)

logger.info(f'response: {response}')
logger.info(f"respose.content: {response.content.decode('utf-8')}")


