# Filepath: app/tasks/macos_hardware/definition.py
from typing import Dict, Any

ANALYSIS_CONFIG = {
    "type": "macos-hardware-eol",
    "description": "Analyzes macOS hardware against Apple's End-of-Life policy. Evaluates device age, support status, and remaining lifespan to determine hardware health score.",
    "cost": 2,
    "schedule": 0,  # Run once per device (one-time analysis)
    "input_type": "json",
    "output_format": "html",
    "allowed_tags": ['p', 'br', 'ul', 'li', 'strong', 'em', 'span'],
    "prerequisites": ["devicestatus", "devicebios"],
    "run_once": True  # Custom flag to indicate this should only run once per device
}
