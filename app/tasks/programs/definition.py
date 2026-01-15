# Filepath: app/tasks/programs/definition.py
from typing import Dict, Any

ANALYSIS_CONFIG = {
    "type": "msinfo-InstalledPrograms",
    "description": "Inventories installed Windows software, tracking versions and identifying outdated or potentially problematic applications. Monitors software changes and flags unauthorized or suspicious installations.",
    "cost": 2,  # Higher cost due to complexity
    "schedule": 43200,  # Run every 12 hours
    "input_type": "json",
    "output_format": "html",
    "allowed_tags": ['p', 'br', 'ul', 'li', 'strong', 'em']
}