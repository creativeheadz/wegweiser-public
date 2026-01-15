# Filepath: app/utilities/app_utilities_check_api_key.py
import geoip2.database
from functools import wraps
from flask import current_app, redirect, url_for, session
from sqlalchemy import text
from app.models import db
from flask import request, current_app


def check_api_key():
    api_key = request.headers.get('x-api-key')
    if api_key == current_app.config['API_KEY']:
        return True
    else:
        return False
