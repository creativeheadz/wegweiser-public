# Filepath: app/tasks/crashes/definition.py
from typing import Dict, Any

ANALYSIS_CONFIG = {
    "type": "msinfo-RecentAppCrashes",
    "description": "Tracks Windows application crashes and stability issues. Analyzes crash patterns, identifies common failure points, and consolidates crash reports to highlight problematic applications.",
    "cost": 3,  # Higher cost due to preprocessing
    "schedule": 1800,  # Run every 30 minutes
    "input_type": "json",
    "output_format": "html",
    "allowed_tags": ['p', 'br', 'ul', 'li', 'strong', 'em']
}