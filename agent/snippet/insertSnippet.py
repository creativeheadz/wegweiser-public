# Filepath: agent/insertSnippet.py
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
from datetime import datetime, timedelta



def genSnippetsScheduleSql(snippetUuid, deviceUuid, recurrence, interval, startTimeEpoch):
	if deviceUuid.upper() == 'ALL':
		snippetsScheduleSql = f"""
INSERT INTO snippetsschedule (
	scheduleuuid,
	snippetuuid,
	deviceuuid,
	recurrence,
	interval,
	nextexecution,
	inprogress,
	enabled
)
select 
	uuid_generate_v4(),
	\'{snippetUuid}\',
	deviceuuid,
	{recurrence},
	{interval},
	{startTimeEpoch},
	False,
	True
from
	snippetsschedule
group by
	deviceuuid;"""

	elif deviceUuid.upper() == 'TEST':
		snippetsScheduleSql = f"""
INSERT INTO snippetsschedule (
	scheduleuuid,
	snippetuuid,
	deviceuuid,
	recurrence,
	interval,
	nextexecution,
	inprogress,
	enabled
)
values (
	\'{str(uuid.uuid4())}\',
	\'{snippetUuid}\',
	'3d6669a8-bdf2-43c6-a635-0051d2eb923a',
	{recurrence},
	{interval},
	{startTimeEpoch},
	False,
	True
);"""

	else:
		snippetsScheduleSql = f"""
INSERT INTO snippetsschedule (
	scheduleuuid,
	snippetuuid,
	deviceuuid,
	recurrence,
	interval,
	nextexecution,
	inprogress,
	enabled
)
values (
	\'{str(uuid.uuid4())}\',
	\'{snippetUuid}\',
	\'{deviceUuid}\',
	{recurrence},
	{interval},
	{startTimeEpoch},
	False,
	True
);"""
	return(snippetsScheduleSql)


def recStringToSeconds(recString):
	if recString.isdigit():
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

def getEpochTime(startTime):
	if startTime == '0':
		startTimeEpoch = int(time.time())
	else:
		now 		= datetime.now()
		inputTime 	= datetime.strptime(startTime, "%H:%M").time()
		inputToday 	= datetime.combine(now.date(), inputTime)
		if inputToday < now:
			inputToday += timedelta(days=1)
		startTimeEpoch	= int(inputToday.timestamp())
	return(startTimeEpoch)

####################### MAIN #######################

tenantUuid 			= '00000000-0000-0000-0000-000000000000'
tempDir 			= '/tmp/'


deviceUuid 			= input('Enter deviceuuid to schedule on (ALL for all, TEST for test machine): ')
snippetUuid 		= input('Enter snippet ID: ')
recString			= input('Enter recurrence. e.g., 1h, 2d, 5m: ')
startTime 			= input('Enter start time hh:mm. 0 if <now>: ')

#deviceUuid 			= 'c8089c23-f95a-45dc-8f35-6f71728be091' # desktop
#snippetUuid 		= '779b5439-f759-4510-af89-e7b995adcfcd' # fullAudit

#deviceUuid 		= '37fd664b-6c45-41c6-af91-21dd39b74071' # hermes
#snippetUuid 		= 'd99ead32-4247-4d0d-88af-7d81a225a663' # zipLogs
#snippetUuid 	 	= '3beed7e2-55ec-4aed-8ba0-88e2ef0a07c3' # update agent



recurrence, \
	interval 		= recStringToSeconds(recString)

startTimeEpoch 		= getEpochTime(startTime)

snippetsScheduleSql	= genSnippetsScheduleSql(snippetUuid, deviceUuid, recurrence, interval, startTimeEpoch)


print(f'{snippetsScheduleSql}\n-------------------------\n')
