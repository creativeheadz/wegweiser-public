# Filepath: app/tasks/crashes/utils.py
import re
import json
import logging
from collections import Counter
from typing import List, Dict, Any, Tuple

def extract_application_name(metalogos: Dict[str, Any]) -> List[str]:
    """Extract application names from crash logs"""
    app_names = []
    if isinstance(metalogos, list):
        for entry in metalogos:
            if isinstance(entry, dict) and 'Message' in entry:
                match = re.search(r'Faulting application name: ([\w.]+)', entry['Message'])
                if match:
                    app_names.append(match.group(1))
    elif isinstance(metalogos, dict):
        for key, value in metalogos.items():
            if isinstance(value, str):
                match = re.search(r'Faulting application name: ([\w.]+)', value)
                if match:
                    app_names.append(match.group(1))
    return app_names

def aggregate_crash_logs(logs: List[Dict[str, Any]]) -> List[Tuple[str, int]]:
    """Aggregate crash logs and count occurrences"""
    crash_counter = Counter()
    for log in logs:
        if isinstance(log['metalogos'], str):
            try:
                metalogos = json.loads(log['metalogos'])
            except json.JSONDecodeError:
                logging.error(f"Failed to parse metalogos JSON")
                continue
        else:
            metalogos = log['metalogos']
        
        app_names = extract_application_name(metalogos)
        for app_name in app_names:
            crash_counter[app_name] += 1
    return crash_counter.most_common(25)