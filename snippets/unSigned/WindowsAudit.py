# Filepath: snippets/unSigned/WindowsAudit.py
"""
Windows-specific audit collector for Wegweiser
Collects comprehensive system information using psutil and Windows-specific tools
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
import uuid
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

try:
    import win32api
except ImportError:
    logger.info('Installing pypiwin32...')
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pypiwin32'])
    import win32api

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
        deviceUuid = config.get('deviceuuid')
        host = config.get('serverAddr', 'app.wegweiser.tech')
        if not deviceUuid:
            logger.error('deviceuuid not found in config file.')
            return None, host
        try:
            uuid.UUID(str(deviceUuid))
        except Exception:
            logger.error(f'Invalid deviceuuid format in config: {deviceUuid}')
            return None, host
        logger.info(f'deviceUuid: {deviceUuid}')
        return deviceUuid, host
    except Exception as e:
        logger.error(f'Failed to read config file: {e}')
        return None, 'app.wegweiser.tech'

def getAppDirs():
    """Get application directories"""
    if platform.system() == 'Windows':
        appDir = r'c:\program files (x86)\Wegweiser'
        logDir = os.path.join(appDir, 'Logs')
        configDir = os.path.join(appDir, 'Config')
        tempDir = os.path.join(appDir, 'Temp')
        filesDir = os.path.join(appDir, 'Files')
    else:
        # Fallback for non-Windows or dev environments
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
        # Get CPU name from WMI
        command = "(Get-WmiObject Win32_Processor).Name"
        result = subprocess.run(
            ["powershell", "-Command", command],
            stdout=subprocess.PIPE,
            universal_newlines=True,
            timeout=10
        )
        cpuName = ' '.join(result.stdout.split()) if result.stdout else 'Unknown'
        
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
        plat = platform.system() or 'Unknown'
        rel = platform.release() or 'Unknown'
        ver = platform.version() or 'Unknown'
        device_platform = f"{plat}-{rel}-{ver}"

        deviceDataDict['system'] = {
            'devicePlatform': device_platform,
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
        net_if_stats = psutil.net_if_stats()
        net_io = psutil.net_io_counters(pernic=True)
        for interface_name, interface_addrs in psutil.net_if_addrs().items():
            stats = net_if_stats.get(interface_name)
            if not stats:
                continue
            iface = {
                'ifIsUp': stats.isup,
                'ifSpeed': stats.speed,
                'ifMtu': stats.mtu,
                'bytesSent': 0,
                'bytesRecv': 0,
                'errIn': 0,
                'errOut': 0,
                'address4': None,
                'netmask4': None,
                'broadcast4': None,
                'address6': None,
                'netmask6': None,
                'broadcast6': None
            }
            io = net_io.get(interface_name)
            if io:
                iface['bytesSent'] = io.bytes_recv
                iface['bytesRecv'] = io.bytes_sent
                iface['errIn'] = io.errin
                iface['errOut'] = io.errout

            for addr in interface_addrs:
                if addr.family == socket.AF_INET:
                    iface['address4'] = addr.address
                    iface['netmask4'] = addr.netmask
                    iface['broadcast4'] = addr.broadcast
                elif addr.family == socket.AF_INET6:
                    iface['address6'] = addr.address
                    iface['netmask6'] = addr.netmask
                    iface['broadcast6'] = addr.broadcast

            networkList.append({interface_name: iface})

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
                'secsLeft': battery.secsleft if battery.secsleft != psutil.POWER_TIME_UNLIMITED else -1,
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
    """Get collector version information aligned with server expectations"""
    try:
        # Determine install and config directories
        app_dir, _, config_dir, _, _ = getAppDirs()
        # Read agent version from Config/agentVersion.txt (fallback to 0)
        version_path = os.path.join(config_dir, 'agentVersion.txt')
        local_version = 0
        try:
            with open(version_path, 'r') as f:
                v = f.read().strip()
                if v.isdigit():
                    local_version = int(v)
        except Exception as ve:
            logger.warning(f'agentVersion.txt not found or invalid: {ve}')
            local_version = 0
        # Populate collector fields expected by server
        deviceDataDict.setdefault('collector', {})
        deviceDataDict['collector']['collversion'] = local_version
        deviceDataDict['collector']['collinstalldir'] = app_dir
        logger.info('Collector data collected')
        return deviceDataDict
    except Exception as e:
        # Ensure keys exist to avoid server-side KeyError
        deviceDataDict.setdefault('collector', {})
        deviceDataDict['collector'].setdefault('collversion', 0)
        deviceDataDict['collector'].setdefault('collinstalldir', 'unknown')
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
    """Get GPU information (Windows-specific)"""
    try:
        command = "(Get-WmiObject Win32_VideoController)"
        result = subprocess.run(
            ["powershell", "-Command", command],
            stdout=subprocess.PIPE,
            universal_newlines=True,
            timeout=10
        )

        vendor = 'No data found'
        product = 'No data found'
        colourDepth = -1
        hRes = -1
        vRes = -1

        for line in result.stdout.splitlines():
            if 'VideoProcessor' in line:
                product = line.split('VideoProcessor')[1].split(':')[1].strip()
            if 'VideoModeDescription' in line:
                try:
                    colourDepth = line.split('x ')[2].split(' ')[0]
                    colourDepth = int(colourDepth)
                    if colourDepth > 2147483647:
                        colourDepth = 2147483647
                    hRes = int(line.split(': ')[1].split(' ')[0])
                    vRes = int(line.split('x ')[1].split(' ')[0])
                except:
                    pass
            if 'AdapterDACType' in line:
                vendor = line.split('AdapterDACType')[1].split(':')[1].strip()

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
        command = "(Get-WmiObject Win32_ComputerSystemProduct).Vendor"
        result = subprocess.run(
            ["powershell", "-Command", command],
            stdout=subprocess.PIPE,
            universal_newlines=True,
            timeout=10
        )
        manufacturer = result.stdout.strip() or 'Unknown'
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
        command = "(Get-WmiObject Win32_OperatingSystem).MUILanguages"
        result = subprocess.run(
            ["powershell", "-Command", command],
            stdout=subprocess.PIPE,
            universal_newlines=True,
            timeout=10
        )
        osLang = result.stdout.strip() or 'Unknown'
        deviceDataDict['osLang'] = osLang
        logger.info(f'OS Language: {osLang}')
        return deviceDataDict
    except Exception as e:
        logger.error(f'Error getting OS language: {e}')
        deviceDataDict['osLang'] = 'Unknown'
        return deviceDataDict

def getSmBiosInfo(deviceDataDict):
    """Get SMBIOS information (Windows-specific)"""
    try:
        command = "(Get-WmiObject Win32_SystemEnclosure)"
        result = subprocess.run(
            ["powershell", "-Command", command],
            stdout=subprocess.PIPE,
            universal_newlines=True,
            timeout=10
        )

        smbios_dict = {}
        for line in result.stdout.splitlines():
            if 'SerialNumber' in line:
                smbios_dict['serialNumber'] = line.split(':')[1].strip()
            if 'ChassisTypes' in line:
                smbios_dict['chassisType'] = line.split(':')[1].strip()

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
        command = "(Get-WmiObject Win32_ComputerSystem).Model"
        result = subprocess.run(
            ["powershell", "-Command", command],
            stdout=subprocess.PIPE,
            universal_newlines=True,
            timeout=10
        )
        model = result.stdout.strip() or 'Unknown'
        deviceDataDict['systemModel'] = model
        logger.info(f'System Model: {model}')
        return deviceDataDict
    except Exception as e:
        logger.error(f'Error getting system model: {e}')
        deviceDataDict['systemModel'] = 'Unknown'
        return deviceDataDict

def getPrinters(deviceDataDict):
    """Get printer information"""

    # Win32_Printer PrinterStatus codes mapping
    PRINTER_STATUS_MAP = {
        1: "Other",
        2: "Unknown",
        3: "Idle",
        4: "Printing",
        5: "Warming Up",
        6: "Stopped Printing",
        7: "Offline"
    }

    def convert_printer_status(status):
        """Convert numeric PrinterStatus code to human-readable string"""
        if status is None:
            return "Unknown"
        try:
            status_int = int(status)
            return PRINTER_STATUS_MAP.get(status_int, f"Unknown ({status_int})")
        except (ValueError, TypeError):
            return str(status)

    try:
        command = """
        Get-WmiObject Win32_Printer | ForEach-Object {
            [PSCustomObject]@{
                Name = $_.Name
                DriverName = $_.DriverName
                PortName = $_.PortName
                Location = $_.Location
                PrinterStatus = $_.PrinterStatus
                Default = $_.Default
            }
        } | ConvertTo-Json
        """
        result = subprocess.run(
            ["powershell", "-Command", command],
            stdout=subprocess.PIPE,
            universal_newlines=True,
            timeout=10
        )

        printers_dict = {}
        if result.stdout.strip():
            try:
                printers_json = json.loads(result.stdout)
                # Handle single printer (not in array) vs multiple printers (in array)
                if not isinstance(printers_json, list):
                    printers_json = [printers_json]

                for printer in printers_json:
                    name = printer.get('Name', 'Unknown')
                    status_code = printer.get('PrinterStatus', 'unknown')
                    printers_dict[name] = {
                        'drivername': printer.get('DriverName', 'unknown'),
                        'location': printer.get('Location', 'unknown') if printer.get('Location') else 'unknown',
                        'printerstatus': convert_printer_status(status_code),
                        'portname': printer.get('PortName', 'unknown'),
                        'default': printer.get('Default', False)
                    }
            except json.JSONDecodeError as e:
                logger.error(f'Error parsing printer JSON: {e}')
                # Fallback to simple name collection
                for line in result.stdout.splitlines():
                    if line.strip() and 'Name' not in line and '---' not in line:
                        name = line.strip()
                        printers_dict[name] = {
                            'drivername': 'unknown',
                            'location': 'unknown',
                            'printerstatus': 'unknown',
                            'portname': 'unknown',
                            'default': False
                        }

        deviceDataDict['printers'] = printers_dict
        logger.info(f'Printers collected: {len(printers_dict)}')
        return deviceDataDict
    except Exception as e:
        logger.error(f'Error getting printers: {e}')
        deviceDataDict['printers'] = []
        return deviceDataDict

def getUsbDevices(deviceDataDict):
    """Get USB device information"""
    try:
        command = "Get-WmiObject Win32_USBControllerDevice | Select-Object Dependent"
        result = subprocess.run(
            ["powershell", "-Command", command],
            stdout=subprocess.PIPE,
            universal_newlines=True,
            timeout=10
        )

        usb_devices = []
        for line in result.stdout.splitlines():
            if 'Win32_' in line:
                usb_devices.append(line.strip())

        deviceDataDict['usbDevices'] = usb_devices
        logger.info(f'USB devices collected: {len(usb_devices)}')
        return deviceDataDict
    except Exception as e:
        logger.error(f'Error getting USB devices: {e}')
        deviceDataDict['usbDevices'] = []
        return deviceDataDict

def getDrivers(deviceDataDict):
    """Get driver information (Windows-specific) and return a dict keyed by driver name"""
    try:
        # Use PowerShell to emit JSON for robust parsing
        command = (
            "Get-WmiObject Win32_SystemDriver | "
            "Select-Object Name, Description, PathName, State, StartMode, ServiceType | "
            "ConvertTo-Json -Compress"
        )
        result = subprocess.run(
            ["powershell", "-Command", command],
            stdout=subprocess.PIPE,
            universal_newlines=True,
            timeout=15
        )

        drivers_dict = {}
        raw = result.stdout.strip()
        if raw:
            try:
                data = json.loads(raw)
                # Convert single object to list for uniformity
                if isinstance(data, dict):
                    data = [data]
                if isinstance(data, list):
                    for item in data:
                        try:
                            name = (item.get('Name') or '').strip()
                            if not name:
                                continue
                            description = (item.get('Description') or 'unknown').strip()
                            pathname = (item.get('PathName') or 'unknown').strip()
                            servicetype = (item.get('ServiceType') or 'unknown').strip()
                            version = 'unknown'
                            driverdate = 0
                            drivers_dict[name] = {
                                'description': description if description else 'unknown',
                                'driverpath': pathname if pathname else 'unknown',
                                'drivertype': servicetype if servicetype else 'unknown',
                                'version': version,
                                'driverdate': driverdate
                            }
                        except Exception:
                            continue
            except Exception:
                # Fallback: parse simple "Name State" lines if JSON parsing fails
                for line in raw.splitlines():
                    line = line.strip()
                    if line and 'Name' not in line and '---' not in line:
                        name = line.split()[0]
                        if name:
                            drivers_dict[name] = {
                                'description': 'unknown',
                                'driverpath': 'unknown',
                                'drivertype': 'unknown',
                                'version': 'unknown',
                                'driverdate': 0
                            }

        deviceDataDict['drivers'] = drivers_dict
        logger.info(f'Drivers collected: {len(drivers_dict)}')
        return deviceDataDict
    except Exception as e:
        logger.error(f'Error getting drivers: {e}')
        deviceDataDict['drivers'] = {}
        return deviceDataDict

###################### MAIN EXECUTION ######################

if __name__ == '__main__':
    if debugMode:
        logger.info('WindowsAudit Starting...')

    # Setup directories
    appDir, logDir, configDir, tempDir, filesDir = getAppDirs()

    # Get device UUID and host
    agentConfigFile = os.path.join(configDir, 'agent.config')
    deviceUuid, host = getDeviceUuid(agentConfigFile)
    if not deviceUuid:
        logger.error('Missing or invalid deviceUuid. Aborting upload.')
        sys.exit(1)

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
    deviceDataDict = getPartitionData(deviceDataDict)
    deviceDataDict = getDrivers(deviceDataDict)

    # Update device UUID in payload
    deviceDataDict['device']['deviceUuid'] = deviceUuid

    # Send payload
    route = '/payload/sendaudit'
    payload = {'data': deviceDataDict}

    if debugMode:
        logger.info(f'Payload: {json.dumps(payload, indent=2, default=str)}')

    response = sendJsonPayloadFlask(payload, route, host, debugMode)
    logger.info(f'Server response: {response.status_code} | {response.text}')

