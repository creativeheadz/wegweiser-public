# Filepath: app/tasks/software/definition.py
from typing import Dict, Any

ANALYSIS_CONFIG = {
    "type": "msinfo-SystemSoftwareConfig",
    "description": "Analyzes Windows system software configuration including services, scheduled tasks, and system policies. Identifies misconfigurations and tracks changes in system software settings.",
    "cost": 2,
    "schedule": 43200,  # Run every 12 hours
    "input_type": "json",
    "output_format": "html",
    "allowed_tags": ['p', 'br', 'ul', 'li', 'strong', 'em']
}