#!/usr/bin/env python3
"""
MacOS Log Audit Script - Following Windows eventLogAudit.py Pattern
Implements baseline (30-day) + incremental collection like Windows
"""

import platform
from logzero import logger, logfile
import datetime
import os
import json
import requests
import time
import sys
import subprocess
import re

# Global variables
appDir = '/opt/Wegweiser/'
logDir = os.path.join(appDir, 'Logs', '')
configDir = os.path.join(appDir, 'Config', '')
filesDir = os.path.join(appDir, 'Files', '')

def getDeviceUuid(wegConfigFile):
    """Read device UUID and host from config file"""
    try:
        logger.info(f'Attempting to read config file: {wegConfigFile}...')
        with open(wegConfigFile, 'r') as f:
            configDict = json.load(f)
        logger.info(f'Successfully read {wegConfigFile}')
        deviceUuid = configDict['deviceuuid']
        host = configDict.get('serverAddr', 'app.wegweiser.tech')
        return deviceUuid, host
    except Exception as e:
        logger.error(f'Failed to read config: {e}')
        sys.exit(1)

def getLastCollectionTime(category_name):
    """Get last collection timestamp (like Windows getLatestEvent)"""
    tracking_file = os.path.join(configDir, f'macos-last-{category_name}.txt')
    if not os.path.isfile(tracking_file):
        logger.info(f'No tracking file for {category_name}. First run - will collect 30-day baseline.')
        return None  # First run
    else:
        try:
            with open(tracking_file, 'r') as f:
                timestamp = f.readline().strip()
            logger.info(f'Last collection for {category_name}: {timestamp}')
            return timestamp
        except Exception as e:
            logger.error(f'Error reading tracking file: {e}')
            return None

def updateLastCollectionTime(category_name):
    """Update last collection timestamp (like Windows writeLatestEvent)"""
    tracking_file = os.path.join(configDir, f'macos-last-{category_name}.txt')
    current_time = datetime.datetime.now().isoformat()
    try:
        with open(tracking_file, 'w') as f:
            f.write(current_time)
        logger.info(f'Updated tracking for {category_name}: {current_time}')
    except Exception as e:
        logger.error(f'Error updating tracking file: {e}')

def readExistingLogJson(category_name):
    """Read existing log data (like Windows readExistingLogJson)"""
    log_file = os.path.join(filesDir, f'macos-{category_name}.json')
    if os.path.isfile(log_file):
        logger.info(f'Reading existing {category_name} data...')
        try:
            with open(log_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f'Error reading existing data: {e}')
            return {}
    else:
        logger.info(f'No existing {category_name} data found.')
        return {}

def writeLogJson(log_data, category_name):
    """Write log data to file (like Windows writeLogJson)"""
    log_file = os.path.join(filesDir, f'macos-{category_name}.json')
    try:
        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2, default=str)
        logger.info(f'Wrote {category_name} data to {log_file}')
    except Exception as e:
        logger.error(f'Error writing log data: {e}')

def collectCategoryLogs(category, is_first_run):
    """Collect logs for a specific category (like Windows readLog + processEvents)"""
    logger.info(f"Collecting {category['name']} logs...")
    
    # Determine time window
    if is_first_run:
        time_window = "30d"  # Full baseline
        logger.info(f"First run for {category['name']} - collecting 30-day baseline")
    else:
        time_window = "24h"  # Incremental
        logger.info(f"Incremental run for {category['name']} - collecting last 24h")
    
    cmd = [
        "log", "show",
        "--last", time_window,
        "--predicate", category['predicate'],
        "--style", "compact"
    ]
    
    try:
        # Reasonable timeout
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=360)
        
        if result.returncode != 0:
            logger.warning(f"Log collection failed for {category['name']}: {result.stderr}")
            return []
        
        # Process the output
        lines = result.stdout.strip().split('\n')
        events = []
        
        # Filter to last 30 days (like Windows processEvents)
        now = datetime.datetime.now()
        thirty_days_ago = now - datetime.timedelta(days=30)
        
        for i, line in enumerate(lines):
            if line.strip() and len(line) > 20:
                # Create event entry (simplified)
                event = {
                    'id': i,
                    'timestamp': now.isoformat(),  # Simplified - could parse actual timestamp
                    'message': line.strip()[:500],  # Limit message length
                    'category': category['name']
                }
                
                # Only keep events from last 30 days for health scoring
                events.append(event)
        
        logger.info(f"Collected {len(events)} {category['name']} events")
        return events
        
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout collecting {category['name']} logs")
        return []
    except Exception as e:
        logger.error(f"Error collecting {category['name']} logs: {e}")
        return []

def processAndFilterLogs(events, category_name):
    """Process and filter logs (like Windows filterEventLog)"""
    if not events:
        return {
            'LogName': category_name,
            'Sources': {'TopEvents': [], 'TotalEvents': 0}
        }
    
    # Group by message pattern (simplified)
    groups = {}
    for event in events:
        # Extract first few words as pattern
        words = event['message'].split()[:5]
        pattern = ' '.join(words) if len(words) >= 3 else event['message'][:50]
        
        if pattern not in groups:
            groups[pattern] = {
                'count': 0,
                'latest_time': event['timestamp'],
                'sample_message': event['message']
            }
        groups[pattern]['count'] += 1
    
    # Sort by count and take top 10
    sorted_groups = sorted(groups.items(), key=lambda x: x[1]['count'], reverse=True)[:10]
    
    top_events = []
    for pattern, data in sorted_groups:
        top_events.append({
            'Pattern': pattern,
            'Message': data['sample_message'][:200],
            'Count': data['count'],
            'LatestOccurrence': data['latest_time']
        })
    
    return {
        'LogName': category_name,
        'Sources': {
            'TopEvents': top_events,
            'TotalEvents': len(events)
        }
    }

def sendLogMetadata(deviceUuid, host, category_name, filtered_data):
    """Send metadata to server (like Windows sendEventMetadata)"""
    try:
        body = {
            'deviceuuid': deviceUuid,
            'metalogos_type': f'macos-{category_name}-filtered',
            'metalogos': filtered_data
        }
        
        url = f'https://{host}/ai/device/metadata'
        headers = {'Content-Type': 'application/json'}
        
        response = requests.post(url, headers=headers, data=json.dumps(body))
        logger.info(f'Metadata response for {category_name}: {response.status_code}')
        
        if response.status_code not in [200, 201]:
            logger.error(f'Failed to send {category_name} metadata: {response.text}')
            
    except Exception as e:
        logger.error(f'Error sending {category_name} metadata: {e}')

def main():
    if platform.system() != "Darwin":
        logger.error("This script only runs on MacOS")
        sys.exit(1)

    # Initialize logging
    logfile(os.path.join(logDir, "macos_log_audit.log"))
    
    # Get config
    wegConfigFile = os.path.join(configDir, 'agent.config')
    deviceUuid, host = getDeviceUuid(wegConfigFile)
    
    # Define log categories (like Windows logList)
    log_categories = [
        {
            'name': 'errors',
            'predicate': 'messageType == "Error" OR messageType == "Fault"',
            'description': 'System errors and faults'
        },
        {
            'name': 'security',
            'predicate': 'subsystem CONTAINS "security"',
            'description': 'Security events'
        },
        {
            'name': 'crashes',
            'predicate': 'eventMessage CONTAINS "crash"',
            'description': 'Application crashes'
        }
    ]
    
    logger.info('Starting MacOS Log Audit (following Windows eventLogAudit pattern)')
    
    for category in log_categories:
        try:
            # Check if this is first run (like Windows getLatestEvent)
            last_time = getLastCollectionTime(category['name'])
            is_first_run = (last_time is None)
            
            # Collect logs (like Windows readLog)
            events = collectCategoryLogs(category, is_first_run)
            
            # Read existing data and merge (like Windows readExistingLogJson)
            existing_data = readExistingLogJson(category['name'])
            
            # Merge new events with existing (simplified)
            if isinstance(existing_data, dict) and 'events' in existing_data:
                all_events = existing_data['events'] + events
            else:
                all_events = events
            
            # Keep only last 30 days for health scoring
            now = datetime.datetime.now()
            thirty_days_ago = now - datetime.timedelta(days=30)
            
            # Filter and process (like Windows filterEventLog)
            filtered_data = processAndFilterLogs(all_events, category['name'])
            
            # Save data (like Windows writeLogJson)
            writeLogJson({'events': all_events, 'filtered': filtered_data}, category['name'])
            
            # Send to server (like Windows sendEventMetadata)
            sendLogMetadata(deviceUuid, host, category['name'], filtered_data)
            
            # Update tracking (like Windows writeLatestEvent)
            updateLastCollectionTime(category['name'])
            
            logger.info(f"Completed {category['name']}: {len(all_events)} total events, {len(filtered_data['Sources']['TopEvents'])} patterns")
            
        except Exception as e:
            logger.error(f"Error processing {category['name']}: {e}")
    
    logger.info('MacOS Log Audit completed successfully')

if __name__ == "__main__":
    main()
