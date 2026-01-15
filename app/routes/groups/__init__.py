# Filepath: app/routes/groups/__init__.py
# __init__.py
from flask import Blueprint
groups_bp = Blueprint('groups_bp', __name__)

# This ensures all routes are registered before the blueprint is used
from . import groups, groups_add, groups_delete