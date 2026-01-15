# Filepath: app/tasks/lynis_audit/definition.py
from typing import Dict, Any

ANALYSIS_CONFIG = {
    "type": "lynis-audit",
    "description": "Analyzes Lynis security audit reports to assess system hardening, identify security vulnerabilities, and provide compliance recommendations. Evaluates against ISO27001, PCI-DSS, HIPAA, and CIS benchmarks.",
    "cost": 10,  # Wegcoins per analysis (premium feature)
    "schedule": 604800,  # Run once per week (604800 seconds)
    "input_type": "json",
    "output_format": "html",
    "allowed_tags": ['p', 'br', 'ul', 'li', 'strong', 'em', 'h4', 'h5'],
    "premium_feature": True,  # Requires WegCoins subscription
}
