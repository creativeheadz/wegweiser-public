# Filepath: app/routes/tenant/accounts.py
# Filepath: app/routes/accounts.py
from flask import Blueprint, request, jsonify, session
from app.utilities.app_access_login_required import login_required
from app.models import db, Accounts
import logging
from app.utilities.app_logging_helper import log_with_route
from flask_wtf.csrf import CSRFProtect
from app import csrf

# Create blueprint with a url_prefix
account_bp = Blueprint('account_bp', __name__, url_prefix='/account')

@account_bp.route('/set_theme', methods=['POST'])
@login_required
@csrf.exempt  # Only use this if you intentionally want to bypass CSRF for this route
def set_theme():
    if not request.is_json:
        log_with_route(logging.WARNING, 'Invalid content type for theme update request.')
        return jsonify({'error': 'Request must be JSON'}), 400

    data = request.get_json()
    new_theme = data.get('theme')
    user_id = session.get('user_id')

    if not user_id:
        log_with_route(logging.WARNING, 'User ID not found in session.')
        return jsonify({'error': 'User not logged in'}), 401

    if not new_theme:
        log_with_route(logging.WARNING, 'No theme provided in the request.')
        return jsonify({'error': 'No theme provided'}), 400

    log_with_route(logging.INFO, f'Received request to set theme to {new_theme} for user ID {user_id}.')

    user = Accounts.query.get(user_id)
    if not user:
        log_with_route(logging.ERROR, f'User with ID {user_id} not found.')
        return jsonify({'error': 'User not found'}), 404

    try:
        user.theme = new_theme
        db.session.commit()
        session['theme'] = new_theme  # Update session with new theme

        log_with_route(logging.INFO, f'Theme updated to {new_theme} for user ID {user_id}.')
        return jsonify({'message': 'Theme updated successfully'})
    except Exception as e:
        log_with_route(logging.ERROR, f'Error updating theme for user ID {user_id}: {e}', exc_info=True)
        return jsonify({'error': 'Failed to update theme'}), 500
