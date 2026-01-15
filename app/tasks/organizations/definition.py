# Filepath: app/tasks/organizations/definition.py
from typing import Dict, Any

ANALYSIS_CONFIG = {
    "type": "organization-health-analysis",
    "description": "Analyzes organization health by compiling group analyses, identifying top 10 worst performing groups, detecting patterns across groups, and providing programmatic summaries grouped by group type and device distribution.",
    "cost": 5,  # Higher cost due to complex multi-group analysis
    "schedule": 10800,  # Run every 3 hours
    "input_type": "json",
    "output_format": "html",
    "allowed_tags": ['p', 'br', 'ul', 'li', 'strong', 'em', 'h4', 'h5', 'table', 'tr', 'td', 'th']
}
