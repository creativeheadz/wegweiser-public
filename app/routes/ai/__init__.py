# Filepath: app/routes/ai/__init__.py
from flask import Blueprint
import os
import importlib

# Define the blueprint
ai_bp = Blueprint('ai_bp', __name__, url_prefix='/ai')

# Function to dynamically import all modules in this directory and subdirectories
def import_routes():
    current_dir = os.path.dirname(__file__)

    # First, import the core module
    if os.path.exists(os.path.join(current_dir, 'core.py')):
        importlib.import_module('.core', package=__package__)

    # Then import all other Python files in the current directory
    for filename in os.listdir(current_dir):
        if filename.endswith('.py') and filename not in ['__init__.py', 'core.py']:
            module_name = filename[:-3]
            importlib.import_module(f'.{module_name}', package=__package__)

    # Import modules from subdirectories
    for item in os.listdir(current_dir):
        subdir_path = os.path.join(current_dir, item)
        if os.path.isdir(subdir_path) and not item.startswith('__'):
            # Import the package itself
            package_name = f'.{item}'
            try:
                importlib.import_module(package_name, package=__package__)

                # Import all modules in the subdirectory
                for subfile in os.listdir(subdir_path):
                    if subfile.endswith('.py') and subfile != '__init__.py':
                        submodule_name = f'.{item}.{subfile[:-3]}'
                        importlib.import_module(submodule_name, package=__package__)
            except ImportError as e:
                print(f"Error importing {package_name}: {e}")

# Import all routes
import_routes()
