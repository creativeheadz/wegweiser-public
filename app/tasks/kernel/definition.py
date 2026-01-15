# Filepath: app/tasks/kernel/definition.py
from typing import Dict, Any

ANALYSIS_CONFIG = {
    "type": "kernFiltered",
    "description": "Analyzes Linux kernel logs to detect hardware issues, driver problems, and system resource constraints. Identifies kernel panics, hardware failures, and resource exhaustion events.",
    "cost": 2,  # Higher cost for complex analysis
    "schedule": 10800,  # Run every 3 hours
    "input_type": "json",
    "output_format": "html",
    "allowed_tags": ['p', 'br', 'ul', 'li', 'strong', 'em']
}