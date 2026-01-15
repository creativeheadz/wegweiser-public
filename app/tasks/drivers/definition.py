# Filepath: app/tasks/drivers/definition.py
from typing import Dict, Any

ANALYSIS_CONFIG = {
    "type": "windrivers",
    "description": "Evaluates Windows driver health and compatibility. Identifies outdated, unsigned, or problematic drivers while monitoring driver-related system events and performance impacts.",
    "cost": 3,  # Higher cost for complex analysis
    "schedule": 14400,  # Run every 4 hours
    "input_type": "json",
    "output_format": "html",
    "allowed_tags": ['p', 'br', 'ul', 'li', 'strong', 'em']
}