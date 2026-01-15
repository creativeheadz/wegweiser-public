# Filepath: app/tasks/tenant_suggestions/definition.py
from typing import Dict, Any

ANALYSIS_CONFIG = {
    "type": "tenant-ai-suggestions",
    "description": "Provides comprehensive strategic analysis based on overall tenant health metrics, device distribution patterns, and operational insights. Delivers actionable recommendations for improving infrastructure performance and business outcomes.",
    "cost": 7,  # Higher cost due to comprehensive strategic analysis
    "schedule": 86400,  # Run daily (24 hours)
    "input_type": "json",
    "output_format": "html",
    "allowed_tags": ['p', 'br', 'ul', 'li', 'strong', 'em', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']
}
