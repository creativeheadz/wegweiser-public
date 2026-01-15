# Filepath: app/tasks/groups/definition.py
from typing import Dict, Any

ANALYSIS_CONFIG = {
    "type": "group-health-analysis",
    "description": "Analyzes group health by compiling device analyses, identifying top 10 worst performing devices, detecting patterns across devices in the same location, and providing programmatic summaries grouped by OS type and device count.",
    "cost": 3,  # Higher cost due to complex multi-device analysis
    "schedule": 7200,  # Run every 2 hours
    "input_type": "json",
    "output_format": "html",
    "allowed_tags": ['p', 'br', 'ul', 'li', 'strong', 'em', 'h4', 'h5', 'table', 'tr', 'td', 'th']
}
