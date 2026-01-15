# Filepath: app/tasks/macos_os/definition.py
from typing import Dict, Any

ANALYSIS_CONFIG = {
    "type": "macos-os-version",
    "description": "Analyzes macOS version against current Apple releases. Evaluates security update status, feature currency, and compatibility to determine OS health score.",
    "cost": 2,
    "schedule": 86400,  # Run daily to detect OS changes
    "input_type": "json",
    "output_format": "html",
    "allowed_tags": ['p', 'br', 'ul', 'li', 'strong', 'em', 'span'],
    "prerequisites": ["devicestatus"],
    "change_detection": True  # Only run when OS version changes
}
