# Filepath: snippets/unSigned/fullAudit.py
# Filepath: collector/collector.py
import socket
import json
import os
import platform
import time
import getpass
import shutil
import math
import argparse
import sys
import datetime
import subprocess
import hashlib
try:
	from logzero import logger, logfile
except Exception as e:
	subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'logzero'])
	from logzero import logger, logfile
try:
	import psutil
except Exception as e:
	subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'psutil'])
	import psutil
try:
	import requests
except Exception as e:
	subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'requests'])
	import requests
try:
	import dns.resolver
except:
	subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'dnspython'])
	import dns.resolver
if platform.system() == 'Windows':
	try:
		import win32api
		logger.debug('win32api already imported')
	except Exception as e:
		logger.info('Need to import win32api')
		logger.debug(f'Running {sys.executable} -m pip install pypiwin32')
		importResult = subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pypiwin32'])
		logger.debug(f'importResult: {importResult}')
		import win32api	





###################### FUNCTIONS ######################

# def parseArgs():
# 	parser = argparse.ArgumentParser()
# 	parser.add_argument("-t", "--tempDir", 		help = "Enter temp directory", 	required=True)
# 	parser.add_argument("-m", "--mode", 		help = "Enter mode - audit", 	required=False)	
# 	parser.add_argument("-g", "--groupUuid",	help = "Enter groupUuid",		required=False)		 
# 	parser.add_argument("-v", "--version",		help = "Display the version", 	action='store_true')
# 	args = parser.parse_args()	
# 	return(args)

def convertSize(sizeBytes):
	if sizeBytes == 0:
		return "0 B"
	sizeName = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
	i = int(math.floor(math.log(sizeBytes, 1024)))
	p = math.pow(1024, i)
	s = round(sizeBytes / p, 2)
	return (f'{s} {sizeName[i]}')

def sendJsonPayloadFlask(payload, endpoint):
	url 		= f'https://{host}{endpoint}'
	if debugMode == True:
		logger.debug(f'payload to send: {payload}')
		logger.debug(f'Attempting to connect to {url}')
	headers 	= {'Content-Type': 'application/json'}
	response 	= requests.post(url, headers=headers, data=json.dumps(payload))
	return(response)

def getPublicIpAddr():
	odDnsServer 			= '208.67.222.222'
	httpDnsServer			= 'https://icanhazip.com'
	dnsResolver 			= dns.resolver.Resolver()
	dnsResolver.nameservers = [odDnsServer]
	try:
		answers 			= dnsResolver.resolve('myip.opendns.com', 'A')
		for publicIp in answers:
			publicIp = publicIp.to_text()
	except Exception as e:
		logger.error(f'Failed to get publicIP from {odDnsServer}. Reason: {e}')
		publicIp = None
	if not publicIp:
		try:
			r 			= requests.get(httpDnsServer)
			logger.info(f'rtext: {r.text}')
			publicIp 	= r.text.strip()
		except Exception as e:
			logger.error(f'Failed to get publicIP from {httpDnsServer}. Reason: {e}')
			publicIp = None
	if not publicIp:
		publicIp = '0.0.0.0'
	return(publicIp)

def getUserHomePath():
	userHomePath 	= os.path.expanduser("~")
	logger.info(f'userHomePath: {userHomePath}')
	return(userHomePath)

def getDeviceUuid(configFile):
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
			host = configDict['serverAddr']
		else:
			host = 'app.wegweiser.tech'
	else:
		logger.error(f'{configFile} does not exist. Quitting.')
	return(deviceUuid, host)

# def writeWegConfigFile(deviceuuid, groupuuid):
# 	configDict = {'deviceuuid':deviceuuid, 'groupuuid':groupuuid}
# 	logger.info(f'Attempting to write to {wegConfigFile}')
# 	with open(wegConfigFile, 'w') as f:
# 		f.write(json.dumps(configDict, indent=4))
# 	logger.info(f'{wegConfigFile} written successfully.')

# def registerDevice(groupuuid):
# 	endpoint 		= '/devices/register'
# 	deviceName 		= socket.gethostname()
# 	hardwareInfo 	= platform.system()
# 	payload 		= {'groupuuid': groupuuid, 'devicename': deviceName, 'hardwareinfo': hardwareInfo}
# 	response 		= sendJsonPayloadFlask(payload, endpoint)
# 	logger.debug(f'response: {response.text}')
# 	deviceUuid 		= json.loads(response.text)['deviceuuid']
# 	logger.debug(f'Device issued new deviceUuid: {deviceUuid}')
# 	return(deviceUuid)

def getDeviceData(deviceDataDict):
	deviceDataDict['device'] 					= {}
	deviceDataDict['device']['deviceUuid']		= f'{deviceUuid}'
#	deviceDataDict['device']['groupUuid']		= f'{groupUuid}'
	deviceDataDict['device']['systemtime']		= int(time.time())
	if debugMode == True:
		logger.debug(json.dumps(deviceDataDict, indent=4))
	return(deviceDataDict)

def getSystemData(deviceDataDict):
	deviceDataDict['system'] 					= {}	
	deviceDataDict['system']['devicePlatform'] 	= platform.platform()
	deviceDataDict['system']['systemName']		= socket.gethostname()
	deviceDataDict['system']['currentUser']		= getpass.getuser()
	deviceDataDict['system']['cpuUsage']		= psutil.cpu_percent(4)
	deviceDataDict['system']['cpuCount'] 		= psutil.cpu_count()
	deviceDataDict['system']['publicIp'] 		= getPublicIpAddr()
	if debugMode == True:
		logger.debug(json.dumps(deviceDataDict, indent=4))
	return(deviceDataDict)

def getCollectorData(deviceDataDict):
	agentVersionFile = os.path.join(configDir, 'agentVersion.txt')
	with open(agentVersionFile, 'r') as f:
		localAgentVersion = f.read().strip()
	logger.info(f'localAgentVersion: {localAgentVersion}')
	deviceDataDict['collector'] 					= {}
	deviceDataDict['collector']['collversion']		= localAgentVersion
	deviceDataDict['collector']['collinstalldir']	= appDir
	return(deviceDataDict)

def getUptimeData(deviceDataDict):
	if 'system' not in deviceDataDict:
		deviceDataDict['system'] = {}
	deviceDataDict['system']['bootTime']		= int(psutil.boot_time())
	return(deviceDataDict)

def getNetworkData(deviceDataDict):
	deviceDataDict['networkList']				= []
	psNetDict 									= psutil.net_if_stats()
	ifDict 										= {}

	for ifName, data in psNetDict.items():
		ifDict[ifName] 				= {}
		ifDict[ifName]['ifIsUp']	= data.isup
		ifDict[ifName]['ifSpeed']	= data.speed
		ifDict[ifName]['ifMtu']		= data.mtu

	psNetDict 									= psutil.net_io_counters(pernic=True)
	for ifName, data in psNetDict.items():
		ifDict[ifName]['bytesSent'] 	= data.bytes_recv
		ifDict[ifName]['bytesRecv'] 	= data.bytes_sent
		ifDict[ifName]['errIn'] 		= data.errin
		ifDict[ifName]['errOut'] 		= data.errout

	psNetDict 									= psutil.net_if_addrs()
	for ifName, addresses in psNetDict.items():
		for address in addresses:
			if address.family == socket.AF_INET:
				ifDict[ifName]['address4'] 		= address.address
				ifDict[ifName]['netmask4'] 		= address.netmask
				ifDict[ifName]['broadcast4'] 	= address.broadcast
			elif address.family == socket.AF_INET6:
				ifDict[ifName]['address6'] 		= address.address
				ifDict[ifName]['netmask6'] 		= address.netmask
				ifDict[ifName]['broadcast6'] 	= address.broadcast
	deviceDataDict['networkList'].append(ifDict)	
	return(deviceDataDict)	
	
def getUserData(deviceDataDict):
	users 		= psutil.users()
	deviceDataDict['Users'] 				= []
	userDict 	= {}
	userId 		= 0
	for user in users:
		userDict[userId] 				= {}
		userDict[userId]['username'] 	= user.name
		if not user.terminal:
			userDict[userId]['terminal'] 	= '-1'
		else:
			userDict[userId]['terminal'] 	= user.terminal
		if not user.host:
			userDict[userId]['host'] 	= 'localhost'
		else:
			userDict[userId]['host'] 		= user.host
		userDict[userId]['loggedIn'] 	= user.started
		if not user.pid:
			userDict[userId]['pid']			= -1
		else:
			userDict[userId]['pid'] 		= user.pid
		userId += 1
	deviceDataDict['Users'].append(userDict)
	return(deviceDataDict)

def getWindowsDrives():
	drives 			= win32api.GetLogicalDriveStrings()
	drivesList 		= drives.split('\000')[:-1]
	if debugMode == True:
		logger.debug(f'drivesList: {drivesList}')
	return(drivesList)

def getDiskStats(deviceDataDict):
	if platform.system() == 'Windows':
		deviceDataDict['drives'] = []
		drivesList = getWindowsDrives()
		for drive in drivesList:
			if debugMode == True:
				logger.debug(f'checking drive: {drive}')
			driveData = {}
			try:
				stat 	= shutil.disk_usage(drive)
				total 	= stat.total
				used 	= stat.used
				free 	= stat.free
				usedPer	= (used / total) * 100
				freePer = (free / total) * 100
				driveData['name'] 		= drive
				driveData['total'] 		= total
				driveData['used'] 		= used
				driveData['free'] 		= free
				driveData['usedPer'] 	= usedPer
				driveData['freePer'] 	= freePer
				deviceDataDict['drives'].append(driveData)
			except Exception as e:
				logger.error(f'Unable to query {drive}. Reason: {e}')

	elif platform.system() == 'Linux':
		driveData 	= {}
		stat 		= shutil.disk_usage('/')
		total 		= stat.total
		used 		= stat.used
		free 		= stat.free
		usedPer		= (used / total) * 100
		freePer 	= (free / total) * 100
		deviceDataDict['drives'] = []
		driveData['name'] 		= '/'
		driveData['total'] 		= total
		driveData['used'] 		= used
		driveData['free'] 		= free
		driveData['usedPer'] 	= usedPer
		driveData['freePer'] 	= freePer
		deviceDataDict['drives'].append(driveData)
	return(deviceDataDict)

def getBatteryData(deviceDataDict):
	battery 								= psutil.sensors_battery()
	deviceDataDict['battery']	 			= {}
	if battery:
		deviceDataDict['battery']['installed']	= True
		deviceDataDict['battery']['pcCharged']	= battery.percent
		deviceDataDict['battery']['secsLeft']	= battery.secsleft.value
		deviceDataDict['battery']['powerPlug']	= battery.power_plugged
	else:
		deviceDataDict['battery']['installed']	= False
		deviceDataDict['battery']['pcCharged']	= 0
		deviceDataDict['battery']['secsLeft']	= 0
		deviceDataDict['battery']['powerPlug']	= False
	return(deviceDataDict)

def getPartitionData(deviceDataDict):
	partitionDict 					= {}
	deviceDataDict['partitions'] 	= []
	partitionsList					= psutil.disk_partitions()
	for partition in partitionsList:
		partitionDict[partition.mountpoint] 			= {}
		partitionDict[partition.mountpoint]['device']	= partition.device
		partitionDict[partition.mountpoint]['fstype']	= partition.fstype
	deviceDataDict['partitions'].append(partitionDict)
	return(deviceDataDict)

def getmemoryData(deviceDataDict):
	memory 									= psutil.virtual_memory()
	deviceDataDict['memory']	 			= {}
	deviceDataDict['memory']['total']		= memory.total
	deviceDataDict['memory']['available']	= memory.available
	deviceDataDict['memory']['used']		= memory.used
	deviceDataDict['memory']['free']		= memory.free
	return(deviceDataDict)



def checkMode(mode):
	validModes = ['AUDIT', 'EVENTLOG', 'STATUS', 'WEGLOG', 'FULLAUDIT', 
			   		'MSINFO', 'UPDATE', 'INSTALL', 'RESETEVENTS']
	if mode.upper() in validModes:
		return(mode)
	else:
		logger.error(f'Invalid mode specified: {mode}')
		sys.exit()

def getWegConfigFileX(configDir):
	if platform.system() == 'Windows':
		wegConfigFile = f'{configDir}wegweiser.config'
	else:	
		wegConfigFile = f'{configDir}wegweiser.config'
	return(wegConfigFile)

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

def delFile(fileToDelete):
	logger.info(f'Attempting to delete {fileToDelete}...')
	try:
		os.remove(fileToDelete)
		logger.info(f'Successfully deleted {fileToDelete}.')
	except Exception as e:
		logger.error(f'Failed to delete {fileToDelete}. Reason: {e}')

def runMsinfo(msinfoOutput):
	logger.info('Attempting to run msinfo32...')
	logger.info(f'Writing output to {msinfoOutput}')
	try:
		subprocess.run(['msinfo32.exe', '/report', msinfoOutput])
		logger.info(f'Successfully wrote {msinfoOutput}')
	except Exception as e:
		logger.error(f'Failed to run msinfo32.exe. Reason: {e}')
	return(msinfoOutput)

def runAndreiMsInfo():
	logger.info('Collecting MS Info summaries...')
	msifoPsfile = os.path.join(appDir, 'scripts', 'msinfo32-evaluatorAgent.ps1')
	logger.debug(f'Attempting to run powershell.exe -File {msifoPsfile}')
	command 	= ['powershell.exe', '-ExecutionPolicy', 'Bypass', '-File', msifoPsfile]
	result 		= subprocess.run(command, stdout = subprocess.PIPE, universal_newlines = True)
	url 		= f'https://{host}/ai/device/metadata'
### removed SystemResources (IRQs)
#	fileNames 	= ['InstalledPrograms','NetworkConfig', 'RecentAppCrashes', 'StorageInfo', 'SystemHardwareConfig', 
#			   		'SystemResources', 'SystemSoftwareConfig']
	fileNames 	= ['InstalledPrograms','NetworkConfig', 'RecentAppCrashes', 'StorageInfo', 'SystemHardwareConfig', 
			   		'SystemSoftwareConfig']
	for fileName in fileNames:
		currentFile = os.path.join(filesDir, fileName +".json")
		logger.info(f'Processing {currentFile}')
		if os.path.getsize(currentFile) == 0:
			logger.warning(f'{currentFile} is 0 bytes. Skipping.')	
		else:	
			logger.info(f'{currentFile} has data. Processing...')
			with open(currentFile, 'rb') as f:
				data = json.loads(f.read().decode('utf-16'))
			body = {
				'deviceuuid':deviceUuid,
				'metalogos_type':f'msinfo-{fileName}',
				'metalogos':data
				}
			
			headers 	= {'Content-Type': 'application/json'}
			logger.info(f'Attempting to POST to: {url}')
			logger.debug(f'andreimsinfo: {body}')
			response 	= requests.post(url, headers=headers, data=json.dumps(body))
			logger.info(f'response: {response.status_code}')
			if response.status_code != 201:
				logger.error(f'Failed to POST data. Reason: {response.text}')
	return(True)

def getCpuInfo(deviceDataDict):
	if platform.system() == 'Windows':
		command 	= "(Get-WmiObject Win32_Processor).Name"
		result 		= subprocess.run(["powershell", "-Command", command], stdout = subprocess.PIPE, universal_newlines = True)
		cpuName 	= ' '.join(result.stdout.split())
	elif platform.system() == 'Linux':
		command 	= 'lscpu'
		result 		= subprocess.Popen([command], stdout = subprocess.PIPE, universal_newlines = True)
		result 		= result.stdout.read()
		for line in result.splitlines():
			if 'Model name' in line:
				cpuName = line.split('Model name:')[1].strip()
	logger.info(f'cpuName: {cpuName}')
	deviceDataDict['cpu']  				= {}
	deviceDataDict['cpu']['cpuname']	= cpuName
	return(deviceDataDict)

def checkAppInstalled(appName):
	logger.info(f'Checking if {appName} exists...')
	command 	= ["which", appName]
	result 		= subprocess.Popen(command, stdout=subprocess.PIPE)
	result 		= result.stdout.read().decode("utf-8").strip()
	logger.info(f'E: {result}')
	if len(result) > 0:
		logger.info(f'{appName} exists')
		return(True)
	else:
		logger.info(f'{appName} does not exist')
		return(False)

def getGpuInfo(deviceDataDict):
	if platform.system() == 'Windows':
		command 	= "(Get-WmiObject Win32_VideoController)"
		result 		= subprocess.run(["powershell", "-Command", command], stdout = subprocess.PIPE, universal_newlines = True)
		for line in result.stdout.splitlines():
			if 'VideoProcessor' in line:
				product = line.split('VideoProcessor')[1].split(':')[1].strip()
				if len(product) < 1:
					product = 'No data found'
			if 'VideoModeDescription' in line:
				colourDepth = line.split('x ')[2].split(' ')[0]
				colourDepth = int(math.log2(int(colourDepth)))
				hRes 		= line.split(': ')[1].split(' ')[0]
				vRes		= line.split('x ')[1].split(' ')[0]
			if 'AdapterDACType' in line:
				vendor = line.split('AdapterDACType')[1].split(':')[1].strip()
				if len(vendor) < 1:
					vendor = 'No data found'
	elif platform.system() == 'Linux':
		if checkAppInstalled('lshw'):
			command 	= ['lshw', '-C',  'display']
			result 		= subprocess.Popen(command, stdout = subprocess.PIPE, universal_newlines = True)
			result 	= result.stdout.read()
			for line in result.splitlines():
				if 'vendor' in line:
					vendor = line.split('vendor:')[1].strip()
				else:
					vendor = 'No data found'
				if 'product' in line:
					product = line.split('product:')[1].strip()
				else:
					product = 'No data found'
				if 'configuration: depth' in line:
					colourDepth = line.split('depth=')[1].split(' ')[0]	
					hRes		= line.split('resolution=')[1].split(',')[0]	
					vRes 		= line.split('resolution=')[1].split(',')[1]
				else:
					colourDepth = 'No data found'
					hRes 		= 'No data found'
					vRes 		= 'No data found'
		else:
			logger.debug('setting default lshw values')
			vendor 			= 'No data found'
			product 		= 'No data found'
			colourDepth 	= -1
			hRes 			= -1
			vRes 			= -1
	deviceDataDict['gpuinfo']					= {}
	deviceDataDict['gpuinfo']['gpuvendor']		= vendor
	deviceDataDict['gpuinfo']['gpuproduct']		= product
	deviceDataDict['gpuinfo']['gpucolour']		= colourDepth
	deviceDataDict['gpuinfo']['gpuhres']		= hRes
	deviceDataDict['gpuinfo']['gpuvres']		= vRes
	return(deviceDataDict)

def zipFile(fileToZip):
	import zipfile
	inFile 		= os.path.join(filesDir, fileToZip)
	outZipFile 	= os.path.join(filesDir, f'{fileToZip}.zip')
	logger.info(f'Zipping {inFile} to {outZipFile}')
	try:
		with zipfile.ZipFile(outZipFile, 'w', compression=zipfile.ZIP_DEFLATED) as zipf:
			zipf.write(inFile, os.path.basename(inFile))
		logger.info(f'Successfully zipped {inFile} to {outZipFile}')
	except Exception as e:
		logger.error(f'Failed to zip {inFile} to {outZipFile}. Reason: {e}')
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

def getSmBiosInfo(deviceDataDict):
	if platform.system() == 'Windows':
		command 	= "(Get-WmiObject Win32_BIOS)"
		result 		= subprocess.run(["powershell", "-Command", command], stdout=subprocess.PIPE, universal_newlines = True)
		for line in result.stdout.splitlines():
			if 'Manufacturer' in line:
				vendor = line.split('Manufacturer')[1].split(':')[1].strip()
			if 'Name' in line:
				biosVersion = line.split('Name')[1].split(':')[1].strip()
			if 'SerialNumber' in line:
				serialNumber = line.split('SerialNumber')[1].split(':')[1].strip()
			if 'Version' in line:
				version = line.split('Version')[1].split(':')[1]	
				version = ' '.join(version.split()).strip()		

	elif platform.system() == 'Linux':
		# Check if dmidecode command exists
		if shutil.which('dmidecode') is None:
			logger.warning('dmidecode command not found. Skipping SMBIOS info. Install dmidecode package if needed.')
			vendor 			= 'n/a'
			serialNumber 	= 'n/a'
			version			= 'n/a'
		else:
			try:
				logger.debug('Running dmidecode')
				command 	= ['dmidecode', '-t', '1']
				result 		= subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines = True)
				result 		= result.stdout.read()
				for line in result.splitlines():
					if 'Manufacturer:' in line:
						vendor = line.split('Manufacturer:')[1].strip()
					if 'Serial Number' in line:
						serialNumber = line.split('Serial Number:')[1].strip()
					if 'No SMBIOS nor DMI entry point found' in line:
						vendor 			= 'n/a'
						serialNumber 	= 'n/a'
						version			= 'n/a'
				command 	= ['dmidecode', '-t', 'bios', '-q']
				result 		= subprocess.Popen(command, stdout = subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines = True)
				result 		= result.stdout.read()
				for line in result.splitlines():
					if 'Version:' in line:
						version = line.split('Version:')[1].strip()
			except Exception as e:
				logger.error(f'Failed to get SMBIOS info: {e}')
				vendor 			= 'n/a'
				serialNumber 	= 'n/a'
				version			= 'n/a'
	logger.info(f'vendor: {vendor}')
	logger.info(f'serialNumber: {serialNumber}')
	logger.info(f'version: {version}')
	deviceDataDict['bios']					= {}
	deviceDataDict['bios']['biosvendor']	= vendor
	deviceDataDict['bios']['serialnumber']	= serialNumber
	deviceDataDict['bios']['biosversion']	= version
	return(deviceDataDict)

def getSystemModelFromProc():
	systemModel	= 'n/a'
	command		= ['cat', '/proc/cpuinfo']
	result 		= subprocess.Popen(command, stdout = subprocess.PIPE, universal_newlines = True)
	logger.debug(f'result: {result}')
	outtext 	= result.stdout.read()
	logger.info(f'outtext: {outtext}')
	for line in outtext.splitlines():
		if 'Model' in line:
			systemModel = line.split(':')[1].strip()
	logger.info(f'systemModel: {systemModel}')	
	return(systemModel)

def getSystemModel(deviceDataDict):
	if platform.system() == 'Windows':
		command 	= ['wmic', 'csproduct', 'get', 'name']
		result 		= subprocess.run(command, stdout = subprocess.PIPE, universal_newlines = True)
		for line in result.stdout.splitlines():
			if line.strip() == 'Name':
				pass
			elif len(line) > 0:
				systemModel = line.strip()
				break
	elif platform.system() == 'Linux':
		# Check if dmidecode command exists
		if shutil.which('dmidecode') is None:
			logger.warning('dmidecode command not found. Falling back to /proc/cpuinfo. Install dmidecode package if needed.')
			systemModel = getSystemModelFromProc()
		else:
			try:
				command 	= ['dmidecode', '-t', '1']
				result 		= subprocess.Popen(command, stdout = subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines = True)
				result 		= result.stdout.read()
				for line in result.splitlines():
					if 'Product Name: ' in line:
						systemModel = line.split('Product Name:')[1].strip()
					if 'No SMBIOS nor DMI entry point found' in line:
						systemModel = getSystemModelFromProc()
			except Exception as e:
				logger.error(f'Failed to get system model from dmidecode: {e}. Falling back to /proc/cpuinfo.')
				systemModel = getSystemModelFromProc()
	logger.info(f'systemModel: {systemModel}')
	deviceDataDict['system']['systemmodel']		= systemModel
	return(deviceDataDict)

def getServices():
	logger.info('Attempting to get services...')
	servicesDict 	= {}
	if platform.system() == 'Windows':
		import win32service
		SERVICE_STATE_ALL 	= win32service.SERVICE_STATE_ALL
		service_manager 	= win32service.OpenSCManager(None, None, win32service.SC_MANAGER_ENUMERATE_SERVICE)
		services 			= win32service.EnumServicesStatusEx(service_manager, win32service.SERVICE_WIN32, SERVICE_STATE_ALL)
		for service in services:
			if service['CurrentState'] == 1:
				friendlyState = 'STOPPED'
			elif service['CurrentState'] == 2:
				friendlyState = 'STARTING'
			elif service['CurrentState'] == 3:
				friendlyState = 'STOPPING'
			elif service['CurrentState'] == 4:
				friendlyState = 'RUNNING'
			elif service['CurrentState'] == 7:
				friendlyState = 'PAUSED'	
			else:
				friendlyState = 'OTHER'
			if '_' in service['ServiceName']:
				serviceName = service['ServiceName'].split('_')[0]
				displayName = service['DisplayName'].split('_')[0]
			else:
				serviceName = service['ServiceName']
				displayName = service['DisplayName']
			print(f"{service['CurrentState']} | {friendlyState} | {displayName}({serviceName})")
			servicesDict[serviceName] = {}
			servicesDict[serviceName]['displayname'] = displayName
			servicesDict[serviceName]['currentstate'] = service['CurrentState']
			servicesDict[serviceName]['friendlystate'] = friendlyState
	logger.info('Successfully collected services.')
	servicesDictFile	= writeServicesJson(servicesDict)
	route 				= '/payload/sendfile'
	uploadSuccess 		= sendPayloadFlask(route, servicesDictFile, deviceUuid)
	if uploadSuccess == True:
		delFile(servicesDictFile)
	else:
		logger.error(f'Upload failed.')
	return(servicesDict)

def writeServicesJson(servicesDict):
	servicesDictFile = f'{filesDir}services.json'
	logger.info(f'Attempting to write services to {servicesDictFile}')
	try:
		with open(servicesDictFile, 'w') as f:
			f.write(json.dumps(servicesDict, indent=4))
	except Exception as e:
		logger.error(f'Failed to write servicesDict to {servicesDictFile}. Reason: {e}')
	return(servicesDictFile)

def getPrinters(deviceDataDict):
	printerDict 				= {}
	deviceDataDict['printers'] 	= []
	if platform.system() == 'Windows':
		command 	= 'get-printer | Format-list'
		result 		= subprocess.run(["powershell", "-Command", command], stdout = subprocess.PIPE, universal_newlines = True)
		result 		= result.stdout
		for line in result.splitlines():
			if line.startswith('Name'):
				printerName = line.split(':')[1].strip()
				printerDict[printerName] = {}
			if line.startswith('PortName'):
				portName = ':'.join(line.split(':')[1:]).strip()
				printerDict[printerName]['portname'] = portName
			if line.startswith('DriverName'):
				driverName = line.split(':')[1].strip()
				printerDict[printerName]['drivername'] = driverName		
			if line.startswith('Location'):
				location = ':'.join(line.split(':')[1:]).strip()
				printerDict[printerName]['location'] = location	
			if line.startswith('PrinterStatus'):
				printerStatus = ''.join(line.split(':')[1:]).strip()
				printerDict[printerName]['printerstatus'] = printerStatus	
		deviceDataDict['printers'] = printerDict
	else:
		if checkAppInstalled('lpstat'):
			command 					= ['lpstat', '-p', '-l', '-s']
			result 						= subprocess.Popen(command, stdout = subprocess.PIPE, universal_newlines = True)
			result 						= result.stdout.read()
			logger.debug(f'printerResult: {result}')
			for line in result.splitlines():
				logger.debug(f'printerLine: {line}')
				if line.strip().startswith('printer'):
					logger.debug('i found a printer')
					printerName = line.split('printer ')[1].split(' ')[0].strip()
					logger.debug(f'printerName: {printerName}')
					if printerName not in printerDict:
						logger.debug(f'adding {printerName} to printerDict')
						printerDict[printerName] = {}
						logger.debug(f'printerDict: {printerDict}')
				if line.strip().startswith('system default'):
					printerName = ':'.join(line.split(':')[1:]).strip()
					defaultPrinter = line.split(':')[1].strip()
					if defaultPrinter in printerDict:
						printerDict[printerName]['default'] = True

				if line.strip().startswith('device'):
					printerName = line.split('device for ')[1].split(':')[0]
					printerPort = ':'.join(line.split(':')[1:]).strip()
					if printerName in printerDict:
						printerDict[printerName]['portname'] = printerPort
			deviceDataDict['printers'] = printerDict			
		else:
			deviceDataDict['printers'] = {}
	return(deviceDataDict)

def getPciDevices(deviceDataDict):
	pciDeviceDict 				= {}
	if platform.system() == 'Windows':
		command 	= "Get-WmiObject -Query \"SELECT PNPClass, Name FROM Win32_PnPEntity WHERE DeviceID LIKE '%PCI%'\""
		result 		= subprocess.run(["powershell", "-Command", command], stdout = subprocess.PIPE, universal_newlines = True)
		result 		= result.stdout
		for line in result.splitlines():
			if line.startswith('Name'):
				name = line.split(':')[1].strip()
				pciDeviceDict[name] = {}

			if line.startswith('PNPClass'):
				pnpClass = line.split(':')[1].strip()
				pciDeviceDict[name]['pnpclass'] = pnpClass
		deviceDataDict['pcidevices'] = pciDeviceDict
	else:
		# Check if lspci command exists
		if shutil.which('lspci') is None:
			logger.warning('lspci command not found. Skipping PCI device enumeration. Install pciutils package if needed.')
			deviceDataDict['pcidevices'] = {}
		else:
			try:
				command 					= ['lspci']
				result 						= subprocess.Popen(command, stdout = subprocess.PIPE, universal_newlines = True)
				result 						= result.stdout.read()
				for line in result.splitlines():
					if 'Cannot ' in line:
						pass
					else:
						pnpClass 	= ':'.join(line.split(' ')[1:]).split(':')[0].strip()
						name 		= ':'.join(line.split(': ')[1:]).strip()
						pciDeviceDict[name] = {}
						pciDeviceDict[name]['pnpclass'] = pnpClass
				deviceDataDict['pcidevices'] = pciDeviceDict
			except Exception as e:
				logger.error(f'Failed to get PCI devices: {e}')
				deviceDataDict['pcidevices'] = {}
	return(deviceDataDict)

def getUsbDevices(deviceDataDict):
	usbDeviceList					= []
	usbDeviceDict 					= {}

	if platform.system() == 'Windows':
		command 	= "get-pnpdevice | Where-Object { $_.Class -eq \"USB\" } | select Name, InstanceId, status"
		print(f'command: {command}')
		result 		= subprocess.run(["powershell", "-Command", command], stdout = subprocess.PIPE, universal_newlines = True)
		result 		= result.stdout
		for line in result.splitlines():
			logger.debug(f'lineX: {line}')
			if line.startswith('Name') or line.startswith('--') or len(line) < 5:
				continue
			elif 'USB\\' in line:
				parts = line.split('USB\\')
				prefix = 'USB\\'
			elif 'PCI\\' in line:
				parts = line.split('PCI\\')
				prefix = 'PCI\\'
			else:
				continue
			name 		= parts[0].strip()
			instanceId 	= f'{prefix}{parts[1].split(" ")[0].strip()}'
#			status 		= ' '.join(parts[1].split()).split(' ')[1].strip()
			if instanceId not in usbDeviceDict:
				usbDeviceDict[instanceId] 			= {}
				usbDeviceDict[instanceId]['name'] 	= name
#				usbDeviceDict[instanceId]['status'] = status
		deviceDataDict['usbdevices'] = usbDeviceDict
	else:
		# Check if lsusb command exists
		if shutil.which('lsusb') is None:
			logger.warning('lsusb command not found. Skipping USB device enumeration. Install usbutils package if needed.')
			deviceDataDict['usbdevices'] = []
		else:
			try:
				command 					= ['lsusb']
				result 						= subprocess.Popen(command, stdout = subprocess.PIPE, universal_newlines = True)
				result 						= result.stdout.read()
				for line in result.splitlines():
					name 		= ' '.join(line.split(' ')[6:])
					if name not in usbDeviceList:
						usbDeviceList.append(name)
				deviceDataDict['usbdevices'] = usbDeviceList
			except Exception as e:
				logger.error(f'Failed to get USB devices: {e}')
				deviceDataDict['usbdevices'] = []
	return(deviceDataDict)

##################### EVENT LOG FUNCTIONS #####################

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

def fixEventId(badId):
	if badId < 0:
		badId += 2**16
	fixedEventId = badId & 0xFFFF
	return (fixedEventId)	

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

def writeLogJson(eventDict, log):
	eventDictFile = f'{filesDir}events-{log}.json'
	with open(eventDictFile, 'w') as f:
		f.write(json.dumps(eventDict, indent=4))

def writeRecordStartPoint(log):
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

# def getServerCollVersion(appVersion):
# 	logger.info(f'Checking collector version')
# 	logger.info(f'local collectorVersion: {appVersion}')
# 	r 		= requests.get(f'https://{host}/diags/collectorVersion')
# 	data 	= r.json()
# 	serverCollectorVersion = data['serverCollectorVersion']
# 	collHashPy 	= data['serverHashPy']
# 	collHashWin	= data['serverHashWin']
# 	logger.info(f'server collectorVersion: {serverCollectorVersion}')
# 	if int(appVersion) < int(serverCollectorVersion):
# 		logger.info('Local collector needs updating...')
# 		collectorUpdateReqd = True
# 	else:
# 		logger.info('Local collector is up to date.')
# 		collectorUpdateReqd = False
# 	return(collectorUpdateReqd, collHashPy, collHashWin)

def getSha256Hash(fileToHash):
	sha256Hash = hashlib.sha256()
	with open(fileToHash, 'rb') as f:
		for byteBlock in iter(lambda: f.read(4096), b""):
			sha256Hash.update(byteBlock)
	logger.info(f'sha256 of {fileToHash}: {sha256Hash.hexdigest()}')
	return(sha256Hash.hexdigest())

# def updateCollector(collHashPy, collHashWin):
# 	if platform.system() == 'Linux':
# 		collectorUrl = f'https://{host}/download/collector.py'
# 		chunkSize = 4096
# 		saveToFile = f'{sys.argv[0]}.new'
# 		logger.info(f'Attempting to download {collectorUrl} to {saveToFile}...')
# 		try:
# 			r = requests.get(collectorUrl, stream=True)
# 			if r.status_code != 200:
# 				logger.error(f'Failed to download {collectorUrl}. Status Code: {r.status_code}')
# 				return(False)
# 			with open(saveToFile, 'wb') as f:
# 				for chunk in r.iter_content(chunk_size=chunkSize):
# 					if chunk:
# 						f.write(chunk)
# 		except Exception as e:
# 			logger.error(f'Failed to download {collectorUrl} to {saveToFile}. Reason: {e}')
# 		newCollHash = getSha256Hash(saveToFile)
# 		logger.info(f'Downloaded Hash: {newCollHash} | Server Hash: {collHashPy}')
# 		if newCollHash == collHashPy:
# 			logger.info(f'Attempting to rename {saveToFile} to {sys.argv[0]}')
# 			try:
# 				os.rename(saveToFile, sys.argv[0])
# 				logger.info(f'Successfully upgraded {collectorUrl} to {saveToFile}')
# 				logger.info('New collector will run on next cycle')
# 			except Exception as e:
# 				logger.error(f'Failed to rename {saveToFile} to {sys.argv[0]}. Reason: {e}')
# 		else:
# 			logger.error('Hashes do not match. Deleting download.')
# 			try:
# 				os.remove(saveToFile)
# 			except Exception as e:
# 				logger.error(f'Failed to delete {saveToFile}. Reason: {e}')
		
# 	elif platform.system() == 'Windows':
# 		command = f'(New-Object System.Net.WebClient).DownloadFile("https://app.wegweiser.tech/download/wegweiser.exe","$env:TEMP/wegweiser.exe"); \
# Start-Process -FilePath "$env:TEMP/wegweiser.exe" -ArgumentList "/groupuuid={groupUuid}", "/LOG=$env:TEMP/WegweiserSetup.log", "/SILENT"'
# 		logger.info(f'Attempting to run: {command}')
# 		result = subprocess.run(["powershell", "-Command", command], stdout = subprocess.PIPE, universal_newlines = True)
# 		logger.info(f'result: {result.stdout}')

def parseTime(timeStr):
    return (datetime.datetime.strptime(timeStr, "%Y-%m-%d-%H:%M:%S"))

def parseTime2(timeStr):
    return (datetime.datetime.strptime(timeStr, "%Y-%m-%d %H:%M:%S"))

def readEventJson(jsonFile):
    with open(jsonFile, 'r') as f:
        eventsDict = json.load(f)
    return(eventsDict)

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

def getDateFormat(dateString):
	if ('-' in dateString) and ('+' in dateString):
		eventTime = datetime.datetime.fromisoformat(dateString)
	else:
		eventTime = datetime.datetime.strptime(dateString, "%b %d %H:%M:%S")
		eventTime = eventTime.replace(year=datetime.datetime.now().year)
	return(eventTime)		
	
# def checkArgs(args):
# 	if args.version:
# 		print(f'{appName} Version: {appVersion}')
# 		sys.exit()
# 	if args.groupUuid:
# 		groupUuid 		= args.groupUuid
# 	else:
# 		groupUuid		= None
# 	if args.mode:
# 		mode = args.mode
# 	else:
# 		mode = 'AUDIT'
# 	return(groupUuid, mode)

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

def getOsLang(deviceDataDict):
	systemLocale = 'Not detected'
	if platform.system() == 'Windows':
		if not os.path.isfile(msinfoOutput):
			logger.warning(f'{msinfoOutput} not found.Need to run FULLAUDIT')
		else:
			with open (msinfoOutput, 'r', encoding='utf-16') as f:
				msinfoLines = f.readlines()
				for line in msinfoLines:
#					logger.debug(f'msinfoline: {line}')
					if line.startswith('Locale'):
						systemLocale = line.split('\t')[1].strip()
	else:
		systemLocale	= os.getenv('LANGUAGE')
		logger.debug(f'systemLocale: {systemLocale}')
	deviceDataDict['system']['systemlocale'] = systemLocale
	return(deviceDataDict)

def getManufacturer(deviceDataDict):
	systemManufacturer = 'Not detected'
	if platform.system() == 'Windows':
		if not os.path.isfile(msinfoOutput):
			logger.warning(f'{msinfoOutput} not found.Need to run FULLAUDIT')
		else:
			with open (msinfoOutput, 'r', encoding='utf-16') as f:
				msinfoLines = f.readlines()
				for line in msinfoLines:
#					logger.debug(f'msinfoline: {line}')
					if line.startswith('System Manufacturer'):
						systemManufacturer = line.split('\t')[1].strip()
	else:
		# Check if dmidecode command exists
		if shutil.which('dmidecode') is None:
			logger.warning('dmidecode command not found. Skipping manufacturer detection. Install dmidecode package if needed.')
		else:
			try:
				command 			= ['dmidecode']
				grepCommand 		= ['grep', '-A3', '^System Information']
				dmidecode_process 	= subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
				grep_process 		= subprocess.Popen(grepCommand, stdin=dmidecode_process.stdout, stdout=subprocess.PIPE,
													stderr=subprocess.PIPE, universal_newlines=True)

				dmidecode_process.stdout.close()
				output, error 		= grep_process.communicate()
				output 				= output   #.decode('utf-8')
				logger.debug(f'output: {output}')
				for line in output.splitlines():
					if line.strip().startswith('Manufacturer:'):
						systemManufacturer = line.split('Manufacturer:')[1].strip()
			except Exception as e:
				logger.error(f'Failed to get manufacturer info: {e}')
	logger.debug(f'systemManufacturer: {systemManufacturer}')
	deviceDataDict['system']['systemmanufacturer'] = systemManufacturer
	return(deviceDataDict)

def removeEvents():
	logger.info('Resetting event logs...')
	filesToDel = [f'{configDir}latestEvt-Application.txt',
				f'{configDir}latestEvt-Security.txt',
				f'{configDir}latestEvt-System.txt',
				f'{filesDir}events-Application.json',
				f'{filesDir}events-Security.json',
				f'{filesDir}events-System.json',
				f'{filesDir}eventsFiltered-Application.json',
				f'{filesDir}eventsFiltered-Security.json',
				f'{filesDir}eventsFiltered-System.json'
				]
	for fileToDel in filesToDel:
		logger.info(f'Attempting to delete {filesToDel}...')
		try:
			os.remove(fileToDel)
		except Exception as e:
			logger.error(f'Failed to delete {fileToDel}')

def getMsInfo(msinfoOutput):
	if platform.system() == 'Windows':
		route 				= '/payload/sendfile'
		logger.info('Starting MSINFO Collection')
		msinfoOutput 		= runMsinfo(msinfoOutput)
		outZipFile 			= zipFile('msinfo.txt')
		uploadSuccess 		= sendPayloadFlask(route, outZipFile, deviceUuid)
		if uploadSuccess == True:
			delFile(outZipFile)
		else:
			logger.error(f'Upload failed.')
		result = runAndreiMsInfo()
	else:
		logger.info('Skipping MSInfo as this is not a Windows Device.')

def getFileVersion(path, GetFileVersionInfo, LOWORD, HIWORD):
	try:
		info = GetFileVersionInfo (path, "\\")
		ms = info['FileVersionMS']
		ls = info['FileVersionLS']
	except Exception as e:
		logger.error(f'Version Data not found. Reason: {e}')
	try:
		installedVersion = str(HIWORD (ms)) + '.' + \
						str(LOWORD (ms)) + '.' + \
						str(HIWORD (ls)) + '.' + \
						str(LOWORD (ls))
		return(installedVersion)
	except Exception as e:
		logger.error(f'error: {e}')
		return('0.0.0.0')

def getFileModifiedDate(path):
	modDate = int(os.path.getmtime(path))
	return(modDate)

def getDrivers(deviceDataDict):
	driverDict = {}
	if platform.system() == 'Windows':
		from win32api import GetFileVersionInfo, LOWORD, HIWORD
		goodSection = False
		with open(msinfoOutput, 'r', encoding='utf-16') as f:
			lines = f.readlines()
			for line in lines:
#				print(f'line: {line.strip()} | {len(line)}')
				if '[System Drivers]' in line:
					goodSection = True
				if '[Environment Variables]' in line:
					goodSection = False
				if goodSection:
					if line.startswith('['): 
						pass
					elif len(line) < 5:
						pass
					elif line.startswith('Name\tDescription'):
						pass
					else:
						lineParts 	= line.split('\t')
						driverName 	= lineParts[0]
						driverDesc 	= lineParts[1]
						driverPath	= lineParts[2]
						driverType 	= lineParts[3]
						driverDict[driverName] = {}
						driverDict[driverName]['description'] = driverDesc
						driverDict[driverName]['driverpath'] = driverPath
						driverDict[driverName]['drivertype'] = driverType
		deviceDataDict['drivers'] = driverDict

		for driverName, driverData in deviceDataDict['drivers'].items():
			installedVersion = getFileVersion(driverData['driverpath'], GetFileVersionInfo, LOWORD, HIWORD)
			deviceDataDict['drivers'][driverName]['version'] = installedVersion
			modDate = getFileModifiedDate(driverData['driverpath'])
			deviceDataDict['drivers'][driverName]['driverdate'] = modDate
	else:
		deviceDataDict['drivers'] = {}
#	sendMetaMetadata(deviceUuid, deviceDataDict['drivers'], 'windrivers')
	return(deviceDataDict)

def sendMetaMetadata(deviceUuid, data, metaName):
	url = f'https://{host}/metadata'
	body = {
		'deviceuuid':deviceUuid,
		'metalogos_type': metaName,
		'metalogos':data
		}
	
	headers 	= {'Content-Type': 'application/json'}
	logger.info(f'Attempting to POST to: {url}')
	response 	= requests.post(url, headers=headers, data=json.dumps(body))
	logger.info(f'response: {response.status_code}')
	if response.status_code != 201:
		logger.error(f'Failed to POST data. Reason: {response.text}')

##################################################
###################### MAIN ######################
##################################################

debugMode 			= True
host 				= 'app.wegweiser.tech'
port 				= 443
#args				= parseArgs()

if debugMode == True:
	logger.info('fullAudit Starting...')

appDir, \
	logDir, \
	configDir, \
	tempDir, \
	filesDir		= getAppDirs()
#logFile 			= f'{logDir}.log'
#logfile(logFile)
#logger.debug(f'logFile: {logFile}')
agentConfigFile 	= f'{configDir}agent.config'
deviceUuid, \
	host		= getDeviceUuid(agentConfigFile)
msinfoOutput 		= f'{filesDir}msinfo.txt'


###################### MSINFO ######################

getMsInfo(msinfoOutput)

###################### AUDIT ######################

deviceDataDict	= {}
deviceDataDict 	= getDeviceData(deviceDataDict)
deviceDataDict	= getSystemData(deviceDataDict)
deviceDataDict	= getDiskStats(deviceDataDict)
deviceDataDict 	= getNetworkData(deviceDataDict)
deviceDataDict	= getUserData(deviceDataDict)
deviceDataDict 	= getUptimeData(deviceDataDict)
deviceDataDict	= getBatteryData(deviceDataDict)
deviceDataDict	= getmemoryData(deviceDataDict)
deviceDataDict  = getCollectorData(deviceDataDict)
deviceDataDict 	= getManufacturer(deviceDataDict)
deviceDataDict 	= getOsLang(deviceDataDict)
deviceDataDict	= getCpuInfo(deviceDataDict)
deviceDataDict	= getGpuInfo(deviceDataDict)
deviceDataDict	= getSmBiosInfo(deviceDataDict)
deviceDataDict	= getSystemModel(deviceDataDict)
deviceDataDict	= getPrinters(deviceDataDict)
deviceDataDict	= getPciDevices(deviceDataDict)
deviceDataDict	= getUsbDevices(deviceDataDict)
deviceDataDict 	= getPartitionData(deviceDataDict)
deviceDataDict	= getDrivers(deviceDataDict)
servicesDict	= getServices()

###################### SEND RESULTS ######################

route = '/payload/sendaudit'
payload = {
	"data": deviceDataDict
}

if debugMode == True:
	print(f'payload dumps: {json.dumps(payload, indent=4)}')
	with open(f'{logDir}fullAudit.log', 'a') as f:
		f.write(json.dumps(deviceDataDict, indent=4))
response 	= sendJsonPayloadFlask(payload, route)
logger.info(f'Server response: {response} | {response.text}')











