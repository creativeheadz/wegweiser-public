# Filepath: snippets/unSigned/MacAudit.py
"""
macOS-specific audit collector for Wegweiser
Self-contained snippet with all utilities inlined.
"""
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

###################### INLINED UTILITIES (from AuditCommon) ######################

def convertSize(sizeBytes):
	"""Convert bytes to human-readable format"""
	if sizeBytes == 0:
		return "0 B"
	sizeName = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
	i = int(math.floor(math.log(sizeBytes, 1024)))
	p = math.pow(1024, i)
	s = round(sizeBytes / p, 2)
	return f'{s} {sizeName[i]}'

def sendJsonPayloadFlask(payload, endpoint, host, debugMode=False):
	"""Send JSON payload to Flask endpoint"""
	url = f'https://{host}{endpoint}'
	if debugMode:
		logger.debug(f'payload to send: {payload}')
		logger.debug(f'Attempting to connect to {url}')
	headers = {'Content-Type': 'application/json'}
	response = requests.post(url, headers=headers, data=json.dumps(payload))
	return response

def getPublicIpAddr():
	"""Get public IP address"""
	odDnsServer = '208.67.222.222'
	httpDnsServer = 'https://icanhazip.com'
	dnsResolver = dns.resolver.Resolver()
	dnsResolver.nameservers = [odDnsServer]
	publicIp = None

	try:
		answers = dnsResolver.resolve('myip.opendns.com', 'A')
		for ip in answers:
			publicIp = ip.to_text()
	except Exception as e:
		logger.error(f'Failed to get publicIP from {odDnsServer}. Reason: {e}')

	if not publicIp:
		try:
			r = requests.get(httpDnsServer)
			publicIp = r.text.strip()
		except Exception as e:
			logger.error(f'Failed to get publicIP from {httpDnsServer}. Reason: {e}')

	if not publicIp:
		publicIp = '0.0.0.0'

	return publicIp

def getUserHomePath():
	"""Get user home directory path"""
	userHomePath = os.path.expanduser("~")
	logger.info(f'userHomePath: {userHomePath}')
	return userHomePath

def getDeviceUuid(configFile):
	"""Get device UUID from config file"""
	logger.info(f'Attempting to read {configFile}')
	try:
		with open(configFile, 'r') as f:
			config = json.load(f)
			deviceUuid = config.get('deviceUuid')
			host = config.get('host', 'app.wegweiser.tech')
			logger.info(f'deviceUuid: {deviceUuid}')
			return deviceUuid, host
	except Exception as e:
		logger.error(f'Failed to read config file: {e}')
		return None, 'app.wegweiser.tech'

def getAppDirs():
	"""Get application directories"""
	userHomePath = getUserHomePath()
	appDir = os.path.join(userHomePath, '.wegweiser')
	logDir = os.path.join(appDir, 'logs')
	configDir = os.path.join(appDir, 'config')
	tempDir = os.path.join(appDir, 'temp')
	filesDir = os.path.join(appDir, 'files')

	for directory in [appDir, logDir, configDir, tempDir, filesDir]:
		os.makedirs(directory, exist_ok=True)

	logger.info(f'appDir: {appDir}')
	return appDir, logDir, configDir, tempDir, filesDir

def delFile(fileToDelete):
	"""Delete a file"""
	logger.info(f'Attempting to delete {fileToDelete}...')
	try:
		os.remove(fileToDelete)
		logger.info(f'Successfully deleted {fileToDelete}.')
	except Exception as e:
		logger.error(f'Failed to delete {fileToDelete}. Reason: {e}')

###################### INLINED PSUTIL METRICS (from PsutilMetrics) ######################

def getCpuMetrics():
	"""Gather comprehensive CPU metrics using psutil"""
	try:
		cpu_metrics = {}

		# Core information
		cpu_metrics['cores_logical'] = psutil.cpu_count(logical=True)
		cpu_metrics['cores_physical'] = psutil.cpu_count(logical=False)

		# Frequency information
		try:
			freq = psutil.cpu_freq()
			if freq:
				cpu_metrics['frequency_current'] = round(freq.current, 2)
				cpu_metrics['frequency_min'] = round(freq.min, 2)
				cpu_metrics['frequency_max'] = round(freq.max, 2)
		except Exception as e:
			logger.debug(f'Could not get CPU frequency: {e}')

		# Per-CPU usage percentage
		try:
			cpu_percent = psutil.cpu_percent(interval=1, percpu=True)
			cpu_metrics['cpu_percent'] = [round(p, 2) for p in cpu_percent]
		except Exception as e:
			logger.debug(f'Could not get per-CPU percent: {e}')

		# Overall CPU usage
		try:
			cpu_metrics['cpu_percent_overall'] = round(psutil.cpu_percent(interval=0.1), 2)
		except Exception as e:
			logger.debug(f'Could not get overall CPU percent: {e}')

		# CPU times (user, system, idle, iowait, irq, softirq)
		try:
			times = psutil.cpu_times()
			cpu_metrics['cpu_times'] = {
				'user': round(times.user, 2),
				'system': round(times.system, 2),
				'idle': round(times.idle, 2),
				'iowait': round(times.iowait, 2) if hasattr(times, 'iowait') else None,
				'irq': round(times.irq, 2) if hasattr(times, 'irq') else None,
				'softirq': round(times.softirq, 2) if hasattr(times, 'softirq') else None,
			}
		except Exception as e:
			logger.debug(f'Could not get CPU times: {e}')

		# CPU statistics (context switches, interrupts)
		try:
			stats = psutil.cpu_stats()
			cpu_metrics['cpu_stats'] = {
				'ctx_switches': stats.ctx_switches,
				'interrupts': stats.interrupts,
				'soft_interrupts': stats.soft_interrupts,
				'syscalls': stats.syscalls if hasattr(stats, 'syscalls') else None,
			}
		except Exception as e:
			logger.debug(f'Could not get CPU stats: {e}')

		logger.info(f'Successfully gathered CPU metrics')
		return cpu_metrics

	except Exception as e:
		logger.error(f'Error gathering CPU metrics: {e}')
		return {}

def getMemoryMetrics():
	"""Gather comprehensive memory metrics using psutil"""
	try:
		memory_metrics = {}

		# Virtual memory details
		try:
			vmem = psutil.virtual_memory()
			memory_metrics['buffers'] = vmem.buffers if hasattr(vmem, 'buffers') else None
			memory_metrics['cached'] = vmem.cached if hasattr(vmem, 'cached') else None
			memory_metrics['shared'] = vmem.shared if hasattr(vmem, 'shared') else None
			memory_metrics['percent'] = round(vmem.percent, 2)
		except Exception as e:
			logger.debug(f'Could not get virtual memory details: {e}')

		# Swap memory details
		try:
			swap = psutil.swap_memory()
			memory_metrics['swap_total'] = swap.total
			memory_metrics['swap_used'] = swap.used
			memory_metrics['swap_free'] = swap.free
			memory_metrics['swap_percent'] = round(swap.percent, 2)
		except Exception as e:
			logger.debug(f'Could not get swap memory details: {e}')

		logger.info(f'Successfully gathered memory metrics')
		return memory_metrics

	except Exception as e:
		logger.error(f'Error gathering memory metrics: {e}')
		return {}





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
	plat = 'macOS' if platform.system() == 'Darwin' else (platform.system() or 'Unknown')
	rel  = platform.release() or 'Unknown'
	ver  = platform.version() or 'Unknown'
	deviceDataDict['system']['devicePlatform'] 	= f"{plat}-{rel}-{ver}"
	deviceDataDict['system']['systemName']		= socket.gethostname()
	deviceDataDict['system']['currentUser']		= getpass.getuser()
	deviceDataDict['system']['cpuUsage']		= psutil.cpu_percent(4)
	deviceDataDict['system']['cpuCount'] 		= psutil.cpu_count()
	deviceDataDict['system']['publicIp'] 		= getPublicIpAddr()
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
		if ifName in ifDict:  # Only process interfaces we found before
			ifDict[ifName]['bytesSent'] 	= data.bytes_recv
			ifDict[ifName]['bytesRecv'] 	= data.bytes_sent
			ifDict[ifName]['errIn'] 		= data.errin
			ifDict[ifName]['errOut'] 		= data.errout

	psNetDict 									= psutil.net_if_addrs()
	for ifName, addresses in psNetDict.items():
		if ifName in ifDict:  # Only process interfaces we found before
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

# Windows-specific function removed for macOS-only script

def getDiskStats(deviceDataDict):
	"""Get disk usage statistics for macOS"""
	driveData = {}
	stat = shutil.disk_usage('/')
	total = stat.total
	used = stat.used
	free = stat.free
	usedPer = (used / total) * 100
	freePer = (free / total) * 100
	deviceDataDict['drives'] = []
	driveData['name'] = '/'
	driveData['total'] = total
	driveData['used'] = used
	driveData['free'] = free
	driveData['usedPer'] = usedPer
	driveData['freePer'] = freePer
	deviceDataDict['drives'].append(driveData)
	return(deviceDataDict)

def getBatteryData(deviceDataDict):
    battery = psutil.sensors_battery()
    deviceDataDict['battery'] = {}
    if battery:
        deviceDataDict['battery']['installed'] = True
        deviceDataDict['battery']['pcCharged'] = battery.percent
        # Fix for macOS battery seconds left handling
        if battery.secsleft == -2:  # Power connected
            deviceDataDict['battery']['secsLeft'] = -2
        elif battery.secsleft == -1:  # Calculating...
            deviceDataDict['battery']['secsLeft'] = -1
        else:
            deviceDataDict['battery']['secsLeft'] = battery.secsleft
        deviceDataDict['battery']['powerPlug'] = battery.power_plugged
    else:
        deviceDataDict['battery']['installed'] = False
        deviceDataDict['battery']['pcCharged'] = 0
        deviceDataDict['battery']['secsLeft'] = 0
        deviceDataDict['battery']['powerPlug'] = False
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
	"""Get memory information including comprehensive psutil metrics"""
	try:
		memory = psutil.virtual_memory()

		# Get comprehensive memory metrics
		try:
			memory_metrics = getMemoryMetrics()
		except:
			memory_metrics = {}

		deviceDataDict['memory'] = {
			'total': memory.total,
			'available': memory.available,
			'used': memory.used,
			'free': memory.free,
			'memory_metrics': memory_metrics
		}
		logger.info(f'Memory data collected')
		return(deviceDataDict)
	except Exception as e:
		logger.error(f'Error getting memory data: {e}')
		deviceDataDict['memory'] = {
			'total': 0,
			'available': 0,
			'used': 0,
			'free': 0,
			'memory_metrics': {}
		}
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
	"""Get config file path for macOS"""
	wegConfigFile = f'{configDir}agent.config'
	return(wegConfigFile)

def getAppDirs():
	"""Get application directories for macOS"""
	appDir = '/opt/Wegweiser/'
	logDir = os.path.join(appDir, 'Logs', '')
	configDir = os.path.join(appDir, 'Config', '')
	tempDir = os.path.join(appDir, 'Temp', '')
	filesDir = os.path.join(appDir, 'Files', '')
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

# Windows MSInfo functions removed - not applicable for macOS
# MSInfo processing removed - not applicable for macOS

def getCpuInfo(deviceDataDict):
	"""Get CPU information for macOS including comprehensive psutil metrics"""
	try:
		command = ['sysctl', '-n', 'machdep.cpu.brand_string']
		result = subprocess.run(command, capture_output=True, text=True, timeout=10)
		cpuName = result.stdout.strip() or 'Unknown'

		logger.info(f'cpuName: {cpuName}')

		# Get comprehensive CPU metrics
		try:
			cpu_metrics = getCpuMetrics()
		except:
			cpu_metrics = {}

		deviceDataDict['cpu'] = {
			'cpuname': cpuName,
			'cpu_metrics': cpu_metrics
		}
		return(deviceDataDict)
	except Exception as e:
		logger.error(f'Error getting CPU info: {e}')
		deviceDataDict['cpu'] = {
			'cpuname': 'Unknown',
			'cpu_metrics': {}
		}
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
	"""Get GPU information for macOS"""
	vendor = 'No data found'
	product = 'No data found'
	colourDepth = -1
	hRes = -1
	vRes = -1

	command = ['system_profiler', 'SPDisplaysDataType']
	result = subprocess.run(command, capture_output=True, text=True)
	for line in result.stdout.splitlines():
		if 'Chipset Model' in line:
			product = line.split(': ')[1].strip()
		if 'Vendor' in line:
			vendor = line.split(': ')[1].strip()
		if 'Resolution' in line:
			resolution = line.split(': ')[1].strip()
			try:
				hRes, vRes = resolution.split(' x ')
				hRes = int(hRes)
				vRes = ''.join(filter(str.isdigit, vRes))
				vRes = int(vRes) if vRes.isdigit() else -1
			except:
				hRes = -1
				vRes = -1
		if 'Framebuffer Depth' in line:
			try:
				colourDepth = int(line.split(': ')[1].strip().split('-')[0])
			except:
				colourDepth = -1

	deviceDataDict['gpuinfo'] = {}
	deviceDataDict['gpuinfo']['gpuvendor'] = vendor
	deviceDataDict['gpuinfo']['gpuproduct'] = product
	deviceDataDict['gpuinfo']['gpucolour'] = colourDepth
	deviceDataDict['gpuinfo']['gpuhres'] = hRes
	deviceDataDict['gpuinfo']['gpuvres'] = vRes
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
	"""Get system information for macOS using system_profiler"""
	vendor = 'Apple Inc.'
	serialNumber = 'n/a'
	version = 'n/a'

	try:
		command = ['system_profiler', 'SPHardwareDataType']
		result = subprocess.run(command, capture_output=True, text=True)
		for line in result.stdout.splitlines():
			if 'Serial Number' in line:
				serialNumber = line.split(': ')[1].strip()
			if 'Boot ROM Version' in line:
				version = line.split(': ')[1].strip()
	except Exception as e:
		logger.error(f'Failed to get system info: {e}')

	logger.info(f'vendor: {vendor}')
	logger.info(f'serialNumber: {serialNumber}')
	logger.info(f'version: {version}')
	deviceDataDict['bios'] = {}
	deviceDataDict['bios']['biosvendor'] = vendor
	deviceDataDict['bios']['serialnumber'] = serialNumber
	deviceDataDict['bios']['biosversion'] = version
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
	"""Get detailed system model for macOS including year and generation"""
	systemModel = 'n/a'
	modelIdentifier = 'n/a'
	modelName = 'n/a'

	try:
		command = ['system_profiler', 'SPHardwareDataType']
		result = subprocess.run(command, capture_output=True, text=True)
		for line in result.stdout.splitlines():
			if 'Model Name' in line:
				modelName = line.split(': ')[1].strip()
			elif 'Model Identifier' in line:
				modelIdentifier = line.split(': ')[1].strip()

		# Combine both for complete model info
		if modelName != 'n/a' and modelIdentifier != 'n/a':
			systemModel = f"{modelName} ({modelIdentifier})"
		elif modelName != 'n/a':
			systemModel = modelName
		elif modelIdentifier != 'n/a':
			systemModel = modelIdentifier

	except Exception as e:
		logger.error(f'Failed to get system model: {e}')

	logger.info(f'systemModel: {systemModel}')
	logger.info(f'modelName: {modelName}')
	logger.info(f'modelIdentifier: {modelIdentifier}')
	deviceDataDict['system']['systemmodel'] = systemModel
	deviceDataDict['system']['modelname'] = modelName
	deviceDataDict['system']['modelidentifier'] = modelIdentifier
	return(deviceDataDict)

def getServices():
	"""Get running services/daemons for macOS using launchctl"""
	logger.info('Attempting to get services...')
	servicesDict = {}

	try:
		# Get list of loaded services
		command = ['launchctl', 'list']
		result = subprocess.run(command, capture_output=True, text=True)

		for line in result.stdout.splitlines():
			if line.startswith('PID') or line.strip() == '':
				continue
			parts = line.split('\t')
			if len(parts) >= 3:
				pid = parts[0].strip()
				status = parts[1].strip()
				serviceName = parts[2].strip()

				# Determine friendly state
				if pid == '-':
					friendlyState = 'STOPPED'
				elif pid.isdigit():
					friendlyState = 'RUNNING'
				else:
					friendlyState = 'OTHER'

				servicesDict[serviceName] = {
					'displayname': serviceName,
					'currentstate': 1 if friendlyState == 'STOPPED' else 4,
					'friendlystate': friendlyState,
					'pid': pid if pid != '-' else None
				}
	except Exception as e:
		logger.error(f'Failed to get services: {e}')

	logger.info('Successfully collected services.')
	servicesDictFile = writeServicesJson(servicesDict)
	route = '/payload/sendfile'
	uploadSuccess = sendPayloadFlask(route, servicesDictFile, deviceUuid)
	if uploadSuccess:
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
	"""Get printer information for macOS"""
	printerDict = {}
	deviceDataDict['printers'] = []

	try:
		# Use lpstat to get printer information
		command = ['lpstat', '-p', '-l', '-s']
		result = subprocess.run(command, capture_output=True, text=True)

		for line in result.stdout.splitlines():
			if line.strip().startswith('printer'):
				printerName = line.split('printer ')[1].split(' ')[0].strip()
				if printerName not in printerDict:
					printerDict[printerName] = {}
			elif line.strip().startswith('system default'):
				defaultPrinter = line.split(':')[1].strip()
				if defaultPrinter in printerDict:
					printerDict[defaultPrinter]['default'] = True
			elif line.strip().startswith('device'):
				printerName = line.split('device for ')[1].split(':')[0]
				printerPort = ':'.join(line.split(':')[1:]).strip()
				if printerName in printerDict:
					printerDict[printerName]['portname'] = printerPort

		deviceDataDict['printers'] = printerDict
	except Exception as e:
		logger.error(f'Failed to get printer info: {e}')
		deviceDataDict['printers'] = {}

	return(deviceDataDict)

def getPciDevices(deviceDataDict):
	"""Get PCI device information for macOS using system_profiler"""
	pciDeviceDict = {}

	try:
		command = ['system_profiler', 'SPPCIDataType']
		result = subprocess.run(command, capture_output=True, text=True)

		current_device = None
		for line in result.stdout.splitlines():
			line = line.strip()
			if ':' in line and not line.startswith(' '):
				# This is a device name
				current_device = line.rstrip(':')
				pciDeviceDict[current_device] = {}
			elif current_device and 'Type:' in line:
				device_type = line.split('Type:')[1].strip()
				pciDeviceDict[current_device]['pnpclass'] = device_type

		deviceDataDict['pcidevices'] = pciDeviceDict
	except Exception as e:
		logger.error(f'Failed to get PCI devices: {e}')
		deviceDataDict['pcidevices'] = {}

	return(deviceDataDict)

def getUsbDevices(deviceDataDict):
	"""Get USB device information for macOS using system_profiler"""
	usbDeviceList = []

	try:
		command = ['system_profiler', 'SPUSBDataType']
		result = subprocess.run(command, capture_output=True, text=True)

		for line in result.stdout.splitlines():
			line = line.strip()
			if ':' in line and not line.startswith(' '):
				# This is a device name
				device_name = line.rstrip(':')
				if device_name not in usbDeviceList and device_name != 'USB':
					usbDeviceList.append(device_name)

		deviceDataDict['usbdevices'] = usbDeviceList
	except Exception as e:
		logger.error(f'Failed to get USB devices: {e}')
		deviceDataDict['usbdevices'] = []

	return(deviceDataDict)

# Windows Event Log functions removed - not applicable for macOS

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

# Windows/Linux log filtering functions removed - not applicable for macOS

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

# Linux log processing removed - not applicable for macOS

def getOsLang(deviceDataDict):
	"""Get system locale for macOS"""
	systemLocale = 'Not detected'

	try:
		# Get system locale using defaults command
		command = ['defaults', 'read', '-g', 'AppleLocale']
		result = subprocess.run(command, capture_output=True, text=True)
		if result.returncode == 0:
			systemLocale = result.stdout.strip()
		else:
			# Fallback to environment variable
			systemLocale = os.getenv('LANG', 'Not detected')
	except Exception as e:
		logger.error(f'Failed to get system locale: {e}')
		systemLocale = os.getenv('LANG', 'Not detected')

	logger.debug(f'systemLocale: {systemLocale}')
	deviceDataDict['system']['systemlocale'] = systemLocale
	return(deviceDataDict)

def getManufacturer(deviceDataDict):
    """Get system manufacturer for macOS"""
    systemManufacturer = 'Apple Inc.'  # macOS devices are always Apple

    logger.debug(f'systemManufacturer: {systemManufacturer}')
    deviceDataDict['system']['systemmanufacturer'] = systemManufacturer
    return(deviceDataDict)

# Windows-specific functions removed - not applicable for macOS

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

# getDrivers() function removed - not applicable for macOS

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
agentConfigFile 	= os.path.join(configDir, 'agent.config')
deviceUuid, \
	host		= getDeviceUuid(agentConfigFile)
msinfoOutput 		= f'{filesDir}msinfo.txt'


###################### MACOS AUDIT ######################

deviceDataDict = {}
deviceDataDict = getDeviceData(deviceDataDict)
deviceDataDict = getSystemData(deviceDataDict)
deviceDataDict = getDiskStats(deviceDataDict)
deviceDataDict = getNetworkData(deviceDataDict)
deviceDataDict = getUserData(deviceDataDict)
deviceDataDict = getUptimeData(deviceDataDict)
deviceDataDict = getBatteryData(deviceDataDict)
deviceDataDict = getmemoryData(deviceDataDict)
deviceDataDict = getCollectorData(deviceDataDict)
deviceDataDict = getManufacturer(deviceDataDict)
deviceDataDict = getOsLang(deviceDataDict)
deviceDataDict = getCpuInfo(deviceDataDict)
deviceDataDict = getGpuInfo(deviceDataDict)
deviceDataDict = getSmBiosInfo(deviceDataDict)
deviceDataDict = getSystemModel(deviceDataDict)
deviceDataDict = getPrinters(deviceDataDict)
deviceDataDict = getPciDevices(deviceDataDict)
deviceDataDict = getUsbDevices(deviceDataDict)
deviceDataDict = getPartitionData(deviceDataDict)
# getDrivers() removed - not applicable for macOS
servicesDict = getServices()

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











