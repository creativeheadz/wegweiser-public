# Filepath: app/tasks/journal/definition.py
from typing import Dict, Any

ANALYSIS_CONFIG = {
    "type": "journalFiltered",
    "description": "Examines Linux systemd journal logs for system health and service issues. Identifies service failures, resource constraints, and system errors while tracking boot/shutdown cycles and service dependencies.",
    "cost": 1,  # Wegcoins per analysis
    "schedule": 3600,  # Run every hour
    "input_type": "json",
    "output_format": "html",
    "allowed_tags": ['p', 'br', 'ul', 'li', 'strong', 'em']
}