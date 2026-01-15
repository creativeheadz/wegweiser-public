# Filepath: app/tasks/loki_scan/definition.py
from typing import Dict, Any

ANALYSIS_CONFIG = {
    "type": "loki-scan",
    "description": (
        "Analyzes Loki IOC scan results to assess malware and indicator of compromise risk, "
        "highlight suspicious findings, and provide remediation guidance."
    ),
    "cost": 5,  # Wegcoins per analysis
    "schedule": 0,  # On-demand; no automatic schedule
    "input_type": "json",
    "output_format": "html",
    "allowed_tags": ['p', 'br', 'ul', 'li', 'strong', 'em', 'h4', 'h5'],
    "premium_feature": True,
}

