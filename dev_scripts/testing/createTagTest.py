# Filepath: tools/createTagTest.py
import requests
from logzero import logger
import time
import json
import random
import string

def sendJsonPayloadFlask(endpoint, payload, mode):
	url 		= f'https://{host}{endpoint}'
	logger.info(f'Attempting to connect to {url}')
	logger.info(f'sending: {json.dumps(payload)}')
	headers 	= {'Content-Type': 'application/json'}
	if mode == 'POST':
		response 	= requests.post(url, headers=headers, data=json.dumps(payload))
	elif mode == 'DELETE':
		response 	= requests.delete(url, headers=headers, data=json.dumps(payload))
	return(response)

def createTag(tenantuuid, tagvalue):
	payload 		= {'tenantuuid': tenantuuid, 'tagvalue':tagvalue}
	logger.info(f'Attempting to create tag: {tagvalue}...')
	endpoint 		= '/tags/create'
	response 		= sendJsonPayloadFlask(endpoint, payload, 'POST')
	logger.info(f'tenantuuid: {tenantuuid}')
	logger.info(f'Creating tagvalue: {tagvalue}')
	logger.info(f'response: {response}')
	logger.info(f"respose.content: {response.content.decode('utf-8')}")
	data = json.loads(response.content)
	taguuid = data['taguuid']
	print(f'taguuid: {taguuid}')
	return(taguuid)

def assignTag(deviceuuid, taguuid):
	payload 		= {'deviceuuid': deviceuuid, 'taguuid':taguuid}
	logger.info(f'Attempting to assign tag: {taguuid} to device {deviceuuid}...')
	endpoint 		= '/tags/assign/device'
	response 		= sendJsonPayloadFlask(endpoint, payload, 'POST')
	logger.info(f'response: {response}')
	logger.info(f"respose.content: {response.content.decode('utf-8')}")

def unAssignTag(deviceuuid, taguuid):
	payload 		= {'deviceuuid': deviceuuid, 'taguuid':taguuid}
	logger.info(f'Attempting to assign tag: {taguuid} to device {deviceuuid}...')
	endpoint 		= '/tags/unassign/device'
	response 		= sendJsonPayloadFlask(endpoint, payload, 'DELETE')
	logger.info(f'response: {response}')
	logger.info(f"respose.content: {response.content.decode('utf-8')}")	

def deleteTag(taguuid):
	payload 		= {'taguuid':taguuid}
	logger.info(f'Attempting to delete tag: {taguuid}...')
	endpoint 		= '/tags/delete'
	response 		= sendJsonPayloadFlask(endpoint, payload, 'DELETE')
	logger.info(f'response: {response}')
	logger.info(f"respose.content: {response.content.decode('utf-8')}")	

######################## MAIN ########################

debugMode 		= True
host 			= 'app.wegweiser.tech'
tagvalue 		= ''.join(random.choices(string.ascii_lowercase, k=8))
tenantuuid		= 'd7f55679-f0ad-402b-a0bb-dc8f870d1c5d'
deviceuuid1		= '62e59d40-ec03-4587-baf4-1579b5f5f844'
deviceuuid2		= '62e59d40-ec03-4587-baf4-1579b5f5f844'

#deleteTag('aa4c60dc-a02d-4783-a49a-83644ccdf22b')
#input(f'Check that the taguuid {taguuid} has been deleted and unassigned from {deviceuuid2}')
#quit()
taguuid = createTag(tenantuuid, tagvalue)
input(f'Check that the tagvalue {tagvalue} ({taguuid}) has been created...')

assignTag(deviceuuid1, taguuid)
input(f'Check that the taguuid {taguuid} has been assigned to deviceuuid {deviceuuid1}')

assignTag(deviceuuid2, taguuid)
input(f'Check that the taguuid {taguuid} has been assigned to deviceuuid {deviceuuid2}')

unAssignTag(deviceuuid1, taguuid)
input(f'Check that the taguuid {taguuid} has been unassigned from deviceuuid {deviceuuid1}')

deleteTag(taguuid)
input(f'Check that the taguuid {taguuid} has been deleted and unassigned from {deviceuuid2}')