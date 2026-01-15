# Filepath: app/routes/organisations/__init__.py
# __init__.py
from flask import Blueprint
organisations_bp = Blueprint('organisations_bp', __name__)

# This ensures all routes are registered before the blueprint is used
from . import organisations, organisations_add, organisations_delete