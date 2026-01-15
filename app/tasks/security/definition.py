# Filepath: app/tasks/security/definition.py
from typing import Dict, Any

ANALYSIS_CONFIG = {
    "type": "eventsFiltered-Security",
    "description": "Analyzes Windows security events to detect unauthorized access attempts, privilege escalations, and policy changes. Tracks user authentication patterns and identifies potential security breaches or suspicious activities.",
    "cost": 4,  # Wegcoins per analysis
    "schedule": 3600,  # Run every hour
    "input_type": "json",
    "output_format": "html",
    "allowed_tags": ['p', 'br', 'ul', 'li', 'strong', 'em']
}