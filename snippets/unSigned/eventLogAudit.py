# Filepath: snippets/unSigned/eventLogAudit.py
# Filepath: snippets/unSigned/eventLog-audit.py
import platform
from logzero import logger, logfile
import datetime
import os
import json
import zipfile
import requests
import time
import sys
import subprocess

# Windows-specific imports (only available on Windows)
if platform.system() == 'Windows':
    import win32evtlog
    import win32evtlogutil

########################################## FUNCTIONS ##########################################

def readLog(log):
    # Read Windows event logs starting from the last processed record number
    logger.info(f'Reading {log} event log from recordNumber {latestEvent}...')
    objectList 	= []
    h			= win32evtlog.OpenEventLog(None, log)
    logger.debug(f'Total number of records in {log} log: {win32evtlog.GetNumberOfEventLogRecords(h)}')
    while True:
        # Read events in reverse chronological order
        objects 	= win32evtlog.ReadEventLog(h, win32evtlog.EVENTLOG_BACKWARDS_READ|win32evtlog.EVENTLOG_SEQUENTIAL_READ, 0)
        if not objects:
            logger.info('End of events...')
            break
        for object in objects:	
            # Only include events that we haven't processed yet
            if object.RecordNumber > latestEvent:
                objectList.append(object)
            else:
                pass
    return(objectList)

def getDateFormat(dateString):
    # Convert different date formats to datetime objects
    if ('-' in dateString) and ('+' in dateString):
        # ISO format with timezone
        eventTime = datetime.datetime.fromisoformat(dateString)
    else:
        # Standard syslog format (no year)
        eventTime = datetime.datetime.strptime(dateString, "%b %d %H:%M:%S")
        # Add current year as it's not in the log entry
        eventTime = eventTime.replace(year=datetime.datetime.now().year)
    return(eventTime)	

def getEventValueToString(eventValue):
    # Convert Windows event numeric types to human readable strings
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

def fixEventId(badId):
    # Fix negative event IDs which can occur in Windows event logs
    if badId < 0:
        badId += 2**16
    fixedEventId = badId & 0xFFFF
    return (fixedEventId)	

def processEvents(log, objectList, eventDict):
    # Process and filter Windows event log objects
    now 				= datetime.datetime.now()
    thirtyDaysAgo		= now - datetime.timedelta(days=30)
    for object in objectList:
        # Skip events older than 30 days
        if object.TimeGenerated < thirtyDaysAgo:
            logger.debug(f'Skipping: {object.RecordNumber} | {object.TimeGenerated}')
            break
        else:
            # Create standardized event dictionary entries
            eventDict[object.RecordNumber] = {
                'timegenerated': object.TimeGenerated.strftime("%Y-%m-%d-%H:%M:%S"), 
                'sourcename': object.SourceName, 
                'eventid': fixEventId(object.EventID),
                'eventtype': getEventValueToString(object.EventType),
                'message': win32evtlogutil.SafeFormatMessage(object, log)
            }
    return(eventDict)

def readExistingLogJson(log):
    # Read previously processed events from JSON file or create new dict if file doesn't exist
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

def writeLogJson(eventDict, log):
    # Save processed events to JSON file
    eventDictFile = f'{filesDir}events-{log}.json'
    with open(eventDictFile, 'w') as f:
        f.write(json.dumps(eventDict, indent=4))

def writeRecordStartPoint(log):
    # Record the latest event number to start from in next execution
    latestEvtFile		= f'{configDir}latestEvt-{log}.txt'
    objectList 			= []
    h					= win32evtlog.OpenEventLog(None, log)
    logger.debug(f'number of records: {win32evtlog.GetNumberOfEventLogRecords(h)}')
    while True:
        objects 	= win32evtlog.ReadEventLog(h, win32evtlog.EVENTLOG_BACKWARDS_READ|win32evtlog.EVENTLOG_SEQUENTIAL_READ, 0)
        if not objects:
            break
        for object in objects:
            objectList.append(object)
    latestEvent = objectList[0].RecordNumber
    logger.info(f'New latest Event: {latestEvent}')
    with open(latestEvtFile, 'w') as f:
        f.write(f'{latestEvent}')
    return(latestEvent)

def getLatestEvent(latestEvtFile):
    # Get the latest processed event number from tracking file
    logger.debug(f'Getting latest event from {latestEvtFile}...')
    if not os.path.isfile(latestEvtFile):
        logger.info(f'latestEvtFile: {latestEvtFile} does not exist. Setting new start point.')
        latestEvent = 0
    else:
        with open(latestEvtFile, 'r') as f:
            latestEvent = f.readline()
    logger.info(f'Previous latestEvent: {latestEvent}')	
    return(int(latestEvent))

def writeLatestEvent(latestEvent, log, objectList):
    # Update the latest event tracking file with newest event number
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

def sendPayloadFlask(route, outZipFile, deviceUuid):
    # Send zipped log data to server using HTTP POST
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

def isJournalUsed():
    # Determine if the system uses systemd journal or traditional log files
    linuxLogsList = ['auth', 'kern', 'syslog']
    journalUsed = True
    for linuxLog in linuxLogsList:
        if linuxLog == 'syslog':
            linuxLogFile 	= f'/var/log/{linuxLog}'
        else:
            linuxLogFile 		= f'/var/log/{linuxLog}.log'	
        if os.path.isfile(linuxLog):
            journalUsed = False
    return(journalUsed)

def formatJournalDate(journalDate):
    # Format journal dates consistently and handle year transitions
    dateObj = datetime.datetime.strptime(journalDate, "%Y-%m-%d %H:%M:%S")
    now 	= datetime.datetime.now()
    # Handle year transition for dates that appear to be in the future
    if dateObj.month > now.month:
        year = now.year - 1  # journalDate is from the previous year
    else:
        year = now.year  # journalDate is from the current year
    journalDateStd = dateObj.replace(year=year).strftime("%Y-%m-%d %H:%M:%S")
    return(journalDateStd)

def writeLastJournal(lastJournalEpoch):
    # Save the timestamp of the last journal entry processed
    lastJournalEpochFile = os.path.join(configDir, 'latestJournal.txt')
    logger.info(f'Writing {lastJournalEpoch} to {lastJournalEpochFile}')
    with open(lastJournalEpochFile, 'w') as f:
        f.write(f'{lastJournalEpoch}')

def getLastJournal():
    # Get the timestamp of the last processed journal entry or default to 7 days ago
    lastJournalEpochFile = os.path.join(configDir, 'latestJournal.txt')
    if os.path.isfile(lastJournalEpochFile):
        logger.debug(f'{lastJournalEpochFile} exists...')
        with open(lastJournalEpochFile, 'r') as f:
            journalSince = f.read()
        logger.debug(f'journalSince: {journalSince}')
    else:
        # Default to 7 days ago if no record exists
        journalSince = int(time.time() - (60 * 60 * 24 * 7))
    return(journalSince)

def processLinuxJournal(days):
    # Process Linux systemd journal logs
    linuxLog			= 'journal'
    linuxlogDict 		= {}
    startDate			= getLastJournal()
    lastJournalEpoch	= int(time.time())
    
    # Use journalctl to get logs since last processed timestamp
    command 			= ["journalctl", "--since", f'@{startDate}', '--no-pager']
    process 			= subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    output, \
        error 			= process.communicate()
    if process.returncode != 0:
        logger.error(f"Error running journalctl: {error}")
        return []
    else:
        logger.info(f'Processing: journal...')
    
    # Parse journal entries
    i = 0
    for line in output.splitlines():
        linuxlogDict[i] = {}
        if not line[0].isalpha():
            pass
        else:
            parts 			= line.split(' ')
            journalDate 	= datetime.datetime.strptime(f'{parts[0]} {parts[1]} {parts[2]}', "%b %d %H:%M:%S")
            journalDateStd	= formatJournalDate(str(journalDate))
            process 	= parts[4].split(':')[0]
            message 	= ' '.join(parts[5:]).strip()
            linuxlogDict[i]['timegenerated'] 	= journalDateStd
            linuxlogDict[i]['sourcename'] 		= process
            linuxlogDict[i]['message'] 			= message
            i += 1
    
    # Save journal to JSON, compress and upload
    linuxLogJsonFile	= os.path.join(filesDir, f'{linuxLog}.json')
    with open(linuxLogJsonFile, 'w') as f:
        f.write(json.dumps(linuxlogDict, indent=4, default=str))
    outZipFile 			= zipFile(f'{linuxLog}.json')
    uploadSuccess 		= sendPayloadFlask(route, outZipFile, deviceUuid)
    if uploadSuccess == True:
        writeLastJournal(lastJournalEpoch)
        delFile(outZipFile)
    else:
        logger.error(f'Upload failed.')
    
    # Create filtered version with top events
    filteredlinuxlogDict 	= filterLinuxLog(linuxLog)
    events 					= filteredlinuxlogDict["Sources"]["TopEvents"]
    totalCount 				= sum(event["Count"] for event in events)
    filteredlinuxlogDict['Sources']['TotalEvents'] = totalCount
    logger.debug(json.dumps(filteredlinuxlogDict, indent=4))
    with open(os.path.join(filesDir, f'{linuxLog}Filtered.json'), 'w') as f:
        f.write(json.dumps(filteredlinuxlogDict, indent=4))
    sendLinuxLogMetadata(deviceUuid, linuxLog)
    if debugMode == True:
        logger.debug(f'{json.dumps(linuxlogDict, indent=4)}')	

def filterLinuxLog(logType):
    # Create summary of Linux logs by grouping and counting events by source
    groupedData = {}
    jsonFile 	= os.path.join(filesDir, f'{logType}.json')
    logger.info(f'Filtering {jsonFile}')
    data 		= readEventJson(jsonFile)

    # Group events by source name
    for record_id, record in data.items():
        timeGenerated 	= (record["timegenerated"])
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
    
    # Sort by count and get top 10 events
    # LIMITATION: Change the value 10 below to increase the number of top events collected
    sortedGroupedData = sorted(groupedData.items(), key=lambda x: x[1]["count"], reverse=True)[:50]

    topEvents = []
    for sourceName, details in sortedGroupedData:
        currentTopEvent = {
            'Message': details['message'], 
            'SourceName': sourceName,
            'Count': details['count'], 
            'LatestOccurrence':details['mostrecenttime']
            }
        topEvents.append(currentTopEvent)

    # Create summary structure
    filteredSyslogDict							= {}
    filteredSyslogDict['LogName'] 				= logType
    filteredSyslogDict['Sources'] 				= {}
    filteredSyslogDict['Sources']['TopEvents'] 	= topEvents
    # LIMITATION: Change the value 10 below to match the number of top events collected above
    filteredSyslogDict['Sources']['TotalEvents'] = 50
    if debugMode == True:
        logger.debug(f'filteredSyslogDict:\n{json.dumps(filteredSyslogDict, indent=4)}')
    return(filteredSyslogDict)

def processLinuxLogs(days):
    # Process traditional Linux log files
    linuxLogsList = ['auth', 'kern', 'syslog']
    for linuxLog in linuxLogsList:
        if linuxLog == 'syslog':
            linuxLogFile 	= f'/var/log/{linuxLog}'
        else:
            linuxLogFile 		= f'/var/log/{linuxLog}.log'
        if os.path.isfile(linuxLogFile):
            # Process each log file if it exists
            logger.info(f'Processing: {linuxLogFile}')
            now 				= datetime.datetime.now()
            thirtyDaysAgo		= now - datetime.timedelta(days=days)
            linuxlogDict 		= {}
            with open(linuxLogFile, 'r', encoding='utf-8', errors='ignore') as f:
                i = 0
                for line in f.readlines():
                    linuxlogDict[i] = {}
                    parts = line.replace('  ', ' ').split(' ')
                    # Handle different log format styles
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
        else:
            logger.warning(f'{linuxLogFile} does not exist. Skipping')
    
    # Save, compress and upload logs
    linuxLogJsonFile	= os.path.join(filesDir, f'{linuxLog}.json')
    with open(linuxLogJsonFile, 'w') as f:
        f.write(json.dumps(linuxlogDict, indent=4, default=str))
    outZipFile 			= zipFile(f'{linuxLog}.json')
    uploadSuccess 		= sendPayloadFlask(route, outZipFile, deviceUuid)
    if uploadSuccess == True:
        delFile(outZipFile)
    else:
        logger.error(f'Upload failed.')
    
    # Create filtered version with top events
    filteredlinuxlogDict 	= filterLinuxLog(linuxLog)
    events 					= filteredlinuxlogDict["Sources"]["TopEvents"]
    totalCount 				= sum(event["Count"] for event in events)
    filteredlinuxlogDict['Sources']['TotalEvents'] = totalCount
    logger.debug(json.dumps(filteredlinuxlogDict, indent=4))
    with open(os.path.join(filesDir, f'{linuxLog}Filtered.json'), 'w') as f:
        f.write(json.dumps(filteredlinuxlogDict, indent=4))
    sendLinuxLogMetadata(deviceUuid, linuxLog)


def getAppDirs():
    # Setup application directories based on OS platform
    if platform.system() == 'Windows':
        appDir 		= 'c:\\program files (x86)\\Wegweiser\\'
        logDir 		= f'{appDir}Logs\\'
        configDir 	= f'{appDir}Config\\'
        tempDir 	= os.getenv('TEMP')
        filesDir	= f'{appDir}Files\\'
    else:
        appDir 		= '/opt/Wegweiser/'
        logDir 		= f'{appDir}Logs/'
        configDir 	= f'{appDir}Config/'
        filesDir	= f'{appDir}Files/'
        tempDir 	= os.getenv('TMPDIR') or os.getenv('TEMP') or os.getenv('TMP') or '/tmp'
    
    # Ensure all required directories exist
    checkDir(appDir)
    checkDir(logDir)
    checkDir(configDir)
    checkDir(tempDir)
    checkDir(filesDir)
    return(appDir, logDir, configDir, tempDir, filesDir)

def checkDir(dirToCheck):
    # Create directory if it doesn't exist
    dirToCheck = os.path.join(dirToCheck, '')
    if not os.path.isdir(dirToCheck):
        logger.info(f'{dirToCheck} does not exist. Creating...')
        try:
            os.makedirs(dirToCheck)
            logger.info(f'{dirToCheck} created.')
        except Exception as e:
            logger.error(f'Failed to create {dirToCheck}. Reason: {e}')
            sys.exit()
    return(dirToCheck)

def zipFile(fileToZip):
    # Compress a file using ZIP format
    import zipfile
    inFile 		= f'{filesDir}{fileToZip}'
    outZipFile 	= f'{filesDir}{fileToZip}.zip'
    logger.info(f'Zipping {inFile} to {outZipFile}')
    with zipfile.ZipFile(outZipFile, 'w', compression=zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(inFile, os.path.basename(inFile))
    logger.info(f'Successfully zipped {inFile} to {outZipFile}')
    return(outZipFile)

def getDeviceUuid(configFile):
    # Get device UUID and server address from config file
    logger.info(f'Attempting to read config file: {configFile}...')
    if os.path.isfile(configFile):
        try:
            with open(configFile, 'r') as f:
                configDict = json.load(f)
            logger.info(f'Successfully read {configFile}')
        except Exception as e:
            logger.error(f'Failed to read {configFile}')
            quit('Quitting.')
        deviceUuid 	= configDict['deviceuuid']
        if 'serverAddr' in configDict:
            host		= configDict['serverAddr']
        else:
            host 	= 'app.wegweiser.tech'  # Default server
    return(deviceUuid, host)

def delFile(fileToDelete):
    # Delete a file after successful upload
    logger.info(f'Attempting to delete {fileToDelete}...')
    try:
        os.remove(fileToDelete)
        logger.info(f'Successfully deleted {fileToDelete}.')
    except Exception as e:
        logger.error(f'Failed to delete {fileToDelete}. Reason: {e}')

def filterEventLog(logName):
    # Create summary of Windows event logs by filtering and grouping events
    groupedData = {}
    jsonFile 	= os.path.join(filesDir, f'events-{logName}.json')
    data 		= readEventJson(jsonFile)

    # Group events by event ID for warnings, errors, and all security events
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

    # Format dates and sort by frequency
    for eventId, details in groupedData.items():
        details["mostrecenttime"] = details["mostrecenttime"].strftime("%Y-%m-%d-%H:%M:%S")
    # LIMITATION: Change the value 10 below to increase the number of top events collected for Windows logs
    sortedGroupedData = sorted(groupedData.items(), key=lambda x: x[1]["count"], reverse=True)[:10]

    # Create top 10 list
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

    # Create summary structure
    filteredEventDict							= {}
    filteredEventDict['LogName'] 				= logName
    filteredEventDict['Sources'] 				= {}
    filteredEventDict['Sources']['TopEvents'] 	= topEvents
    # LIMITATION: Change the value 10 below to match the number of top events collected above
    filteredEventDict['Sources']['TotalEvents'] = 10
    return(filteredEventDict)

def readEventJson(jsonFile):
    # Read event data from JSON file
    with open(jsonFile, 'r') as f:
        eventsDict = json.load(f)
    return(eventsDict)

def parseTime(timeStr):
    # Parse time string in the standard format used by Windows events
    return (datetime.datetime.strptime(timeStr, "%Y-%m-%d-%H:%M:%S"))

def parseTime2(timeStr):
    # Parse time string in the standard format used by Linux logs
    return (datetime.datetime.strptime(timeStr, "%Y-%m-%d %H:%M:%S"))

def sendEventMetadata(deviceUuid):
    # Send filtered Windows event log summaries to server
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

def sendLinuxLogMetadata(deviceUuid, logToSend):
    # Send filtered Linux log summaries to server
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


########################################## MAIN ##########################################

# Global configuration
debugMode 		= False
port 			= 443

# Setup directories
appDir, \
    logDir, \
    configDir, \
    tempDir, \
    filesDir	= getAppDirs()

# Get device identification and server information
wegConfigFile 	= f'{configDir}agent.config'
deviceUuid, \
    host		= getDeviceUuid(wegConfigFile)

route = '/payload/sendfile'

# Platform-specific processing
if platform.system() == 'Windows':
    # Windows event log collection
    # Process standard Windows event logs
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
    
    # Create and send filtered event summaries
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
    # Linux log collection - detect and use appropriate log source
    if isJournalUsed() == True:
        processLinuxJournal(31)
    else:	
        processLinuxLogs(31)