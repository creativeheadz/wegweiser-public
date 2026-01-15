# Filepath: app/routes/osquery/__init__.py
from flask import Blueprint
import os
import importlib

# Define the blueprint
osquery_bp = Blueprint('osquery_bp', __name__, url_prefix='/osquery')

# Function to import routes dynamically
def import_routes():
    current_dir = os.path.dirname(__file__)
    for filename in os.listdir(current_dir):
        if filename.endswith('.py') and filename != '__init__.py':
            module_name = filename[:-3]
            importlib.import_module(f'.{module_name}', package=__package__)

# Dynamically import all route files
import_routes()
