# Filepath: app/utilities/app_get_current_user.py
from app.models import Accounts
from flask import session

def get_current_user():
    user_id = session.get('user_id')  # Assuming session stores the useruuid
    if user_id:
        return Accounts.query.get(user_id)  # Query by useruuid
    return None
