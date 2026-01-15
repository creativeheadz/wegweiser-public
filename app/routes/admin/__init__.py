# Filepath: app/routes/admin/__init__.py
from flask import Blueprint

# Import the admin blueprint from admin.py
from .admin import admin_bp

# Import other admin blueprints if they exist
try:
    from .admin_snippets import admin_snippets_bp
except ImportError:
    pass

try:
    from .nats_demo import nats_demo_bp
except ImportError:
    pass

try:
    from .agent_updates import agent_updates_bp
except ImportError:
    pass

try:
    from .system_health import system_health_bp
except ImportError:
    pass
