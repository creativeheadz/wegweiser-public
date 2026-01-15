# Filepath: app/tasks/tenant/definition.py
from typing import Dict, Any

# Primary config for the definition loader - using recommendations as the main one
ANALYSIS_CONFIG = {
    "type": "tenant-ai-recommendations",
    "description": "Generates AI-powered tool recommendations based on tenant profile data, analyzing missing tool categories and providing strategic recommendations for MSP operations enhancement.",
    "cost": 5,  # Higher cost due to complex AI analysis
    "schedule": 604800,  # Run weekly 
    "input_type": "json",
    "output_format": "html",
    "allowed_tags": ['p', 'br', 'ul', 'li', 'strong', 'em', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']
}

# Note: tenant-ai-suggestions has its own definition file in app/tasks/tenant_suggestions/definition.py
