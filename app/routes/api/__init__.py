# Filepath: app/routes/api/__init__.py
from flask import Blueprint

# Import API blueprints
try:
    from .tours import tours_api_bp
except ImportError:
    pass

try:
    from .analysis_config import analysis_config_bp
except ImportError:
    pass
