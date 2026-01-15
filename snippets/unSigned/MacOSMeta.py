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

# Global variables for directories and config
appDir = '/opt/Wegweiser/'
logDir = f'{appDir}Logs/'
configDir = f'{appDir}Config/'
filesDir = f'{appDir}Files/'
tempDir = os.getenv('TMPDIR') or '/tmp'
host = None

def getAppDirs():
    """Initialize and create required directories"""
    for directory in [appDir, logDir, configDir, filesDir]:
        checkDir(directory)
    return(appDir, logDir, configDir, tempDir, filesDir)

def checkDir(dirToCheck):
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
    """Zip a file with proper error handling"""
    inFile = os.path.join(filesDir, fileToZip)
    outZipFile = os.path.join(filesDir, f"{fileToZip}.zip")
    
    logger.info(f'Zipping {inFile} to {outZipFile}')
    try:
        with zipfile.ZipFile(outZipFile, 'w', compression=zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(inFile, os.path.basename(inFile))
        logger.info(f'Successfully zipped {inFile} to {outZipFile}')
        return outZipFile
    except Exception as e:
        logger.error(f"Failed to create zip file: {e}")
        return None

def getDeviceUuid(configFile):
    """Get device UUID and host from config"""
    global host
    logger.info(f'Attempting to read config file: {configFile}...')
    try:
        with open(configFile, 'r') as f:
            configDict = json.load(f)
        logger.info(f'Successfully read {configFile}')
        deviceUuid = configDict['deviceuuid']
        host = configDict.get('serverAddr', 'app.wegweiser.tech')
        return deviceUuid, host
    except Exception as e:
        logger.error(f'Failed to read {configFile}: {e}')
        sys.exit(1)

def delFile(fileToDelete):
    logger.info(f'Attempting to delete {fileToDelete}...')
    try:
        os.remove(fileToDelete)
        logger.info(f'Successfully deleted {fileToDelete}.')
    except Exception as e:
        logger.error(f'Failed to delete {fileToDelete}. Reason: {e}')

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

def get_system_logs(days=30):
    """Collect and summarize 30 days of system logs locally"""
    logger.info(f"Collecting and processing {days} days of system logs...")

    # Define enhanced log categories to collect more meaningful data
    log_categories = [
        {
            'name': 'errors',
            'predicate': 'messageType >= 16',  # Error and Fault levels
            'description': 'System errors and faults',
            'style': 'json'  # Get structured data
        },
        {
            'name': 'security',
            'predicate': '(subsystem CONTAINS "security" OR category CONTAINS "security" OR subsystem CONTAINS "authorization" OR eventMessage CONTAINS "authentication" OR eventMessage CONTAINS "keychain" OR eventMessage CONTAINS "certificate")',
            'description': 'Security, authentication and authorization events',
            'style': 'json'
        },
        {
            'name': 'crashes',
            'predicate': '(eventMessage CONTAINS "crash" OR eventMessage CONTAINS "panic" OR eventMessage CONTAINS "abort" OR eventMessage CONTAINS "segmentation fault" OR eventMessage CONTAINS "terminated" OR subsystem CONTAINS "crash")',
            'description': 'Application crashes, panics and abnormal terminations',
            'style': 'json'
        },
        {
            'name': 'network',
            'predicate': '(subsystem CONTAINS "network" OR category CONTAINS "network" OR subsystem CONTAINS "wifi" OR subsystem CONTAINS "bluetooth" OR eventMessage CONTAINS "connection" OR eventMessage CONTAINS "socket")',
            'description': 'Network connectivity, WiFi, Bluetooth and socket events',
            'style': 'json'
        },
        {
            'name': 'performance',
            'predicate': '(eventMessage CONTAINS "slow" OR eventMessage CONTAINS "timeout" OR eventMessage CONTAINS "memory" OR eventMessage CONTAINS "cpu" OR subsystem CONTAINS "performance" OR category CONTAINS "performance")',
            'description': 'Performance issues, timeouts and resource problems',
            'style': 'json'
        },
        {
            'name': 'disk_io',
            'predicate': '(subsystem CONTAINS "disk" OR subsystem CONTAINS "storage" OR eventMessage CONTAINS "disk" OR eventMessage CONTAINS "volume" OR eventMessage CONTAINS "filesystem")',
            'description': 'Disk I/O, storage and filesystem events',
            'style': 'json'
        }
    ]

    summary_data = {
        'collection_period': f'{days} days',
        'categories': {},
        'total_events_processed': 0,
        'collection_timestamp': datetime.datetime.now().isoformat()
    }

    for category in log_categories:
        logger.info(f"Processing {category['name']} logs...")

        # Use JSON style for better structured parsing when available
        style = category.get('style', 'compact')
        cmd = [
            "log", "show",
            "--last", f"{days}d",
            "--predicate", category['predicate'],
            "--style", style
        ]

        try:
            # Use longer timeout for 30 days of data
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode != 0:
                logger.warning(f"log show for {category['name']} returned error: {result.stderr}")
                continue

            # Process and group the logs based on format
            if style == 'json':
                grouped_events = process_json_log_output(result.stdout, category['name'])
            else:
                grouped_events = process_log_output(result.stdout, category['name'])

            # Calculate health indicators for this category
            health_indicators = calculate_category_health(grouped_events, category['name'])

            summary_data['categories'][category['name']] = {
                'description': category['description'],
                'total_raw_lines': len(result.stdout.split('\n')),
                'grouped_events': grouped_events['top_events'],
                'unique_event_types': len(grouped_events['all_groups']),
                'total_events': grouped_events['total_count'],
                'parsing_success_rate': grouped_events.get('parsing_success_rate', 0),
                'health_indicators': health_indicators,
                'format': grouped_events.get('format', 'text')
            }

            summary_data['total_events_processed'] += grouped_events['total_count']
            logger.info(f"Processed {grouped_events['total_count']} {category['name']} events into {len(grouped_events['all_groups'])} groups")

        except subprocess.TimeoutExpired:
            logger.error(f"Timeout collecting {category['name']} logs")
            summary_data['categories'][category['name']] = {'error': 'timeout'}
        except Exception as e:
            logger.error(f"Error collecting {category['name']} logs: {e}")
            summary_data['categories'][category['name']] = {'error': str(e)}

    return summary_data

def process_json_log_output(log_output, category_name):
    """Process JSON-formatted log output for better structured data"""
    lines = log_output.strip().split('\n')
    event_groups = {}
    total_count = 0
    parsing_errors = 0

    logger.info(f"Processing {len(lines)} JSON log lines for {category_name}")

    for line in lines:
        if not line.strip():
            continue

        try:
            # Parse JSON log entry
            log_entry = json.loads(line)
            total_count += 1

            # Extract structured fields
            process = log_entry.get('process', 'unknown')
            subsystem = log_entry.get('subsystem', 'unknown')
            category = log_entry.get('category', 'unknown')
            message = log_entry.get('eventMessage', '')
            timestamp = log_entry.get('timestamp', 'recent')
            message_type = log_entry.get('messageType', 'default')

            # Map messageType to severity
            severity_map = {
                16: 'error',
                17: 'fault',
                0: 'default',
                1: 'info',
                2: 'debug'
            }
            severity = severity_map.get(message_type, 'unknown')

            # Normalize message for grouping
            normalized_message = normalize_message_enhanced(message)

            # Create meaningful grouping key
            if category_name == 'network':
                group_key = f"NET_{subsystem}_{category}:{normalized_message[:80]}"
            elif category_name == 'security':
                group_key = f"SEC_{process}_{subsystem}:{normalized_message[:80]}"
            elif category_name == 'errors':
                group_key = f"ERR_{severity}_{process}:{normalized_message[:80]}"
            elif category_name == 'crashes':
                group_key = f"CRASH_{process}:{normalized_message[:80]}"
            elif category_name == 'performance':
                group_key = f"PERF_{process}_{subsystem}:{normalized_message[:80]}"
            elif category_name == 'disk_io':
                group_key = f"DISK_{process}_{subsystem}:{normalized_message[:80]}"
            else:
                group_key = f"{process}_{subsystem}:{normalized_message[:80]}"

            if group_key not in event_groups:
                event_groups[group_key] = {
                    'process': process,
                    'subsystem': subsystem,
                    'category': category,
                    'severity': severity,
                    'message_type': message_type,
                    'message_pattern': normalized_message[:400],
                    'count': 0,
                    'first_seen': timestamp,
                    'sample_message': message[:500],
                    'structured_data': {
                        'process': process,
                        'subsystem': subsystem,
                        'category': category
                    }
                }

            event_groups[group_key]['count'] += 1

        except json.JSONDecodeError:
            parsing_errors += 1
            # Fallback to text processing for non-JSON lines
            continue
        except Exception as e:
            parsing_errors += 1
            logger.debug(f"Error processing JSON log entry: {e}")
            continue

    logger.info(f"Created {len(event_groups)} event groups from {total_count} JSON log entries")
    logger.info(f"JSON parsing errors: {parsing_errors}")

    # Sort by count and take top events
    sorted_groups = sorted(event_groups.items(), key=lambda x: x[1]['count'], reverse=True)
    top_events = []

    for group_key, data in sorted_groups[:30]:  # Top 30 for JSON data
        top_events.append({
            'process': data['process'],
            'subsystem': data['subsystem'],
            'category': data['category'],
            'severity': data['severity'],
            'message_type': data['message_type'],
            'message_pattern': data['message_pattern'],
            'count': data['count'],
            'first_seen': data['first_seen'],
            'sample_message': data['sample_message'],
            'percentage': round((data['count'] / total_count) * 100, 2) if total_count > 0 else 0,
            'group_key': group_key,
            'structured_data': data['structured_data']
        })

    return {
        'top_events': top_events,
        'all_groups': event_groups,
        'total_count': total_count,
        'parsing_success_rate': round(((total_count - parsing_errors) / total_count) * 100, 2) if total_count > 0 else 0,
        'format': 'json'
    }

def process_log_output(log_output, category_name):
    """Process raw log output and group similar events with simplified parsing"""
    lines = log_output.strip().split('\n')
    event_groups = {}
    total_count = 0
    parsing_errors = 0

    logger.info(f"Processing {len(lines)} lines for {category_name}")

    # Debug: Show first few lines to understand format
    if len(lines) > 0:
        logger.info(f"Sample log lines for {category_name}:")
        for i, line in enumerate(lines[:3]):
            logger.info(f"  Line {i+1}: {line[:100]}...")

    for line in lines:
        if not line.strip() or len(line) < 10:
            continue

        total_count += 1

        try:
            # SIMPLIFIED parsing - just extract basic info
            process = 'system'
            message = line.strip()

            # Try to extract process name from common patterns
            # Pattern 1: Look for word followed by [number]
            import re
            process_match = re.search(r'(\w+)\[\d+\]', line)
            if process_match:
                process = process_match.group(1)
            else:
                # Pattern 2: Look for process name after timestamp
                parts = line.split()
                if len(parts) >= 4:
                    # Usually: timestamp hostname process message...
                    potential_process = parts[2] if len(parts) > 2 else 'system'
                    if potential_process and len(potential_process) > 1:
                        process = potential_process.split('[')[0]  # Remove PID if present

            # Normalize message for grouping (remove variable data)
            normalized_message = normalize_message(message)

            # Create simple grouping key
            group_key = f"{process}:{normalized_message[:80]}"

            # Find process name (usually has [pid] or just process name)
            process_found = False
            for i, part in enumerate(parts):
                if '[' in part and ']' in part:
                    # Found process[pid] format
                    process = part.split('[')[0]
                    process_found = True
                    break
                elif i >= 2 and not process_found:  # Skip timestamp and hostname
                    # Might be just process name
                    if ':' not in part and '<' not in part:
                        process = part
                        process_found = True
                        break

            # Extract subsystem and category from <subsystem:category> format
            if '<' in line and '>' in line:
                subsystem_start = line.find('<') + 1
                subsystem_end = line.find('>', subsystem_start)
                if subsystem_end > subsystem_start:
                    subsystem_info = line[subsystem_start:subsystem_end]
                    if ':' in subsystem_info:
                        subsystem, category = subsystem_info.split(':', 1)
                    else:
                        subsystem = subsystem_info

            # Extract severity level
            severity_indicators = ['Error', 'Fault', 'Default', 'Info', 'Debug']
            for indicator in severity_indicators:
                if indicator in line:
                    severity = indicator.lower()
                    break

            # Extract the actual message (everything after the last colon)
            colon_positions = [i for i, char in enumerate(line) if char == ':']
            if colon_positions:
                # Take message after the last meaningful colon
                for pos in reversed(colon_positions):
                    potential_message = line[pos+1:].strip()
                    if len(potential_message) > 10:  # Meaningful message
                        message = potential_message
                        break

            # Normalize message for better grouping
            normalized_message = normalize_message_enhanced(message)

            # Create more meaningful grouping keys
            if category_name == 'network':
                group_key = f"NET_{subsystem}_{category}:{normalized_message[:60]}"
            elif category_name == 'security':
                group_key = f"SEC_{process}_{subsystem}:{normalized_message[:60]}"
            elif category_name == 'errors':
                group_key = f"ERR_{severity}_{process}:{normalized_message[:60]}"
            elif category_name == 'crashes':
                group_key = f"CRASH_{process}:{normalized_message[:60]}"
            else:
                group_key = f"{process}_{subsystem}:{normalized_message[:60]}"

            if group_key not in event_groups:
                event_groups[group_key] = {
                    'process': process,
                    'subsystem': subsystem,
                    'category': category,
                    'severity': severity,
                    'message_pattern': normalized_message[:300],
                    'count': 0,
                    'first_seen': parts[0] if len(parts) > 0 else 'recent',
                    'sample_message': message[:400],
                    'raw_sample': line[:500]  # Keep raw sample for debugging
                }

            event_groups[group_key]['count'] += 1

        except Exception as e:
            parsing_errors += 1
            logger.debug(f"Failed to parse line: {line[:100]}... Error: {e}")

            # Fallback: at least count the event even if parsing fails
            fallback_key = f"UNPARSED_{category_name}:generic_event"
            if fallback_key not in event_groups:
                event_groups[fallback_key] = {
                    'process': 'unknown',
                    'subsystem': 'unknown',
                    'category': 'unknown',
                    'severity': 'unknown',
                    'message_pattern': 'Failed to parse log entry',
                    'count': 0,
                    'first_seen': 'recent',
                    'sample_message': line[:200],
                    'raw_sample': line[:300]
                }
            event_groups[fallback_key]['count'] += 1
            continue

    logger.info(f"Created {len(event_groups)} event groups from {total_count} total events")
    logger.info(f"Parsing errors: {parsing_errors}")

    # Sort by count and take top events
    sorted_groups = sorted(event_groups.items(), key=lambda x: x[1]['count'], reverse=True)
    top_events = []

    for group_key, data in sorted_groups[:25]:  # Top 25 event types for better insight
        top_events.append({
            'process': data['process'],
            'subsystem': data['subsystem'],
            'category': data['category'],
            'severity': data['severity'],
            'message_pattern': data['message_pattern'],
            'count': data['count'],
            'first_seen': data['first_seen'],
            'sample_message': data['sample_message'],
            'percentage': round((data['count'] / total_count) * 100, 2) if total_count > 0 else 0,
            'group_key': group_key  # For debugging
        })

    return {
        'top_events': top_events,
        'all_groups': event_groups,
        'total_count': total_count,
        'parsing_success_rate': round(((total_count - parsing_errors) / total_count) * 100, 2) if total_count > 0 else 0
    }

def normalize_message(message):
    """Normalize log messages for grouping by removing variable data"""
    import re

    # Remove common variable patterns
    normalized = message

    # Remove file paths
    normalized = re.sub(r'/[/\w\.-]+', '[PATH]', normalized)

    # Remove PIDs and numeric IDs
    normalized = re.sub(r'\b\d{3,}\b', '[ID]', normalized)

    # Remove memory addresses
    normalized = re.sub(r'0x[0-9a-fA-F]+', '[ADDR]', normalized)

    # Remove UUIDs
    normalized = re.sub(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}', '[UUID]', normalized)

    # Remove timestamps
    normalized = re.sub(r'\d{4}-\d{2}-\d{2}[\s\T]\d{2}:\d{2}:\d{2}', '[TIMESTAMP]', normalized)

    # Remove IP addresses
    normalized = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[IP]', normalized)

    # Collapse multiple spaces
    normalized = re.sub(r'\s+', ' ', normalized)

    return normalized.strip()

def normalize_message_enhanced(message):
    """Enhanced normalization for better event grouping with more specific patterns"""
    import re

    # Start with basic normalization
    normalized = normalize_message(message)

    # Additional macOS-specific patterns

    # Remove bundle identifiers but keep the app name
    normalized = re.sub(r'com\.[a-zA-Z0-9\.-]+\.([a-zA-Z0-9]+)', r'[BUNDLE].\1', normalized)

    # Remove version numbers
    normalized = re.sub(r'\bv?\d+\.\d+(\.\d+)*\b', '[VERSION]', normalized)

    # Remove port numbers
    normalized = re.sub(r':\d{2,5}\b', ':[PORT]', normalized)

    # Remove MAC addresses
    normalized = re.sub(r'([0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}', '[MAC]', normalized)

    # Remove specific numeric values but keep error codes
    normalized = re.sub(r'\b\d{1,2}\b(?!\s*(error|code|status))', '[NUM]', normalized)

    # Remove temporary file names
    normalized = re.sub(r'tmp[a-zA-Z0-9]+', '[TMPFILE]', normalized)

    # Remove session IDs and tokens
    normalized = re.sub(r'\b[a-zA-Z0-9]{20,}\b', '[TOKEN]', normalized)

    # Normalize common network patterns
    normalized = re.sub(r'bytes?:\s*\d+', 'bytes: [SIZE]', normalized)
    normalized = re.sub(r'timeout:\s*\d+', 'timeout: [TIME]', normalized)
    normalized = re.sub(r'port\s+\d+', 'port [PORT]', normalized)

    # Normalize error patterns
    normalized = re.sub(r'error\s*[-:]?\s*\d+', 'error [CODE]', normalized)
    normalized = re.sub(r'errno\s*=?\s*\d+', 'errno=[CODE]', normalized)

    # Normalize memory/size patterns
    normalized = re.sub(r'\d+\s*(KB|MB|GB|bytes?)', '[SIZE]', normalized)

    # Remove specific device identifiers
    normalized = re.sub(r'device\s+[a-zA-Z0-9\-]+', 'device [ID]', normalized)

    # Collapse multiple spaces again
    normalized = re.sub(r'\s+', ' ', normalized)

    return normalized.strip()

def get_system_info():
    """Collect system information using system_profiler with filtered categories"""
    logger.info("Collecting system information...")
    # Reduce number of categories collected
    essential_categories = [
        "SPHardwareDataType",  # Basic hardware info
        "SPStorageDataType",   # Storage info only
    ]
    system_info = {}
    
    for category in essential_categories:
        cmd = ["system_profiler", category, "-json", "-detailLevel", "mini"]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            data = json.loads(result.stdout)
            # Filter out unnecessary fields
            if category in data:
                filtered_data = {}
                for key, value in data[category][0].items():
                    if key in ["serial_number", "capacity", "size", "model", "type"]:
                        filtered_data[key] = value
                system_info[category] = filtered_data
        except Exception as e:
            logger.error(f"Failed to collect {category}: {e}")
    
    return system_info

def get_system_stats():
    """Collect essential system statistics only"""
    logger.info("Collecting system statistics...")
    stats = {}
    
    # Disk usage - summary only
    try:
        df = subprocess.run(["df", "-h", "/"], capture_output=True, text=True)
        stats["disk_usage"] = df.stdout.split("\n")[1]  # Get only root partition info
    except Exception as e:
        logger.error(f"Failed to collect disk usage: {e}")
    
    # Memory usage - summary only
    try:
        vm_stat = subprocess.run(["vm_stat"], capture_output=True, text=True)
        stats["memory_stats"] = "\n".join(vm_stat.stdout.split("\n")[:5])  # Get only first 5 lines
    except Exception as e:
        logger.error(f"Failed to collect memory stats: {e}")
    
    # CPU load - summary only  
    try:
        top = subprocess.run(["top", "-l", "1", "-n", "1", "-stats", "pid,command,cpu"], 
                           capture_output=True, text=True)
        stats["cpu_stats"] = "\n".join(top.stdout.split("\n")[:10])  # Get only first 10 processes
    except Exception as e:
        logger.error(f"Failed to collect CPU stats: {e}")
    
    return stats

def collect_macos_metadata():
    """Main function to collect all MacOS metadata"""
    if platform.system() != "Darwin":
        logger.error("This script only runs on MacOS")
        return None
        
    try:
        logger.info("Starting MacOS metadata collection...")

        # Collect basic system info (fast)
        logger.info("Collecting basic system information...")
        system_info = get_system_info()
        system_stats = get_system_stats()

        # Process 30 days of logs and create summary (this takes time)
        logger.info("Processing 30 days of system logs - this may take several minutes...")
        system_logs_summary = get_system_logs(days=30)

        metadata = {
            "timestamp": datetime.datetime.now().isoformat(),
            "hostname": platform.node(),
            "os_version": platform.platform(),
            "data_type": "macos_metadata_with_log_summary",
            "system_logs_summary": system_logs_summary,  # Summarized, not raw
            "system_info": system_info,
            "system_stats": system_stats,
            "summary_stats": {
                "total_events_processed": system_logs_summary.get('total_events_processed', 0),
                "categories_analyzed": len(system_logs_summary.get('categories', {})),
                "collection_period": system_logs_summary.get('collection_period', '30 days')
            }
        }

        logger.info(f"MacOS metadata collection completed successfully")
        logger.info(f"Processed {metadata['summary_stats']['total_events_processed']} log events")
        logger.info(f"Analyzed {metadata['summary_stats']['categories_analyzed']} log categories")

        return metadata
    except Exception as e:
        logger.error(f"Error collecting metadata: {e}")
        return None

def send_metadata_to_server(deviceUuid, host, metadata):
    """Send metadata using the correct API endpoint"""
    try:
        body = {
            'deviceuuid': deviceUuid,
            'metalogos_type': 'macos-log-summary',
            'metalogos': metadata
        }

        url = f'https://{host}/ai/device/metadata'
        headers = {'Content-Type': 'application/json'}
        logger.info(f'Attempting to POST metadata to: {url}')

        response = requests.post(url, headers=headers, data=json.dumps(body))
        logger.info(f'Metadata API response: {response.status_code}')

        if response.status_code in [200, 201]:
            logger.info("Successfully sent macOS metadata to server")
            return True
        else:
            logger.error(f"Failed to send metadata. Status: {response.status_code}, Response: {response.text}")
            return False

    except Exception as e:
        logger.error(f"Error sending metadata: {str(e)}")
        return False

def main():
    if platform.system() != "Darwin":
        logger.error("This script only runs on MacOS")
        sys.exit(1)

    # Initialize logging
    logfile(os.path.join(logDir, "macos_metadata.log"))

    # Get config and device UUID
    wegConfigFile = os.path.join(configDir, 'agent.config')
    deviceUuid, host = getDeviceUuid(wegConfigFile)

    try:
        # Collect metadata
        metadata = collect_macos_metadata()
        if metadata is None:
            raise Exception("Failed to collect metadata")

        # Save metadata to file for debugging
        output_file = os.path.join(filesDir, "macos_metadata.json")
        with open(output_file, "w") as f:
            json.dump(metadata, f, indent=4)
        logger.info(f"Metadata saved to {output_file}")

        # Send metadata using the correct API endpoint
        if send_metadata_to_server(deviceUuid, host, metadata):
            logger.info("MacOS metadata collection and upload completed successfully")
        else:
            logger.error("Failed to upload metadata to server")

    except Exception as e:
        logger.error(f"Failed to collect MacOS metadata: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()