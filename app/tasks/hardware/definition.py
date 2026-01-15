# Filepath: app/tasks/hardware/definition.py
from typing import Dict, Any

ANALYSIS_CONFIG = {
    "type": "msinfo-SystemHardwareConfig",
    "description": "Examines Windows hardware configuration and health status. Monitors hardware changes, driver compatibility, and component performance while tracking system resource utilization patterns.",
    "cost": 2,
    "schedule": 3600,  # Run every hour
    "input_type": "json",
    "output_format": "html",
    "allowed_tags": ['p', 'br', 'ul', 'li', 'strong', 'em']
}