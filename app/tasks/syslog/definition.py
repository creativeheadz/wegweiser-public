# Filepath: app/tasks/syslog/definition.py
from typing import Dict, Any

ANALYSIS_CONFIG = {
    "type": "syslogFiltered",
    "description": "Examines Linux system logs for operational issues, security events, and system health indicators. Consolidates related events and identifies patterns that may indicate system problems or security concerns.",
    "cost": 2,
    "schedule": 3600,  # Run every hour
    "input_type": "json",
    "output_format": "html",
    "allowed_tags": ['p', 'br', 'ul', 'li', 'strong', 'em']
}