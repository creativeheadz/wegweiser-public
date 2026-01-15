# Filepath: app/tasks/macos_logs/definition.py
from typing import Dict, Any

ANALYSIS_CONFIG = {
    "type": "macos-log-health",
    "description": "Analyzes macOS system logs for health patterns. Processes error logs, security events, and crash reports to identify system stability and security issues.",
    "cost": 8,
    "schedule": 604800,  # Run weekly (7 days)
    "input_type": "json",
    "output_format": "html",
    "allowed_tags": ['p', 'br', 'ul', 'li', 'strong', 'em', 'span', 'code'],
    "prerequisites": ["macos-errors-filtered", "macos-security-filtered", "macos-crashes-filtered"],
    "data_driven": True  # Only run when new log data is available
}
