# Filepath: snippets/unSigned/getEventLogs.py
import platform
from logzero import logger
import time
import os
import json
import subprocess 
import sys
import datetime
try:
	import requests
except Exception as e:
	subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'requests'])
	import requests


################# FUNCTIONS #################

def getAppDirs():
	if platform.system() == 'Windows':
		appDir 		= 'c:\\program files (x86)\\Wegweiser\\'
	else:
		appDir 		= '/opt/Wegweiser/'
	logDir 		= os.path.join(appDir, 'Logs', '')
	configDir 	= os.path.join(appDir, 'Config', '')
	tempDir 	= os.path.join(appDir, 'Temp', '')
	filesDir	= os.path.join(appDir, 'Files' , '')
	checkDirs([appDir, logDir, configDir, tempDir, filesDir])
	return(appDir, logDir, configDir, tempDir, filesDir)

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

def getLatestEvent(latestEvtFile):
	logger.debug(f'Getting latest event from {latestEvtFile}...')
	if not os.path.isfile(latestEvtFile):
		logger.info(f'latestEvtFile: {latestEvtFile} does not exist. Setting new start point.')
		latestEvent = 0
	else:
		with open(latestEvtFile, 'r') as f:
			latestEvent = f.readline()
	logger.info(f'Previous latestEvent: {latestEvent}')	
	return(int(latestEvent))

def readLog(log):
	logger.info(f'Reading {log} event log from recordNumber {latestEvent}...')
	objectList 	= []
	h			= win32evtlog.OpenEventLog(None, log)
	logger.debug(f'Total number of records in {log} log: {win32evtlog.GetNumberOfEventLogRecords(h)}')
	while True:
		objects 	= win32evtlog.ReadEventLog(h, win32evtlog.EVENTLOG_BACKWARDS_READ|win32evtlog.EVENTLOG_SEQUENTIAL_READ, 0)
		if not objects:
			logger.info('End of events...')
			break
		for object in objects:	
			if object.RecordNumber > latestEvent:
				objectList.append(object)
			else:
				pass
	return(objectList)

def readExistingLogJson(log):
	eventDictFile = f'{filesDir}events-{log}.json'
	logger.info(f'Checking to see if {eventDictFile} exists...')
	if os.path.isfile(eventDictFile):
		logger.info(f'{eventDictFile} exists. Reading data...')
		with open(eventDictFile, 'r') as f:
			eventDict = json.load(f)
		logger.info(f'eventDict read from file.')
	else:
		logger.info(f'{eventDictFile} does not exist. Creating empty eventDict...')
		eventDict = {}
	return(eventDict)

def processEvents(log, objectList, eventDict):
	now 				= datetime.datetime.now()
	thirtyDaysAgo		= now - datetime.timedelta(days=30)
	for object in objectList:
		if object.TimeGenerated < thirtyDaysAgo:
			logger.debug(f'Skipping: {object.RecordNumber} | {object.TimeGenerated}')
			break
		else:
#			logger.debug(f'Found Record: {object.RecordNumber} | {object.TimeGenerated} | {object.SourceName} | {object.EventID} | {getEventValueToString(object.EventType)} | {win32evtlogutil.SafeFormatMessage(object, log)}')
			eventDict[object.RecordNumber] = {
				'timegenerated': object.TimeGenerated.strftime("%Y-%m-%d-%H:%M:%S"), 
				'sourcename': object.SourceName, 
				'eventid': fixEventId(object.EventID),
				'eventtype': getEventValueToString(object.EventType),
				'message': win32evtlogutil.SafeFormatMessage(object, log)
			}
	return(eventDict)

def writeLogJson(eventDict, log):
	eventDictFile = f'{filesDir}events-{log}.json'
	with open(eventDictFile, 'w') as f:
		f.write(json.dumps(eventDict, indent=4))

def writeLatestEvent(latestEvent, log, objectList):
	latestEvtFile		= f'{configDir}latestEvt-{log}.txt'
	logger.debug(f'Writing latest event to {latestEvtFile}...')
	if len(objectList) > 0:
		latestEvent = objectList[0].RecordNumber
		logger.info(f'New latest Event: {latestEvent}')
		with open(latestEvtFile, 'w') as f:
			f.write(f'{latestEvent}')
	else:
		logger.info('No new events.')
		logger.info(f'New latest Event: {latestEvent} (No change)')	

def zipFile(fileToZip):
	import zipfile
	inFile 		= f'{filesDir}{fileToZip}'
	outZipFile 	= f'{filesDir}{fileToZip}.zip'
	logger.info(f'Zipping {inFile} to {outZipFile}')
	with zipfile.ZipFile(outZipFile, 'w', compression=zipfile.ZIP_DEFLATED) as zipf:
		zipf.write(inFile, os.path.basename(inFile))
	logger.info(f'Successfully zipped {inFile} to {outZipFile}')
	return(outZipFile)

def sendPayloadFlask(route, outZipFile, deviceUuid):
	payloadName 	= os.path.basename(outZipFile)
	url 			= f'https://{host}{route}'
	logger.info(f'Request to send {outZipFile} | payloadName: {payloadName}')
	logger.info(f'Attempting to connect to {url}')
	with open(outZipFile, 'rb') as f:
		files = {'file': (payloadName, f)}
		headers = {'deviceuuid': deviceUuid}
		response = requests.post(url, files=files, headers=headers)
		if response.status_code == 200:
			logger.info(f'status_code: {response.status_code}')
			return(True)
		else:
			logger.error(f'status_code: {response.status_code}. Reason: {response.text}')
			return(False)

def delFile(fileToDelete):
	logger.info(f'Attempting to delete {fileToDelete}...')
	try:
		os.remove(fileToDelete)
		logger.info(f'Successfully deleted {fileToDelete}.')
	except Exception as e:
		logger.error(f'Failed to delete {fileToDelete}. Reason: {e}')

def filterEventLog(logName):
	groupedData = {}
	jsonFile 	= os.path.join(filesDir, f'events-{logName}.json')
	data 		= readEventJson(jsonFile)

	for record_id, record in data.items():
		eventId 		= record["eventid"]
		timeGenerated 	= parseTime(record["timegenerated"])
		message 		= record["message"]
		level 			= record['eventtype']
		if (level == 'WARNING') or (level == 'ERROR') or (logName == 'Security'):
			if eventId not in groupedData:
				groupedData[eventId] = {
					"count": 0,
					"message": message,
					"mostrecenttime": timeGenerated,
					"level": level
				}
			groupedData[eventId]["count"] += 1
			if timeGenerated > groupedData[eventId]["mostrecenttime"]:
				groupedData[eventId]["mostrecenttime"] = timeGenerated
		else:
			pass
#	logger.debug(f'groupedData: {groupedData}')
	for eventId, details in groupedData.items():
		details["mostrecenttime"] = details["mostrecenttime"].strftime("%Y-%m-%d-%H:%M:%S")

	sortedGroupedData = sorted(groupedData.items(), key=lambda x: x[1]["count"], reverse=True)[:10]

	topEvents = []
	for eventId, details in sortedGroupedData:
		currentTopEvent = {
			'Message':details['message'], 
			'EventID': eventId, 
			'Level': details['level'], 
			'Count': details['count'], 
			'LatestOccurrence':details['mostrecenttime']
			}
		topEvents.append(currentTopEvent)

	filteredEventDict							= {}
	filteredEventDict['LogName'] 				= logName
	filteredEventDict['Sources'] 				= {}
	filteredEventDict['Sources']['TopEvents'] 	= topEvents
	filteredEventDict['Sources']['TotalEvents'] = 10
	return(filteredEventDict)

def sendEventMetadata(deviceUuid):
	url = f'https://{host}/ai/device/metadata'
	logNames = ['Application', 'System', 'Security']
	for logName in logNames:
		with open(os.path.join(filesDir, 'eventsFiltered-' + logName +'.json'), 'r') as f:
			data = json.load(f)
		body = {
			'deviceuuid':deviceUuid,
			'metalogos_type':f'eventsFiltered-{logName}',
			'metalogos':data
			}
		
		headers 	= {'Content-Type': 'application/json'}
		logger.info(f'Attempting to POST to: {url}')
		response 	= requests.post(url, headers=headers, data=json.dumps(body))
		logger.info(f'response: {response.status_code}')
		if response.status_code != 201:
			logger.error(f'Failed to POST data. Reason: {response.text}')

def processLinuxLogs():
	linuxLogsList = ['auth', 'kern', 'syslog']
	for linuxLog in linuxLogsList:
		if linuxLog == 'syslog':
			linuxLogFile 	= f'/var/log/{linuxLog}'
		else:
			linuxLogFile 		= f'/var/log/{linuxLog}.log'
		logger.info(f'Processing: {linuxLogFile}')
		now 				= datetime.datetime.now()
		thirtyDaysAgo		= now - datetime.timedelta(days=30)
		linuxlogDict 		= {}
		with open(linuxLogFile, 'r', encoding='utf-8', errors='ignore') as f:
			i = 0
			for line in f.readlines():
				linuxlogDict[i] = {}
				parts = line.replace('  ', ' ').split(' ')
				if len(parts[0]) > 3:
					eventTime 	= getDateFormat(parts[0])
					if eventTime < thirtyDaysAgo:
						pass
					else:
						deviceName 	= parts[1]
						process 	= parts[2].split('[')[0]
						message 	= ' '.join(parts[3:]).strip()
				else:
					eventTime 	= getDateFormat(f'{parts[0]} {parts[1]} {parts[2]}')
					if eventTime < thirtyDaysAgo:
						print(f'too old: {eventTime}')
					else:			
						deviceName 	= parts[3]
						process 	= parts[4].split('[')[0]
						message 	= ' '.join(parts[5:]).strip()
						linuxlogDict[i]['timegenerated'] 	= eventTime
						linuxlogDict[i]['sourcename'] 		= process
						linuxlogDict[i]['message'] 			= message
						i += 1
		linuxLogJsonFile	= os.path.join(filesDir, f'{linuxLog}.json')
		with open(linuxLogJsonFile, 'w') as f:
			f.write(json.dumps(linuxlogDict, indent=4, default=str))
		outZipFile 			= zipFile(f'{linuxLog}.json')
		uploadSuccess 		= sendPayloadFlask(route, outZipFile, deviceUuid)
		if uploadSuccess == True:
			delFile(outZipFile)
		else:
			logger.error(f'Upload failed.')
		filteredlinuxlogDict 	= filterLinuxLog(linuxLog)
		events 				= filteredlinuxlogDict["Sources"]["TopEvents"]
		totalCount 			= sum(event["Count"] for event in events)
		filteredlinuxlogDict['Sources']['TotalEvents'] = totalCount
		logger.debug(json.dumps(filteredlinuxlogDict, indent=4))
		with open(os.path.join(filesDir, f'{linuxLog}Filtered.json'), 'w') as f:
			f.write(json.dumps(filteredlinuxlogDict, indent=4))
		sendLinuxLogMetadata(deviceUuid, linuxLog)

def getDateFormat(dateString):
	if ('-' in dateString) and ('+' in dateString):
		eventTime = datetime.datetime.fromisoformat(dateString)
	else:
		eventTime = datetime.datetime.strptime(dateString, "%b %d %H:%M:%S")
		eventTime = eventTime.replace(year=datetime.datetime.now().year)
	return(eventTime)	

def filterLinuxLog(logType):
	groupedData = {}
	jsonFile 	= os.path.join(filesDir, f'{logType}.json')
	logger.info(f'Filtering {jsonFile}')
	data 		= readEventJson(jsonFile)

	for record_id, record in data.items():
		timeGenerated 	= parseTime2(record["timegenerated"])
		message 		= record["message"]
		sourceName 		= record['sourcename']

		if sourceName not in groupedData:
			groupedData[sourceName] = {
				"count": 0,
				"message": message,
				"mostrecenttime": timeGenerated
			}
		groupedData[sourceName]["count"] += 1
		if timeGenerated > groupedData[sourceName]["mostrecenttime"]:
			groupedData[sourceName]["mostrecenttime"] = timeGenerated
	else:
		pass
#	logger.debug(f'groupedData: {groupedData}')
	for sourceName, details in groupedData.items():
		details["mostrecenttime"] = details["mostrecenttime"].strftime("%Y-%m-%d-%H:%M:%S")

	sortedGroupedData = sorted(groupedData.items(), key=lambda x: x[1]["count"], reverse=True)[:10]

	topEvents = []
	for sourceName, details in sortedGroupedData:
		currentTopEvent = {
			'Message': details['message'], 
			'SourceName': sourceName,
			'Count': details['count'], 
			'LatestOccurrence':details['mostrecenttime']
			}
		topEvents.append(currentTopEvent)

	filteredSyslogDict							= {}
	filteredSyslogDict['LogName'] 				= logType
	filteredSyslogDict['Sources'] 				= {}
	filteredSyslogDict['Sources']['TopEvents'] 	= topEvents
	filteredSyslogDict['Sources']['TotalEvents'] = 10
	return(filteredSyslogDict)

def sendLinuxLogMetadata(deviceUuid, logToSend):
	url = f'https://{host}/ai/device/metadata'
	with open(os.path.join(filesDir, f'{logToSend}Filtered.json'), 'r') as f:
		data = json.load(f)
	body = {
		'deviceuuid':deviceUuid,
		'metalogos_type':f'{logToSend}Filtered',
		'metalogos':data
		}
	headers 	= {'Content-Type': 'application/json'}
	logger.info(f'Attempting to POST to: {url} for {logToSend}')
	response 	= requests.post(url, headers=headers, data=json.dumps(body))
	logger.info(f'response: {response.status_code}')
	if response.status_code != 201:
		logger.error(f'Failed to POST data. Reason: {response.text}')

def getDeviceUuid():
	with open(os.path.join(configDir, 'agent.config')) as f:
		agentConfigDict = json.load(f)
	deviceUuid = agentConfigDict['deviceuuid']
	if 'serverAddr' in agentConfigDict:
		host = agentConfigDict['serverAddr']
	else:
		host 	= 'app.wegweiser.tech'
	return(deviceUuid, host)

def fixEventId(badId):
	if badId < 0:
		badId += 2**16
	fixedEventId = badId & 0xFFFF
	return (fixedEventId)	

def getEventValueToString(eventValue):
	if eventValue == 0:
		return('SUCCESS')
	elif eventValue == 1:
		return('ERROR')
	elif eventValue == 2:
		return('WARNING')
	elif eventValue == 4:
		return('INFORMATION')
	elif eventValue == 8:
		return('AUDIT SUCCESS')
	else:
		logger.info(f'OTHER: {eventValue}')
		return(f'OTHER')

def readEventJson(jsonFile):
    with open(jsonFile, 'r') as f:
        eventsDict = json.load(f)
    return(eventsDict)

def parseTime(timeStr):
    return (datetime.datetime.strptime(timeStr, "%Y-%m-%d-%H:%M:%S"))

def parseTime2(timeStr):
    return (datetime.datetime.strptime(timeStr, "%Y-%m-%d %H:%M:%S"))

################# MAIN #################

appDir, \
logDir, \
configDir, \
tempDir, \
filesDir = getAppDirs()

deviceUuid, \
	host	= getDeviceUuid()
host 		= 'app.wegweiser.tech'
port 		= 443
route = '/payload/sendfile'
if platform.system() == 'Windows':
	try:
		logger.info('Importing: win32api')
		import win32api
	except Exception as e:
		logger.info('Installing: pypiwin32')
		subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pypiwin32'])
		import win32api
	try:
		logger.info('Importing: win32evtlog')
		import win32evtlog
	except Exception as e:
		logger.info('Installing: pypiwin32')
		subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'win32api'])
		import win32api
	try:
		logger.info('Importing: win32evtlogutil')
		import win32evtlogutil
	except Exception as e:
		logger.info('Installing: win32evtlogutil')
		subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'win32evtlogutil'])
		import win32evtlogutil



	logList 			= ['Application', 'System', 'Security']
	logger.info('Starting Event Log Collection')
	for log in logList:
		latestEvtFile		= f'{configDir}latestEvt-{log}.txt'
		latestEvent 		= getLatestEvent(latestEvtFile)
		objectList 			= readLog(log)
		eventDict			= readExistingLogJson(log)
		eventDict			= processEvents(log, objectList, eventDict)
		writeLogJson(eventDict, log)
		writeLatestEvent(latestEvent, log, objectList)
		outZipFile 			= zipFile(f'events-{log}.json')
		uploadSuccess 		= sendPayloadFlask(route, outZipFile, deviceUuid)
		if uploadSuccess == True:
			delFile(outZipFile)
		else:
			logger.error(f'Upload failed.')
	
	logNames = ['Application', 'System', 'Security']	
	startTime = time.time()
	for logName in logNames:
		filteredEventDict 	= filterEventLog(logName)
		events 				= filteredEventDict["Sources"]["TopEvents"]
		totalCount 			= sum(event["Count"] for event in events)
		filteredEventDict['Sources']['TotalEvents'] = totalCount
		logger.debug(json.dumps(filteredEventDict, indent=4))
		with open(os.path.join(filesDir, 'eventsFiltered-' + logName +'.json'), 'w') as f:
			f.write(json.dumps(filteredEventDict, indent=4))
	logger.info(f'Eventlog Parse Time: {time.time()-startTime} seconds.')
	sendEventMetadata(deviceUuid)
else:
	processLinuxLogs()