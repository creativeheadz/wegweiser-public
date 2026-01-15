# Filepath: app/utilities/error_handler.py

from flask import request
from app.utilities.ip_blocker import IPBlocker
from app.utilities.app_logging_helper import log_with_route
import logging

def handle_404_error(e):
    """Handle 404 errors and potentially block IPs"""
    # Get client IP
    ip = request.headers.get('X-Real-IP') or request.remote_addr
    
    # Initialize IP blocker
    blocker = IPBlocker()
    
    # Handle the failed request
    result = blocker.handle_failed_request(ip, request.url)
    
    # Return standard 404 response
    return {"error": "Not Found"}, 404