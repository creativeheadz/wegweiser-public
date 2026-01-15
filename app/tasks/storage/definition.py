# Filepath: app/tasks/storage/definition.py
from typing import Dict, Any

ANALYSIS_CONFIG = {
    "type": "msinfo-StorageInfo",
    "description": "Monitors Windows storage systems for space usage, disk health, and performance issues. Tracks disk space trends, identifies fragmentation problems, and alerts on potential drive failures.",
    "cost": 2,
    "schedule": 43200,  # Run every 12 hours
    "input_type": "json",
    "output_format": "html",
    "allowed_tags": ['p', 'br', 'ul', 'li', 'strong', 'em']
}