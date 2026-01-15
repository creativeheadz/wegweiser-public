# Filepath: app/routes/settings/__init__.py
from flask import Blueprint

settings_bp = Blueprint('settings_bp', __name__, url_prefix='/settings')  # Fixed __name__

# Import all routes after blueprint creation
from . import settings