# Filepath: app/tasks/system/definition.py
from typing import Dict, Any

ANALYSIS_CONFIG = {
    "type": "eventsFiltered-System",
    "description": "Monitors Windows system events for hardware issues, driver problems, and system changes. Evaluates boot performance, system stability, and resource utilization while tracking critical system state changes.",
    "cost": 1,  # Wegcoins per analysis
    "schedule": 3600,  # Run every hour
    "input_type": "json",
    "output_format": "html",
    "allowed_tags": ['p', 'br', 'ul', 'li', 'strong', 'em']
}