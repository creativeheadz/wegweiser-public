# Filepath: app/tasks/auth/definition.py
from typing import Dict, Any

ANALYSIS_CONFIG = {
    "type": "authFiltered",
    "description": "Monitors Linux authentication events including login attempts, sudo usage, and SSH access. Analyzes patterns of authentication failures, tracks unusual login times or locations, and identifies potential brute force attempts.",
    "cost": 1,  # Wegcoins per analysis
    "schedule": 3600,  # Run every hour
    "input_type": "json",
    "output_format": "html",
    "allowed_tags": ['p', 'br', 'ul', 'li', 'strong', 'em']
}