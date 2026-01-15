# Filepath: app/utilities/log_utils.py
# log_utils.py
import os
import json
import logging
from datetime import datetime, timedelta
import time
from collections import defaultdict
from app.utilities.loggings import logger

def load_logs_from_file(filepath):
    """Read and load logs from a single JSON file."""
    logger.info(f"Reading {filepath}...")
    try:
        start_time = time.time()
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            logs = json.load(f)
        logger.info(f"Loaded logs from {filepath} in {time.time() - start_time:.2f} seconds.")
        
        if isinstance(logs, dict):
            log_entries = list(logs.values())
        elif isinstance(logs, list):
            log_entries = logs
        else:
            logger.error(f"Unexpected log structure in {filepath}")
            return []
        
        if log_entries:
            logger.info(f"Sample log entry structure: {list(log_entries[0].keys())}")
            logger.info(f"Sample timegenerated value: {log_entries[0].get('timegenerated', 'Not found')}")
        else:
            logger.warning("No log entries found in the file.")
        
        return log_entries
    except json.JSONDecodeError as e:
        logger.error(f"Failed to read {filepath}: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error reading {filepath}: {e}")
        return []

def load_logs_for_multiple_machines(directory, days=3):
    """Load logs for multiple machines from the specified directory."""
    logs_by_machine = defaultdict(list)
    for root, _, files in os.walk(directory):
        for filename in files:
            if filename.endswith('.json'):
                filepath = os.path.join(root, filename)
                machine_id = os.path.basename(root)  # Assuming the directory name is the machine ID
                logs = load_logs_from_file(filepath)
                filtered_logs = filter_recent_logs(logs, days)
                logs_by_machine[machine_id].extend(filtered_logs)
    
    logger.info(f"Loaded logs for {len(logs_by_machine)} machines")
    return logs_by_machine

def filter_recent_logs(logs, days):
    """Filter logs to include only those from the specified number of recent days."""
    if not logs:
        return []
    dates = []
    for log in logs:
        if isinstance(log, dict) and 'timegenerated' in log:
            try:
                date = datetime.strptime(log['timegenerated'], "%Y-%m-%d-%H:%M:%S")
                dates.append(date)
            except ValueError:
                logger.warning(f"Invalid date format in log: {log.get('timegenerated', 'No timegenerated field')}")
    if not dates:
        logger.error("No valid dates found in logs")
        return []
    most_recent_date = max(dates)
    cutoff_date = most_recent_date - timedelta(days=days)
    recent_logs = [
        log for log in logs
        if isinstance(log, dict) and 'timegenerated' in log and 
        datetime.strptime(log['timegenerated'], "%Y-%m-%d-%H:%M:%S") >= cutoff_date
    ]
    logger.info(f"Filtered {len(recent_logs)} logs from the last {days} days")
    return recent_logs

def group_logs_by_date(logs):
    """Group logs by date."""
    grouped_logs = defaultdict(list)
    for log in logs:
        if 'timegenerated' in log:
            try:
                date_obj = datetime.strptime(log['timegenerated'], "%Y-%m-%d-%H:%M:%S")
                date_str = date_obj.strftime('%Y-%m-%d')
                grouped_logs[date_str].append(log)
            except ValueError as e:
                logger.warning(f"Invalid date format in log: {log.get('timegenerated')}. Error: {e}")
    
    logger.info(f"Grouped logs into {len(grouped_logs)} days")
    return grouped_logs