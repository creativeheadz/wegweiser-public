# Filepath: app/routes/index.py
from flask import Blueprint, render_template, send_from_directory, redirect, url_for, session, request, jsonify
import logging
import os
from app.utilities.app_logging_helper import log_with_route
from app.utilities.app_get_client_ip import get_client_ip

index_bp = Blueprint('index', __name__)

@index_bp.route('/')
def index():
    client_ip = get_client_ip(request)  # Pass the request object

    if 'user_id' in session:
        log_with_route(logging.INFO, f"Redirecting logged-in user from {client_ip} to dashboard")
        return redirect(url_for('dashboard_bp.dashboard'))
    else:
        log_with_route(logging.INFO, f"Rendering index page for client {client_ip} without active session")
        return render_template('index.html')

@index_bp.route('/.well-known/security.txt')
def security_txt():
    return send_from_directory('static', '.well-known/security.txt')

@index_bp.route('/robots.txt')
def robots_txt():
    """Serve robots.txt file"""
    log_with_route(logging.INFO, "Serving robots.txt")
    return send_from_directory('static', 'robots.txt')

@index_bp.route('/favicon.ico')
def favicon():
    """Serve favicon.ico file"""
    log_with_route(logging.INFO, "Serving favicon.ico")
    return send_from_directory('static/images', 'favicon-32x32.png', mimetype='image/vnd.microsoft.icon')

@index_bp.route('/privacy')
def privacy_policy():
    """Serve privacy policy page - publicly accessible"""
    client_ip = get_client_ip(request)
    log_with_route(logging.INFO, f"Serving privacy policy page for client {client_ip}")
    return render_template('legal/privacy.html')

@index_bp.route('/terms')
def terms_of_service():
    """Serve terms of service page - publicly accessible"""
    client_ip = get_client_ip(request)
    log_with_route(logging.INFO, f"Serving terms of service page for client {client_ip}")
    return render_template('legal/terms.html')

@index_bp.route('/security')
def security_policy():
    """Serve security policy page - publicly accessible"""
    client_ip = get_client_ip(request)
    log_with_route(logging.INFO, f"Serving security policy page for client {client_ip}")
    return render_template('legal/security.html')

@index_bp.route('/health')
def health_check():
    """
    Health check endpoint for monitoring and internal services.
    Returns 200 OK with status information.

    IMPORTANT: This endpoint is publicly accessible and does NOT trigger IP blocking.
    Used by:
    - Internal monitoring scripts
    - Load balancers
    - Health check systems
    - Development/debugging
    """
    return jsonify({
        'status': 'healthy',
        'service': 'wegweiser'
    }), 200

