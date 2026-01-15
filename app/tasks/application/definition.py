# Filepath: app/tasks/application/definition.py
from typing import Dict, Any

# Filepath: app/tasks/application/definition.py
ANALYSIS_CONFIG = {
    "type": "eventsFiltered-Application",  # Changed to match exact DB value
    "description": "Reviews Windows application event logs to detect software issues, crashes, and performance problems. Consolidates repeated errors and identifies patterns in application behavior that may indicate stability issues.",
    "cost": 1,
    "schedule": 1800,
    "input_type": "json",
    "output_format": "html",
    "allowed_tags": ['p', 'br', 'ul', 'li', 'strong', 'em']
}