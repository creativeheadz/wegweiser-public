# Filepath: app/utilities/app_logging_helper.py
import os
import logging
from flask import current_app, request, has_request_context, has_app_context, g
from app.utilities.app_get_client_ip import get_client_ip
import time
import json
import redis
import psycopg2
from psycopg2.extras import Json
from datetime import datetime, timezone
import uuid
import threading

# Global lock for thread-safe configuration updates
_config_lock = threading.RLock()

# Default logging configuration
DEFAULT_LOGGING_CONFIG = {
    "levels": {
        "INFO": False,
        "DEBUG": False,
        "ERROR": True,
        "WARNING": True
    },
    "last_updated": None,
    "updated_by": "system"
}

# Global configuration storage
_logging_config = DEFAULT_LOGGING_CONFIG.copy()

def get_config_file_path():
    """Get the path to the logging configuration file."""
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config', 'logging_config.json')

def load_logging_config():
    """Load logging configuration from file."""
    global _logging_config
    config_path = get_config_file_path()

    try:
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                file_config = json.load(f)
                # Validate and merge with defaults
                if 'levels' in file_config and isinstance(file_config['levels'], dict):
                    with _config_lock:
                        _logging_config.update(file_config)
                        # Ensure all required levels exist
                        for level in DEFAULT_LOGGING_CONFIG['levels']:
                            if level not in _logging_config['levels']:
                                _logging_config['levels'][level] = DEFAULT_LOGGING_CONFIG['levels'][level]
                else:
                    raise ValueError("Invalid configuration format")
        else:
            # Create default config file
            save_logging_config(_logging_config)
    except Exception as e:
        print(f"Error loading logging config: {e}. Using defaults.")
        with _config_lock:
            _logging_config = DEFAULT_LOGGING_CONFIG.copy()

def save_logging_config(config):
    """Save logging configuration to file."""
    config_path = get_config_file_path()

    try:
        # Ensure config directory exists
        os.makedirs(os.path.dirname(config_path), exist_ok=True)

        # Add timestamp
        config['last_updated'] = datetime.now(timezone.utc).isoformat()

        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving logging config: {e}")
        return False

def get_logging_levels_enabled():
    """Get current logging levels as a dictionary compatible with the original format."""
    with _config_lock:
        return {
            logging.INFO: _logging_config['levels'].get('INFO', False),
            logging.DEBUG: _logging_config['levels'].get('DEBUG', False),
            logging.ERROR: _logging_config['levels'].get('ERROR', True),
            logging.WARNING: _logging_config['levels'].get('WARNING', True),
        }

def update_logging_config(new_levels, updated_by="unknown"):
    """Update logging configuration and save to file."""
    global _logging_config

    with _config_lock:
        _logging_config['levels'].update(new_levels)
        _logging_config['updated_by'] = updated_by

        if save_logging_config(_logging_config):
            return True
        return False

def reload_logging_config():
    """Reload logging configuration from file."""
    load_logging_config()
    return _logging_config.copy()

# Initialize configuration on module load
load_logging_config()

class RemoteLogger:
    _instance = None
    _redis_client = None
    _pg_conn = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._initialize()
        return cls._instance

    @classmethod
    def _initialize(cls):
        # Default to disabled unless explicitly enabled in config
        if not has_app_context() or not current_app.config.get('REMOTE_LOGGING_ENABLED', False):
            cls._redis_client = None
            return

        try:
            # Get configuration from Flask app if available
            host = current_app.config.get('REMOTE_LOGGING_SERVER', '10.0.0.5')
            port = current_app.config.get('REMOTE_LOGGING_PORT', 6379)
            password = current_app.config.get('REMOTE_LOGGING_PASSWORD', '')
            timeout = current_app.config.get('REMOTE_LOGGING_TIMEOUT', 2)

            # Initialize Redis connection with provided config
            cls._redis_client = redis.Redis(
                host=host,
                port=port,
                password=password,
                socket_timeout=timeout,
                socket_connect_timeout=timeout,
                retry_on_timeout=True
            )

            # Test Redis connection
            cls._redis_client.ping()
            if has_app_context():
                current_app.logger.info(f"Remote logging initialized successfully to {host}:{port}")

        except Exception as e:
            if has_app_context():
                current_app.logger.error(f"Failed to initialize Redis connection: {str(e)}")
            cls._redis_client = None

    def log(self, level: int, message: str, metadata: dict, source_type: str = "Application"):
        # Skip if Redis client isn't available or remote logging is disabled
        if not self._redis_client:
            return False

        # Check if we should fall back to local logging only
        if has_app_context() and not current_app.config.get('REMOTE_LOGGING_ENABLED', False):
            return False

        try:
            # Get tenant_uuid from Flask g if available
            tenant_uuid = str(g.tenant_uuid) if hasattr(g, 'tenant_uuid') else None

            log_entry = {
                'tenant_uuid': tenant_uuid,
                'level': logging.getLevelName(level),
                'source_type': source_type,
                'message': message,
                'metadata': metadata,
                'created_at': datetime.now(timezone.utc).isoformat()
            }

            # Queue in Redis for batch processing
            self._redis_client.lpush('wegweiser_logs', json.dumps(log_entry))
            return True
        except Exception as e:
            if has_app_context():
                current_app.logger.error(f"Failed to send log to remote server: {str(e)}")
            return False

class LogLevelFilter(logging.Filter):
    """Filter that only allows records where the level is enabled in the current configuration."""
    def filter(self, record):
        levels_enabled = get_logging_levels_enabled()
        return levels_enabled.get(record.levelno, True)

def should_log(level):
    """Determine if logging should occur for this level."""
    levels_enabled = get_logging_levels_enabled()
    return levels_enabled.get(level, True)

def setup_logger(app):
    """Set up the application logger with the level filter."""
    level_filter = LogLevelFilter()
    for handler in app.logger.handlers:
        if not any(isinstance(f, LogLevelFilter) for f in handler.filters):
            handler.addFilter(level_filter)

def log_with_route(
    level,
    message,
    route=None,
    source_type="Application",
    exc_info=None,
    *,
    request_data_override=None,
    request_headers_override=None,
    append_headers_data=True,
):
    """Log a message with route context, both locally and remotely."""
    if not should_log(level):
        return

    # Get the current process ID (pid)
    pid = os.getpid()

    # Initialize extra with default values
    extra = {
        'source': f'{source_type}, PID: {pid} - No route context',
        'headers': {},
        'data': None
    }

    # Determine the logging context
    if has_request_context():
        client_ip = get_client_ip(request)
        user_agent = request.headers.get('User-Agent', 'Unknown')
        request_method = request.method
        request_url = request.url
        request_headers = request_headers_override if request_headers_override is not None else dict(request.headers)

        # Filter sensitive cookies
        if 'Cookie' in request_headers:
            cookies = request_headers['Cookie'].split('; ')
            filtered_cookies = [cookie for cookie in cookies
                              if not any(sensitive in cookie
                                       for sensitive in ['__stripe_mid', '__stripe_sid'])]
            request_headers['Cookie'] = '; '.join(filtered_cookies)

        if request_data_override is not None:
            request_data = request_data_override
        else:
            request_data = request.get_data(as_text=True) if request.data else None

        # Determine request type
        request_type = "Unknown"
        user_agent_lower = user_agent.lower()
        if any(bot_term in user_agent_lower for bot_term in ["bot", "crawler", "spider"]):
            request_type = "Programmatic"
        elif any(browser_term in user_agent for browser_term in ["Mozilla", "Chrome", "Safari"]):
            request_type = "Browser"

        # Update extra with request context
        extra.update({
            'source': (f'{source_type}, PID: {pid}, {client_ip} - Route: {route or request.path} '
                      f'(Endpoint: {request.endpoint}) - User-Agent: {user_agent} - '
                      f'Type: {request_type} - Method: {request_method} - URL: {request_url}'),
            'headers': request_headers,
            'data': request_data,
            'client_ip': client_ip,
            'request_type': request_type,
            'request_method': request_method,
            'request_url': request_url,
            'route': route or request.path
        })

    # Format the message
    if append_headers_data:
        formatted_message = f'{message} | Headers: {extra["headers"]} | Data: {extra["data"]}'
    else:
        formatted_message = f'{message}'

    # Try remote logging first
    try:
        remote_logger = RemoteLogger()
        remote_logger.log(level, formatted_message, extra, source_type)
    except Exception as e:
        if has_app_context():
            current_app.logger.error(f"Remote logging failed: {str(e)}")

    # Always do local logging as fallback
    if has_app_context() and current_app.logger:
        current_app.logger.log(level, formatted_message, extra=extra, exc_info=exc_info)
    else:
        # Fallback for when there's no Flask application context
        fallback_logger = logging.getLogger('fallback')
        if not fallback_logger.handlers:
            # Ensure the log directory exists
            log_dir = 'wlog'
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)

            handler = logging.FileHandler(os.path.join(log_dir, 'wegweiser.log'))
            handler.addFilter(LogLevelFilter())
            formatter = logging.Formatter('%(asctime)s %(levelname)s [%(source)s]: %(message)s')
            handler.setFormatter(formatter)
            fallback_logger.addHandler(handler)
            fallback_logger.setLevel(logging.DEBUG)

        fallback_logger.log(level, formatted_message, extra={'source': extra['source']}, exc_info=exc_info)