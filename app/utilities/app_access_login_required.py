# Filepath: app/utilities/app_access_login_required.py
# app/utils.py
import geoip2.database
from functools import wraps
from flask import current_app, redirect, url_for, session
from sqlalchemy import text
from app.models import db

# Define the role hierarchy
ROLE_HIERARCHY = {
    'user': 1,
    'master': 2,
    'admin': 3
}

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login_bp.login'))
        return f(*args, **kwargs)
    return decorated_function