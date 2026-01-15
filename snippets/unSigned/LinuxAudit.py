# Filepath: snippets/unSigned/LinuxAudit.py
"""
Linux-specific audit collector for Wegweiser
Collects comprehensive system information using psutil and Linux-specific tools
Self-contained snippet with all utilities inlined.
"""
import socket
import json
import os
import platform
import time
import getpass
import sys
import subprocess
import hashlib
import datetime
import math

# Import dependencies
try:
    from logzero import logger, logfile
except ImportError:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'logzero'])
    from logzero import logger, logfile

try:
    import psutil
except ImportError:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'psutil'])
    import psutil

try:
    import requests
except ImportError:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'requests'])
    import requests

try:
    import dns.resolver
except ImportError:
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
            deviceUuid = config.get('deviceuuid')  # lowercase to match config file
            host = config.get('serverAddr', 'app.wegweiser.tech')
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

###################### CONFIGURATION ######################

debugMode = True
host = 'app.wegweiser.tech'
port = 443

###################### FUNCTIONS ######################

def getCpuInfo(deviceDataDict):
    """Get CPU information including comprehensive psutil metrics"""
    try:
        # Get CPU name from lscpu
        result = subprocess.run(
            ['lscpu'],
            stdout=subprocess.PIPE,
            universal_newlines=True,
            timeout=10
        )
        cpuName = 'Unknown'
        for line in result.stdout.splitlines():
            if 'Model name' in line:
                cpuName = line.split('Model name:')[1].strip()
                break
        
        logger.info(f'cpuName: {cpuName}')
        
        # Get comprehensive CPU metrics
        cpu_metrics = getCpuMetrics()
        
        deviceDataDict['cpu'] = {
            'cpuname': cpuName,
            'cpu_metrics': cpu_metrics
        }
        
        return deviceDataDict
    except Exception as e:
        logger.error(f'Error getting CPU info: {e}')
        deviceDataDict['cpu'] = {
            'cpuname': 'Unknown',
            'cpu_metrics': {}
        }
        return deviceDataDict

def getMemoryData(deviceDataDict):
    """Get memory information including comprehensive psutil metrics"""
    try:
        vmem = psutil.virtual_memory()
        
        # Basic memory info
        totalMemory = vmem.total
        availableMemory = vmem.available
        usedMemory = vmem.used
        freeMemory = vmem.free
        
        # Get comprehensive memory metrics
        memory_metrics = getMemoryMetrics()
        
        deviceDataDict['memory'] = {
            'total': totalMemory,
            'available': availableMemory,
            'used': usedMemory,
            'free': freeMemory,
            'memory_metrics': memory_metrics
        }
        
        logger.info(f'Memory: {convertSize(totalMemory)} total')
        return deviceDataDict
    except Exception as e:
        logger.error(f'Error getting memory data: {e}')
        deviceDataDict['memory'] = {
            'total': 0,
            'available': 0,
            'used': 0,
            'free': 0,
            'memory_metrics': {}
        }
        return deviceDataDict

def getSystemData(deviceDataDict):
    """Get system information"""
    try:
        deviceDataDict['system'] = {
            'devicePlatform': f"{(platform.system() or 'Unknown')}-{(platform.release() or 'Unknown')}-{(platform.version() or 'Unknown')}",
            'systemName': socket.gethostname(),
            'currentUser': getpass.getuser(),
            'cpuUsage': psutil.cpu_percent(interval=1),
            'cpuCount': psutil.cpu_count(),
            'bootTime': psutil.boot_time(),
            'publicIp': getPublicIpAddr()
        }
        logger.info(f'System data collected')
        return deviceDataDict
    except Exception as e:
        logger.error(f'Error getting system data: {e}')
        return deviceDataDict

def getDiskStats(deviceDataDict):
    """Get disk statistics"""
    try:
        drives = []
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                drives.append({
                    'name': partition.device,
                    'total': usage.total,
                    'used': usage.used,
                    'free': usage.free,
                    'usedPer': usage.percent,
                    'freePer': 100 - usage.percent
                })
            except PermissionError:
                logger.debug(f'Permission denied for {partition.mountpoint}')

        deviceDataDict['drives'] = drives
        logger.info(f'Disk stats collected: {len(drives)} drives')
        return deviceDataDict
    except Exception as e:
        logger.error(f'Error getting disk stats: {e}')
        deviceDataDict['drives'] = []
        return deviceDataDict

def getNetworkData(deviceDataDict):
    """Get network interface information"""
    try:
        networkList = []
        for interface_name, interface_addrs in psutil.net_if_addrs().items():
            net_if_stats = psutil.net_if_stats()
            if interface_name in net_if_stats:
                stats = net_if_stats[interface_name]
                interface_data = {
                    interface_name: {
                        'ifIsUp': stats.isup,
                        'ifSpeed': stats.speed,
                        'ifMtu': stats.mtu,
                        'bytesSent': stats.bytes_sent,
                        'bytesRecv': stats.bytes_recv,
                        'errIn': stats.errin,
                        'errOut': stats.errout,
                        'address4': None,
                        'netmask4': None,
                        'broadcast4': None,
                        'address6': None,
                        'netmask6': None,
                        'broadcast6': None
                    }
                }

                for addr in interface_addrs:
                    if addr.family.name == 'AF_INET':
                        interface_data[interface_name]['address4'] = addr.address
                        interface_data[interface_name]['netmask4'] = addr.netmask
                        interface_data[interface_name]['broadcast4'] = addr.broadcast
                    elif addr.family.name == 'AF_INET6':
                        interface_data[interface_name]['address6'] = addr.address
                        interface_data[interface_name]['netmask6'] = addr.netmask
                        interface_data[interface_name]['broadcast6'] = addr.broadcast

                networkList.append(interface_data)

        deviceDataDict['networkList'] = networkList
        logger.info(f'Network data collected: {len(networkList)} interfaces')
        return deviceDataDict
    except Exception as e:
        logger.error(f'Error getting network data: {e}')
        deviceDataDict['networkList'] = []
        return deviceDataDict

def getUserData(deviceDataDict):
    """Get logged-in users"""
    try:
        users = []
        user_dict = {}
        for idx, user in enumerate(psutil.users()):
            user_dict[str(idx)] = {
                'username': user.name,
                'terminal': user.terminal or 'N/A',
                'host': user.host or 'N/A',
                'loggedIn': user.started,
                'pid': user.pid or 0
            }
        users.append(user_dict)

        deviceDataDict['Users'] = users
        logger.info(f'User data collected: {len(user_dict)} users')
        return deviceDataDict
    except Exception as e:
        logger.error(f'Error getting user data: {e}')
        deviceDataDict['Users'] = []
        return deviceDataDict

def getBatteryData(deviceDataDict):
    """Get battery information"""
    try:
        battery = psutil.sensors_battery()
        if battery:
            deviceDataDict['battery'] = {
                'installed': True,
                'pcCharged': battery.percent,
                'secsLeft': int(battery.secsleft) if (isinstance(battery.secsleft, (int, float)) and battery.secsleft >= 0) else -1,
                'powerPlug': battery.power_plugged
            }
        else:
            deviceDataDict['battery'] = {
                'installed': False,
                'pcCharged': 0,
                'secsLeft': -1,
                'powerPlug': True
            }
        logger.info(f'Battery data collected')
        return deviceDataDict
    except Exception as e:
        logger.error(f'Error getting battery data: {e}')
        deviceDataDict['battery'] = {
            'installed': False,
            'pcCharged': 0,
            'secsLeft': -1,
            'powerPlug': True
        }
        return deviceDataDict

def getUptimeData(deviceDataDict):
    """Get uptime information"""
    try:
        boot_time = psutil.boot_time()
        deviceDataDict['uptime'] = {
            'bootTime': boot_time,
            'uptimeSeconds': time.time() - boot_time
        }
        logger.info(f'Uptime data collected')
        return deviceDataDict
    except Exception as e:
        logger.error(f'Error getting uptime data: {e}')
        return deviceDataDict

def getCollectorData(deviceDataDict):
    """Get collector version information"""
    try:
        agentVersionFile = os.path.join(configDir, 'agentVersion.txt')
        try:
            with open(agentVersionFile, 'r') as f:
                localAgentVersion = f.read().strip()
        except Exception:
            localAgentVersion = 'Unknown'
        deviceDataDict['collector'] = {
            'collversion': localAgentVersion,
            'collinstalldir': appDir
        }
        logger.info(f'Collector data collected')
        return deviceDataDict
    except Exception as e:
        logger.error(f'Error getting collector data: {e}')
        return deviceDataDict

def getDeviceData(deviceDataDict, deviceUuid):
    """Get basic device information"""
    try:
        deviceDataDict['device'] = {
            'deviceUuid': deviceUuid,
            'systemtime': time.time()
        }
        logger.info(f'Device data collected')
        return deviceDataDict
    except Exception as e:
        logger.error(f'Error getting device data: {e}')
        return deviceDataDict

def getPartitionData(deviceDataDict):
    """Get partition information"""
    try:
        partitions = []
        partition_dict = {}
        for idx, partition in enumerate(psutil.disk_partitions()):
            partition_dict[partition.mountpoint] = {
                'device': partition.device,
                'fstype': partition.fstype
            }
        partitions.append(partition_dict)

        deviceDataDict['partitions'] = partitions
        logger.info(f'Partition data collected: {len(partition_dict)} partitions')
        return deviceDataDict
    except Exception as e:
        logger.error(f'Error getting partition data: {e}')
        deviceDataDict['partitions'] = []
        return deviceDataDict

def getGpuInfo(deviceDataDict):
    """Get GPU information (Linux-specific)"""
    try:
        vendor = 'No data found'
        product = 'No data found'
        colourDepth = -1
        hRes = -1
        vRes = -1

        # Try lspci for GPU info
        try:
            result = subprocess.run(
                ['lspci'],
                stdout=subprocess.PIPE,
                universal_newlines=True,
                timeout=10
            )
            for line in result.stdout.splitlines():
                if 'VGA' in line or 'Display' in line:
                    parts = line.split(': ')
                    if len(parts) > 1:
                        product = parts[1]
                    break
        except:
            pass

        deviceDataDict['gpuinfo'] = {
            'gpuvendor': vendor,
            'gpuproduct': product,
            'gpucolour': colourDepth,
            'gpuhres': hRes,
            'gpuvres': vRes
        }
        logger.info(f'GPU info collected')
        return deviceDataDict
    except Exception as e:
        logger.error(f'Error getting GPU info: {e}')
        deviceDataDict['gpuinfo'] = {
            'gpuvendor': 'No data found',
            'gpuproduct': 'No data found',
            'gpucolour': -1,
            'gpuhres': -1,
            'gpuvres': -1
        }
        return deviceDataDict

def getManufacturer(deviceDataDict):
    """Get system manufacturer"""
    try:
        manufacturer = 'Unknown'
        # Try dmidecode
        try:
            result = subprocess.run(
                ['sudo', 'dmidecode', '-s', 'system-manufacturer'],
                stdout=subprocess.PIPE,
                universal_newlines=True,
                timeout=10
            )
            manufacturer = result.stdout.strip() or 'Unknown'
        except:
            pass

        deviceDataDict['manufacturer'] = manufacturer
        logger.info(f'Manufacturer: {manufacturer}')
        return deviceDataDict
    except Exception as e:
        logger.error(f'Error getting manufacturer: {e}')
        deviceDataDict['manufacturer'] = 'Unknown'
        return deviceDataDict

def getOsLang(deviceDataDict):
    """Get OS language"""
    try:
        osLang = 'Unknown'
        try:
            result = subprocess.run(
                ['locale'],
                stdout=subprocess.PIPE,
                universal_newlines=True,
                timeout=10
            )
            for line in result.stdout.splitlines():
                if 'LANG=' in line:
                    osLang = line.split('=')[1]
                    break
        except:
            pass

        deviceDataDict['osLang'] = osLang
        logger.info(f'OS Language: {osLang}')
        return deviceDataDict
    except Exception as e:
        logger.error(f'Error getting OS language: {e}')
        deviceDataDict['osLang'] = 'Unknown'
        return deviceDataDict

def getSmBiosInfo(deviceDataDict):
    """Get SMBIOS information (Linux-specific)"""
    try:
        smbios_dict = {}
        try:
            result = subprocess.run(
                ['sudo', 'dmidecode'],
                stdout=subprocess.PIPE,
                universal_newlines=True,
                timeout=10
            )
            for line in result.stdout.splitlines():
                if 'Serial Number' in line:
                    smbios_dict['serialNumber'] = line.split(':')[1].strip()
                if 'Chassis Type' in line:
                    smbios_dict['chassisType'] = line.split(':')[1].strip()
        except:
            pass

        deviceDataDict['smbios'] = smbios_dict
        logger.info(f'SMBIOS info collected')
        return deviceDataDict
    except Exception as e:
        logger.error(f'Error getting SMBIOS info: {e}')
        deviceDataDict['smbios'] = {}
        return deviceDataDict

def getSystemModel(deviceDataDict):
    """Get system model"""
    try:
        model = 'Unknown'
        try:
            result = subprocess.run(
                ['sudo', 'dmidecode', '-s', 'system-product-name'],
                stdout=subprocess.PIPE,
                universal_newlines=True,
                timeout=10
            )
            model = result.stdout.strip() or 'Unknown'
        except:
            pass

        deviceDataDict['systemModel'] = model
        logger.info(f'System Model: {model}')
        return deviceDataDict
    except Exception as e:
        logger.error(f'Error getting system model: {e}')
        deviceDataDict['systemModel'] = 'Unknown'
        return deviceDataDict

def getPrinters(deviceDataDict):
    """Get printer information"""
    try:
        printers = []
        try:
            result = subprocess.run(
                ['lpstat', '-p', '-d'],
                stdout=subprocess.PIPE,
                universal_newlines=True,
                timeout=10
            )
            for line in result.stdout.splitlines():
                if 'printer' in line.lower():
                    printers.append(line.strip())
        except:
            pass

        deviceDataDict['printers'] = printers
        logger.info(f'Printers collected: {len(printers)}')
        return deviceDataDict
    except Exception as e:
        logger.error(f'Error getting printers: {e}')
        deviceDataDict['printers'] = []
        return deviceDataDict

def getUsbDevices(deviceDataDict):
    """Get USB device information"""
    try:
        usb_devices = []
        try:
            result = subprocess.run(
                ['lsusb'],
                stdout=subprocess.PIPE,
                universal_newlines=True,
                timeout=10
            )
            usb_devices = result.stdout.splitlines()
        except:
            pass

        deviceDataDict['usbDevices'] = usb_devices
        logger.info(f'USB devices collected: {len(usb_devices)}')
        return deviceDataDict
    except Exception as e:
        logger.error(f'Error getting USB devices: {e}')
        deviceDataDict['usbDevices'] = []
        return deviceDataDict

def getPciDevices(deviceDataDict):
    """Get PCI device information (Linux-specific)"""
    try:
        pci_devices = []
        try:
            result = subprocess.run(
                ['lspci'],
                stdout=subprocess.PIPE,
                universal_newlines=True,
                timeout=10
            )
            pci_devices = result.stdout.splitlines()
        except:
            pass

        deviceDataDict['pciDevices'] = pci_devices
        logger.info(f'PCI devices collected: {len(pci_devices)}')
        return deviceDataDict
    except Exception as e:
        logger.error(f'Error getting PCI devices: {e}')
        deviceDataDict['pciDevices'] = []
        return deviceDataDict

###################### MAIN EXECUTION ######################

if __name__ == '__main__':
    if debugMode:
        logger.info('LinuxAudit Starting...')

    # Setup directories
    appDir, logDir, configDir, tempDir, filesDir = getAppDirs()

    # Get device UUID and host
    agentConfigFile = os.path.join(configDir, 'agent.config')
    deviceUuid, host = getDeviceUuid(agentConfigFile)

    # Collect all data
    deviceDataDict = {}
    deviceDataDict = getDeviceData(deviceDataDict, deviceUuid)
    deviceDataDict = getSystemData(deviceDataDict)
    deviceDataDict = getDiskStats(deviceDataDict)
    deviceDataDict = getNetworkData(deviceDataDict)
    deviceDataDict = getUserData(deviceDataDict)
    deviceDataDict = getUptimeData(deviceDataDict)
    deviceDataDict = getBatteryData(deviceDataDict)
    deviceDataDict = getMemoryData(deviceDataDict)
    deviceDataDict = getCollectorData(deviceDataDict)
    deviceDataDict = getManufacturer(deviceDataDict)
    deviceDataDict = getOsLang(deviceDataDict)
    deviceDataDict = getCpuInfo(deviceDataDict)
    deviceDataDict = getGpuInfo(deviceDataDict)
    deviceDataDict = getSmBiosInfo(deviceDataDict)
    deviceDataDict = getSystemModel(deviceDataDict)
    deviceDataDict = getPrinters(deviceDataDict)
    deviceDataDict = getUsbDevices(deviceDataDict)
    deviceDataDict = getPciDevices(deviceDataDict)
    deviceDataDict = getPartitionData(deviceDataDict)

    # Update device UUID in payload
    deviceDataDict['device']['deviceUuid'] = deviceUuid

    # Send payload
    route = '/payload/sendaudit'
    payload = {'data': deviceDataDict}

    if debugMode:
        logger.info(f'Payload: {json.dumps(payload, indent=2, default=str)}')

    response = sendJsonPayloadFlask(payload, route, host, debugMode)
    logger.info(f'Server response: {response.status_code} | {response.text}')

