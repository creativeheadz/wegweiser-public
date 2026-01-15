# Filepath: app/utilities/app_access_role_required.py
from functools import wraps
from flask import current_app, redirect, url_for, session
from sqlalchemy import text
from app.models import db
from .app_access_login_required import ROLE_HIERARCHY

def role_required(required_roles):
    def wrapper(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login_bp.login'))
            user_role = session.get('role')
            
            if isinstance(required_roles, str):
                required_roles_list = [required_roles]
            else:
                required_roles_list = required_roles
            
            if not any(ROLE_HIERARCHY.get(user_role, 0) >= ROLE_HIERARCHY.get(required_role, 0) for required_role in required_roles_list):
                return redirect(url_for('dashboard_bp.dashboard'))  # Redirect to dashboard if not authorized
            return f(*args, **kwargs)
        return decorated_function
    return wrapper