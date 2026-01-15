#!/usr/bin/env python3
"""
MacOS Metadata Collection Script - FAST VERSION
Optimized for performance and reliability
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

# Global variables for directories and config
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

def get_system_logs_fast():
    """Fast log collection - only critical events from last 24 hours"""
    logger.info("Collecting critical system events from last 24 hours...")
    
    summary_data = {
        'collection_period': '24 hours',
        'categories': {},
        'total_events_processed': 0,
        'collection_timestamp': datetime.datetime.now().isoformat()
    }
    
    # Only collect the most critical events
    categories = [
        {
            'name': 'errors',
            'predicate': 'messageType == "Error"',
            'description': 'System errors'
        },
        {
            'name': 'crashes', 
            'predicate': 'eventMessage CONTAINS "crash"',
            'description': 'Application crashes'
        }
    ]
    
    for category in categories:
        logger.info(f"Processing {category['name']} logs...")
        
        cmd = [
            "log", "show",
            "--last", "24h",  # Only 24 hours
            "--predicate", category['predicate'],
            "--style", "compact"  # Faster than JSON
        ]
        
        try:
            # Short timeout to prevent hanging
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                logger.warning(f"log show for {category['name']} failed: {result.stderr}")
                summary_data['categories'][category['name']] = {'error': 'command_failed'}
                continue
            
            # Simple processing
            lines = result.stdout.strip().split('\n')
            events = [line for line in lines if line.strip()]
            
            # Basic grouping by first word (usually process name)
            groups = {}
            for event in events:
                if len(event) > 10:
                    # Extract first meaningful word as process
                    words = event.split()
                    process = 'unknown'
                    for word in words:
                        if len(word) > 2 and not word.startswith('202'):  # Skip timestamps
                            process = word.split('[')[0]  # Remove PID
                            break
                    
                    if process not in groups:
                        groups[process] = {
                            'count': 0,
                            'sample': event[:200]
                        }
                    groups[process]['count'] += 1
            
            # Top 10 processes
            top_groups = sorted(groups.items(), key=lambda x: x[1]['count'], reverse=True)[:10]
            
            summary_data['categories'][category['name']] = {
                'description': category['description'],
                'total_events': len(events),
                'unique_processes': len(groups),
                'top_processes': [
                    {
                        'process': proc,
                        'count': data['count'],
                        'sample': data['sample']
                    }
                    for proc, data in top_groups
                ]
            }
            
            summary_data['total_events_processed'] += len(events)
            logger.info(f"Processed {len(events)} {category['name']} events into {len(groups)} process groups")
            
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout collecting {category['name']} logs")
            summary_data['categories'][category['name']] = {'error': 'timeout'}
        except Exception as e:
            logger.error(f"Error collecting {category['name']} logs: {e}")
            summary_data['categories'][category['name']] = {'error': str(e)}
    
    return summary_data

def get_system_info():
    """Get basic system information"""
    try:
        cmd = ["system_profiler", "SPHardwareDataType", "-json"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        data = json.loads(result.stdout)
        return data.get('SPHardwareDataType', [{}])[0]
    except Exception as e:
        logger.error(f"Failed to get system info: {e}")
        return {}

def collect_macos_metadata():
    """Main collection function - FAST VERSION"""
    if platform.system() != "Darwin":
        logger.error("This script only runs on MacOS")
        return None
        
    try:
        logger.info("Starting FAST MacOS metadata collection...")
        
        # Quick system info
        system_info = get_system_info()
        
        # Fast log collection
        system_logs_summary = get_system_logs_fast()
        
        metadata = {
            "timestamp": datetime.datetime.now().isoformat(),
            "data_type": "macos_metadata_fast",
            "hostname": platform.node(),
            "os_version": platform.platform(),
            "system_info": system_info,
            "system_logs_summary": system_logs_summary,
            "summary_stats": {
                "total_events_processed": system_logs_summary.get('total_events_processed', 0),
                "categories_analyzed": len(system_logs_summary.get('categories', {})),
                "collection_period": system_logs_summary.get('collection_period', '24 hours')
            }
        }
        
        logger.info(f"FAST collection completed - processed {metadata['summary_stats']['total_events_processed']} events")
        return metadata
        
    except Exception as e:
        logger.error(f"Error in fast collection: {e}")
        return None

def send_metadata_to_server(deviceUuid, host, metadata):
    """Send metadata using the correct API endpoint"""
    try:
        body = {
            'deviceuuid': deviceUuid,
            'metalogos_type': 'macos-log-summary-fast',
            'metalogos': metadata
        }
        
        url = f'https://{host}/ai/device/metadata'
        headers = {'Content-Type': 'application/json'}
        logger.info(f'Sending metadata to: {url}')
        
        response = requests.post(url, headers=headers, data=json.dumps(body))
        logger.info(f'Response: {response.status_code}')
        
        if response.status_code in [200, 201]:
            logger.info("Successfully sent metadata")
            return True
        else:
            logger.error(f"Failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error sending metadata: {e}")
        return False

def main():
    if platform.system() != "Darwin":
        logger.error("This script only runs on MacOS")
        sys.exit(1)

    # Initialize logging
    logfile(os.path.join(logDir, "macos_metadata_fast.log"))
    
    # Get config
    wegConfigFile = os.path.join(configDir, 'agent.config')
    deviceUuid, host = getDeviceUuid(wegConfigFile)
    
    try:
        # Fast collection
        metadata = collect_macos_metadata()
        if metadata is None:
            raise Exception("Failed to collect metadata")
            
        # Save for debugging
        output_file = os.path.join(filesDir, "macos_metadata_fast.json")
        with open(output_file, "w") as f:
            json.dump(metadata, f, indent=2)
        logger.info(f"Saved to {output_file}")
        
        # Send to server
        if send_metadata_to_server(deviceUuid, host, metadata):
            logger.info("SUCCESS: Fast MacOS metadata collection completed")
        else:
            logger.error("FAILED: Could not upload metadata")
            
    except Exception as e:
        logger.error(f"FAILED: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
