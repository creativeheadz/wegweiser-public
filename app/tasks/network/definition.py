# Filepath: app/tasks/network/definition.py
from typing import Dict, Any

ANALYSIS_CONFIG = {
    "type": "msinfo-NetworkConfig",
    "description": "Evaluates Windows network configuration and connectivity issues. Analyzes network adapter settings, DNS configuration, and network service status while tracking changes in network topology.",
    "cost": 2,
    "schedule": 21600,  # Run every 6 hours
    "input_type": "json",
    "output_format": "html",
    "allowed_tags": ['p', 'br', 'ul', 'li', 'strong', 'em']
}