# Filepath: app/routes/nats/__init__.py
"""
NATS Integration Routes

New routes for NATS-based agent communication, running parallel to existing
Node-RED routes to enable gradual migration without disruption.
"""

from flask import Blueprint

# Create the NATS blueprint
nats_bp = Blueprint('nats', __name__, url_prefix='/api/nats')

# Import route modules
from . import device_api
from . import agent_management
from . import monitoring
