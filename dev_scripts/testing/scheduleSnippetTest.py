# Filepath: tools/scheduleSnippetTest.py
# Filepath: tools/sendEventTest.py
import requests
from logzero import logger
import json


################# FUNCTIONS #################

def sendJsonPayloadFlask(payload, host, endpoint):
	url 		= f'https://{host}{endpoint}'
	if debugMode == True:
		logger.debug(f'payload to send: {payload}')
		logger.debug(f'Attempting to connect to {url}')
	headers 	= {'Content-Type': 'application/json'}
	response 	= requests.post(url, headers=headers, data=json.dumps(payload))
	return(response)

def getDelayedStartTime(minsDelay):
	from datetime import datetime, timedelta
	now 				= datetime.now()
	delayedStartTime 	= (now + timedelta(minutes=minsDelay)).strftime("%H:%M")
	return(delayedStartTime)

################# VARIABLES #################

debugMode 		= True
host 			= 'app.wegweiser.tech'
endpoint 		= '/snippets/schedulesnippet'

snippetDict = {
	'zipLogs.py': 		'd99ead32-4247-4d0d-88af-7d81a225a663',
	'fullAudit.py':		'd9cc5e94-539e-4d25-89b6-5b8681ba674e',
	'quickCheckin.py':	'ae647bec-c1df-4a3a-9d6a-b4df00c207b4'
}



################# MAIN #################

mode 				= 'NORMAL' # TEST / NORMAL
deviceUuid 			= input('Enter deviceUuid: ')

if mode == 'NORMAL': # Schedules the default required snippets

	## updateAgent.py
	# payload = {
	# 	'snippetuuid': 	snippetDict['updateAgent.py'], 
	# 	'deviceuuid': 	deviceUuid,
	# 	'recstring': 	'5m',
	# 	'starttime': 	getDelayedStartTime(2)}
	# logger.info(f'Attempting to schedule updateAgent')    
	# response 		= sendJsonPayloadFlask(payload, host, endpoint)
	# logger.debug(f'response: {response.text}')
	# if response.status_code == 200:
	# 	logger.info(f'Successfully scheduled updateAgent')
	# else:
	# 	logger.error(f'Failed to scheduled updateAgent')

	### zipLogs.py
	payload = {
		'snippetuuid': 	snippetDict['zipLogs.py'], 
		'deviceuuid': 	deviceUuid,
		'recstring': 	'1d',
		'starttime': 	'00:00'}
	logger.info(f'Attempting to schedule zipLogs')
	response 		= sendJsonPayloadFlask(payload, host, endpoint)
	logger.debug(f'response: {response.text}')
	if response.status_code == 200:
		logger.info(f'Successfully scheduled zipLogs')
	else:
		logger.error(f'Failed to scheduled zipLogs')

	### fullAudit.py
	payload = {
			'snippetuuid': 	snippetDict['fullAudit.py'], 
			'deviceuuid': 	deviceUuid,
			'recstring': 	'1d',
			'starttime': 	getDelayedStartTime(3)}
	logger.info(f'Attempting to schedule fullAudit')
	response 		= sendJsonPayloadFlask(payload, host, endpoint)
	logger.debug(f'response: {response.text}')
	if response.status_code == 200:
		logger.info(f'Successfully scheduled fullAudit')
	else:
		logger.error(f'Failed to scheduled fullAudit')	

	### quickCheckin.py
	payload = {
			'snippetuuid': 	snippetDict['quickCheckin.py'], 
			'deviceuuid': 	deviceUuid,
			'recstring': 	'5m',
			'starttime': 	getDelayedStartTime(4)}
	logger.info(f'Attempting to schedule quickCheckin')
	response 		= sendJsonPayloadFlask(payload, host, endpoint)
	if response.status_code == 200:
		logger.info(f'Successfully scheduled quickCheckin')
	else:
		logger.error(f'Failed to scheduled quickCheckin')	

elif mode == 'TEST': # Schedules a one-time fullAudit
	payload = {
			'snippetuuid': 	snippetDict['fullAudit.py'], 
			'deviceuuid': 	deviceUuid,
			'recstring': 	'1d',
			'starttime': 	getDelayedStartTime(3)}
	logger.info(f'Attempting to schedule fullAudit')
	response 		= sendJsonPayloadFlask(payload, host, endpoint)
	logger.debug(f'response: {response.text}')
	if response.status_code == 200:
		logger.info(f'Successfully scheduled fullAudit')
	else:
		logger.error(f'Failed to scheduled fullAudit')	

else:
	logger.error(f'Invalid mode: {mode}')





