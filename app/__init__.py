# Filepath: app/__init__.py
from flask import Flask, render_template, Blueprint, request, session, jsonify
from flask_sqlalchemy import SQLAlchemy
import logging
from logging.handlers import RotatingFileHandler
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
from flask_session import Session
from flask_principal import Principal, identity_loaded, RoleNeed, UserNeed, Permission
from dotenv import load_dotenv
from flask_mail import Mail
from flask_wtf.csrf import CSRFProtect, CSRFError
from authlib.integrations.flask_client import OAuth
from app.models import db, Accounts
from app.models.servercore import create_table_and_insert_initial_values as create_servercore_table_and_insert_initial_values
from app.models.roles import create_roles_table_and_insert_initial_values
from app.utilities.app_logging_helper import log_with_route, setup_logger, LogLevelFilter
from app.utilities.notifications import get_all_notifications
from app.utilities.ip_blocker import IPBlocker
from dotenv import dotenv_values
import markdown
import os
from markupsafe import Markup
from functools import lru_cache
from sqlalchemy import exc as sqlalchemy_exceptions
from contextlib import contextmanager
from datetime import timedelta
import redis

from azure.identity import ManagedIdentityCredential
from azure.keyvault.secrets import SecretClient

import importlib
import json

from .extensions import celery, init_celery

# Configure Azure SDK logging to be less verbose
azure_logger = logging.getLogger('azure')
azure_logger.setLevel(logging.WARNING)
azure_logger.propagate = False

# Configure urllib3 logging (used by Azure SDK)
urllib3_logger = logging.getLogger('urllib3')
urllib3_logger.setLevel(logging.WARNING)
urllib3_logger.propagate = False

# Get the path to the directory this file is in
BASEDIR = os.path.abspath(os.path.dirname(__file__))
# Connect the path with the '.env' file name
load_dotenv(os.path.join(BASEDIR, '..', '.env'))
env_vars = dotenv_values(os.path.join(BASEDIR, '..', '.env'))

# Azure Key Vault configuration
key_vault_url = os.environ.get("AZURE_KEY_VAULT_ENDPOINT", "https://wegweiserkv.vault.azure.net/")
_secret_client = None

@contextmanager
def safe_db_session():
    """Provides a safe database session context."""
    session = db.session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        log_with_route(logging.ERROR, f"Database session error: {str(e)}")
        raise
    finally:
        db.session.remove()  # Use the global session registry for cleanup

@lru_cache(maxsize=128)
def get_secret(secret_name):
    """Cached secret retrieval to prevent repeated Azure calls"""
    global _secret_client
    try:
        if (_secret_client is None):
            credential = ManagedIdentityCredential()
            _secret_client = SecretClient(vault_url=key_vault_url, credential=credential)

        secret_value = _secret_client.get_secret(secret_name).value
        log_with_route(logging.INFO, f"Successfully retrieved secret: {secret_name}")
        return secret_value
    except Exception as e:
        log_with_route(logging.ERROR, f"Failed to retrieve secret {secret_name} from Key Vault: {str(e)}")

        # Fallback to environment variable
        env_value = os.getenv(secret_name.upper())
        if env_value:
            log_with_route(logging.WARNING, f"Using fallback environment variable for {secret_name}")
            return env_value

        # Additional fallback for SUPPORTDESKAPITOKEN specifically
        if secret_name == 'SUPPORTDESKAPITOKEN':
            env_value = os.getenv('ZAMMAD_API_TOKEN')
            if env_value:
                log_with_route(logging.WARNING, f"Using alternative fallback ZAMMAD_API_TOKEN for {secret_name}")
                return env_value

        log_with_route(logging.ERROR, f"No fallback available for {secret_name}")
        raise RuntimeError(f"Failed to retrieve {secret_name} from Key Vault and no fallback available")

mail = Mail()
bcrypt = Bcrypt()
migrate = Migrate()
principal = Principal()
csrf = CSRFProtect()

# Define Permissions
admin_permission = Permission(RoleNeed('admin'))
master_permission = Permission(RoleNeed('master'))
user_permission = Permission(RoleNeed('user'))

def admin_or_master_permission():
    return Permission(RoleNeed('admin')) | Permission(RoleNeed('master'))

def init_commands(app):
    pass  # Placeholder for your actual init_commands function

def register_blueprints(app):
    """Register all blueprint modules dynamically while avoiding duplicate registration."""
    registered_blueprints = set()
    routes_dir = os.path.join(os.path.dirname(__file__), 'routes')

    for root, dirs, files in os.walk(routes_dir):
        for filename in files:
            if filename.endswith('.py') and filename != '__init__.py':
                rel_path = os.path.relpath(root, routes_dir)
                if rel_path == '.':
                    module_path = f"app.routes.{filename[:-3]}"
                else:
                    module_path = f"app.routes.{rel_path.replace(os.sep, '.')}.{filename[:-3]}"
                try:
                    module = importlib.import_module(module_path)
                    for attr in dir(module):
                        item = getattr(module, attr)
                        if isinstance(item, Blueprint) and item.name not in registered_blueprints:
                            app.register_blueprint(item)
                            registered_blueprints.add(item.name)
                except ImportError as e:
                    app.logger.error(f"Failed to import {module_path}: {e}")


def create_app():
    app = Flask(__name__)

    # Startup validation: ensure the audit payload JSON schema exists and is readable.
    # This prevents late discovery (first incoming audit) when the schema is missing/invalid.
    try:
        project_root = os.path.dirname(app.root_path)
        schema_path = os.path.join(project_root, 'includes', 'payloadAuditSchema.json')

        if not os.path.exists(schema_path):
            app.logger.error(f"Missing audit payload schema file: {schema_path}")
            app.config['PAYLOAD_AUDIT_SCHEMA_OK'] = False
            app.config['PAYLOAD_AUDIT_SCHEMA_ERROR'] = f"missing: {schema_path}"
        else:
            with open(schema_path, 'r') as f:
                schema_obj = json.load(f)

            if not isinstance(schema_obj, dict):
                app.logger.error(
                    f"Invalid audit payload schema type in {schema_path}: expected object/dict, got {type(schema_obj).__name__}"
                )
                app.config['PAYLOAD_AUDIT_SCHEMA_OK'] = False
                app.config['PAYLOAD_AUDIT_SCHEMA_ERROR'] = f"invalid schema type: {type(schema_obj).__name__}"
            else:
                app.logger.info(f"Audit payload schema OK: {schema_path}")
                app.config['PAYLOAD_AUDIT_SCHEMA_OK'] = True
                app.config['PAYLOAD_AUDIT_SCHEMA_ERROR'] = None

    except Exception as e:
        app.logger.error(f"Failed to validate audit payload schema: {str(e)}")
        app.config['PAYLOAD_AUDIT_SCHEMA_OK'] = False
        app.config['PAYLOAD_AUDIT_SCHEMA_ERROR'] = str(e)

    # Ensure the IP blocker data directory exists
    ip_blocker_dir = os.path.join(app.root_path, 'data', 'ip_blocker')
    if not os.path.exists(ip_blocker_dir):
        os.makedirs(ip_blocker_dir)

    try:
        database_url = get_secret('DatabaseUrl')
        log_with_route(logging.INFO, f"Retrieved DatabaseUrl: {database_url[:10]}...")

        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_size': 20,  # Increased from 10
            'pool_timeout': 30,
            'pool_recycle': 1800,  # Recycle connections every 30 minutes
            'pool_pre_ping': True,  # Enable connection verification
            'max_overflow': 25,  # Increased from 15
            'isolation_level': 'READ COMMITTED',
            'connect_args': {
                'connect_timeout': 10,
                'keepalives': 1,
                'keepalives_idle': 30,
                'keepalives_interval': 10,
                'keepalives_count': 5
            }
        }
        log_with_route(logging.INFO, "Successfully set SQLALCHEMY_DATABASE_URI from Key Vault")
    except Exception as e:
        log_with_route(logging.ERROR, f"Failed to set SQLALCHEMY_DATABASE_URI: {str(e)}")
        raise RuntimeError("Failed to configure essential database settings")

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Critical security configurations - now using Key Vault
    try:
        secret_key = get_secret('SECRETKEY')
        if not secret_key:
            raise RuntimeError("SECRETKEY not found in Key Vault")
        app.config['SECRET_KEY'] = secret_key
        log_with_route(logging.INFO, "Successfully loaded SECRET_KEY from Key Vault")
    except Exception as e:
        log_with_route(logging.ERROR, f"Failed to load SECRET_KEY from Key Vault: {str(e)}")
        raise RuntimeError("Failed to configure SECRET_KEY from Key Vault")

    try:
        api_key = get_secret('APIKEY')
        if not api_key:
            raise RuntimeError("APIKEY not found in Key Vault")
        app.config['API_KEY'] = api_key
        log_with_route(logging.INFO, "Successfully loaded API_KEY from Key Vault")
    except Exception as e:
        log_with_route(logging.ERROR, f"Failed to load API_KEY from Key Vault: {str(e)}")
        raise RuntimeError("Failed to configure API_KEY from Key Vault")

    # Session Configuration - Redis-based for security
    try:
        # Test Redis connection first (Redis is on the appserver)
        redis_client = redis.Redis(
            host='localhost',  # Redis is on the appserver
            port=6379,
            db=1,  # Use separate database from Celery (db=0)
            decode_responses=False,  # Flask-Session handles its own serialization
            socket_timeout=5,
            socket_connect_timeout=5,
            health_check_interval=30
        )
        redis_client.ping()  # Test connection

        # Redis is available, use it for sessions with Redis-specific settings
        app.config['SESSION_TYPE'] = 'redis'
        app.config['SESSION_REDIS'] = redis_client
        app.config['SESSION_KEY_PREFIX'] = 'wegweiser:session:'  # Redis namespace
        log_with_route(logging.INFO, "Using Redis for session storage")

    except Exception as e:
        # Redis not available, fall back to filesystem with warning
        log_with_route(logging.WARNING, f"Redis not available for sessions ({str(e)}), falling back to filesystem")
        app.config['SESSION_TYPE'] = 'filesystem'
        app.config['SESSION_FILE_DIR'] = os.path.join(app.root_path, '..', 'flask_session')
        app.config['SESSION_KEY_PREFIX'] = 'session:'  # Filesystem-compatible prefix

        # Ensure session directory exists
        if not os.path.exists(app.config['SESSION_FILE_DIR']):
            os.makedirs(app.config['SESSION_FILE_DIR'])

    # Common session security settings (applied to both Redis and filesystem)
    app.config['SESSION_PERMANENT'] = True
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)  # 2-hour session timeout
    app.config['SESSION_USE_SIGNER'] = True  # Sign session cookies
    app.config['SESSION_COOKIE_SECURE'] = True  # Enforce HTTPS
    app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JavaScript access to cookies
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection
    app.config['SESSION_COOKIE_NAME'] = 'wegweiser_session'  # Custom session cookie name
    app.config['SESSION_COOKIE_PATH'] = '/'  # Session cookie path
    app.config['SESSION_COOKIE_DOMAIN'] = None  # Let Flask handle domain automatically

    # File upload and storage configuration
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static/images/profilepictures')
    app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB max file size for payload processing
    app.config['TENANT_LOGO_FOLDER'] = os.path.join(app.root_path, 'static/images/tenantprofile')
    app.config['PREFERRED_URL_SCHEME'] = 'https'

    # Remote logging configuration - using Key Vault for password
    app.config['REMOTE_LOGGING_ENABLED'] = os.getenv('REMOTE_LOGGING_ENABLED', 'False').lower() in ['true', '1', 't']
    app.config['REMOTE_LOGGING_SERVER'] = os.getenv('REMOTE_LOGGING_SERVER')
    app.config['REMOTE_LOGGING_PORT'] = int(os.getenv('REMOTE_LOGGING_PORT', '6379'))
    try:
        app.config['REMOTE_LOGGING_PASSWORD'] = get_secret('REMOTELOGGINGPASSWORD')
        log_with_route(logging.INFO, "Successfully loaded remote logging password from Key Vault")
    except Exception as e:
        log_with_route(logging.WARNING, f"Failed to load remote logging password from Key Vault, using env fallback: {str(e)}")
        app.config['REMOTE_LOGGING_PASSWORD'] = os.getenv('REMOTE_LOGGING_PASSWORD')
    app.config['REMOTE_LOGGING_TIMEOUT'] = int(os.getenv('REMOTE_LOGGING_TIMEOUT', '2'))
    app.config['REMOTE_LOGGING_RETRY_COUNT'] = int(os.getenv('REMOTE_LOGGING_RETRY_COUNT', '1'))
    app.config['REMOTE_LOGGING_FALLBACK_LOCAL'] = True  # Always fall back to local logging

    # IP Blocker configuration - using Key Vault for password
    app.config['IP_BLOCKER_USE_REDIS'] = os.getenv('IP_BLOCKER_USE_REDIS', 'False').lower() in ['true', '1', 't']
    app.config['IP_BLOCKER_USE_LMDB'] = os.getenv('IP_BLOCKER_USE_LMDB', 'True').lower() in ['true', '1', 't']
    app.config['IP_BLOCKER_REDIS_HOST'] = os.getenv('IP_BLOCKER_REDIS_HOST')
    app.config['IP_BLOCKER_REDIS_PORT'] = int(os.getenv('IP_BLOCKER_REDIS_PORT', '6379'))
    try:
        app.config['IP_BLOCKER_REDIS_PASSWORD'] = get_secret('IPBLOCKERREDISPASSWORD')
        log_with_route(logging.INFO, "Successfully loaded IP blocker Redis password from Key Vault")
    except Exception as e:
        log_with_route(logging.WARNING, f"Failed to load IP blocker Redis password from Key Vault, using env fallback: {str(e)}")
        app.config['IP_BLOCKER_REDIS_PASSWORD'] = os.getenv('IP_BLOCKER_REDIS_PASSWORD')
    app.config['IP_BLOCKER_DATA_DIR'] = os.path.join(app.root_path, 'data', 'ip_blocker')

    # Ensure IP blocker data directory exists
    if not os.path.exists(app.config['IP_BLOCKER_DATA_DIR']):
        os.makedirs(app.config['IP_BLOCKER_DATA_DIR'])



    # Access secrets from Azure Key Vault
    app.config['AZURE_OPENAI_API_KEY'] = get_secret('AZUREOPENAIAPIKEY')
    app.config['AZURE_OPENAI_API_VERSION'] = get_secret('AZUREOPENAIAPIVERSION')
    app.config['AZURE_OPENAI_ENDPOINT'] = get_secret('AZUREOPENAIENDPOINT')

    # Azure AD OAuth Configuration
    app.config['AZURE_TENANT_ID'] = get_secret('AZURETENANTID')
    app.config['AZURE_CLIENT_ID'] = get_secret('AZURECLIENTID')
    app.config['AZURE_CLIENT_SECRET'] = get_secret('AZURECLIENTSECRET')
    app.config['AZURE_REDIRECT_URI'] = get_secret('AZUREREDIRECTURI')
    app.config['STRIPE_SECRET_KEY'] = get_secret('STRIPESECRETKEY')
    app.config['STRIPE_WEBHOOK_SECRET'] = get_secret('STRIPEWEBHOOKSECRET')

    # Initialize OAuth
    oauth = OAuth(app)

    global microsoft
    microsoft = oauth.register(
        name='microsoft',
        client_id=app.config['AZURE_CLIENT_ID'],
        client_secret=app.config['AZURE_CLIENT_SECRET'],
        access_token_url=f'https://login.microsoftonline.com/{app.config["AZURE_TENANT_ID"]}/oauth2/v2.0/token',
        authorize_url=f'https://login.microsoftonline.com/{app.config["AZURE_TENANT_ID"]}/oauth2/v2.0/authorize',
        authorize_params=None,
        client_kwargs={'scope': 'User.Read'},
        redirect_uri=app.config['AZURE_REDIRECT_URI'],
    )

    # reCAPTCHA configuration - now using Key Vault
    try:
        app.config['RECAPTCHA_PUBLIC_KEY'] = get_secret('RECAPTCHAPUBLICKEY')
        app.config['RECAPTCHA_PRIVATE_KEY'] = get_secret('RECAPTCHAPRIVATEKEY')
        log_with_route(logging.INFO, "Successfully loaded reCAPTCHA keys from Key Vault")
    except Exception as e:
        log_with_route(logging.ERROR, f"Failed to load reCAPTCHA keys from Key Vault: {str(e)}")
        # Fallback to environment variables for reCAPTCHA (non-critical)
        app.config['RECAPTCHA_PUBLIC_KEY'] = os.getenv('RECAPTCHA_PUBLIC_KEY')
        app.config['RECAPTCHA_PRIVATE_KEY'] = os.getenv('RECAPTCHA_PRIVATE_KEY')

    # Email configuration - now using Key Vault
    try:
        app.config['MAIL_SERVER'] = get_secret('MAILSERVER')
        app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', '587'))  # Keep port as env var (non-sensitive)
        app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() in ['true', '1', 't']  # Keep as env var
        app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'False').lower() in ['true', '1', 't']  # Keep as env var
        app.config['MAIL_USERNAME'] = get_secret('MAILUSERNAME')
        app.config['MAIL_PASSWORD'] = get_secret('MAILPASSWORD')
        app.config['MAIL_DEFAULT_SENDER'] = get_secret('MAILDEFAULTSENDER')
        log_with_route(logging.INFO, "Successfully loaded email configuration from Key Vault")
    except Exception as e:
        log_with_route(logging.ERROR, f"Failed to load email configuration from Key Vault: {str(e)}")
        # Fallback to environment variables for email (non-critical)
        app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
        app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', '587'))
        app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() in ['true', '1', 't']
        app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'False').lower() in ['true', '1', 't']
        app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
        app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
        app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')

    app.config['WTF_CSRF_ENABLED'] = True

    # Celery Configuration (robust: Key Vault first, then ENV fallbacks)
    from urllib.parse import urlparse
    broker_url = None
    result_backend = None
    try:
        broker_url = get_secret('CELERYBROKERURL')
    except Exception:
        broker_url = None
    try:
        result_backend = get_secret('CELERYRESULTBACKEND')
    except Exception:
        result_backend = None

    # Fallback to standard Celery env vars if Key Vault secrets are unavailable
    if not broker_url:
        broker_url = os.getenv('CELERY_BROKER_URL')
    if not result_backend:
        result_backend = os.getenv('CELERY_RESULT_BACKEND')

    # Normalize common typos like 'redis//host' -> 'redis://host'
    def _normalize_url(u: str | None) -> str | None:
        if not u:
            return u
        # Fix common typos
        if u.startswith('redis//'):
            return 'redis://' + u[len('redis//'):]
        if u.startswith('edis://'):
            return 'redis://' + u[len('edis://'):]
        return u

    broker_url = _normalize_url(broker_url)
    result_backend = _normalize_url(result_backend)

    app.config.update({
        'broker_url': broker_url,
        'result_backend': result_backend,
        'broker_connection_retry_on_startup': True
    })

    # ZAMMAD CONFIG
    app.config['SUPPORTDESK_API_TOKEN'] = get_secret('SUPPORTDESKAPITOKEN')

    # Application Flags
    app.config['LOG_DEVICE_HEALTH_SCORE'] = os.getenv('LOG_DEVICE_HEALTH_SCORE', 'False') == 'True'

    # Ensure the upload folders exists
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    if not os.path.exists(app.config['TENANT_LOGO_FOLDER']):
        os.makedirs(app.config['TENANT_LOGO_FOLDER'])

    # Initialize Extensions
    Session(app)
    db.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)
    principal.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)

    # Database error handlers
    @app.errorhandler(sqlalchemy_exceptions.OperationalError)
    def handle_db_operational_error(error):
        db.session.remove()
        log_with_route(logging.ERROR, f"Database operational error: {str(error)}")
        return jsonify({
            "error": "A database error occurred",
            "retry": True
        }), 500

    @app.errorhandler(sqlalchemy_exceptions.SQLAlchemyError)
    def handle_sqlalchemy_error(error):
        db.session.remove()
        log_with_route(logging.ERROR, f"SQLAlchemy error: {str(error)}")
        return jsonify({
            "error": "A database error occurred",
            "retry": True
        }), 500

    @app.context_processor
    def inject_user():
        def get_current_user():
            try:
                user_id = session.get('user_id')
                if user_id:
                    db.session.expire_on_commit = False
                    return db.session.query(Accounts).filter(
                        Accounts.useruuid == user_id
                    ).populate_existing().first()
                return None
            except Exception as e:
                log_with_route(logging.ERROR, f"Error in get_current_user: {str(e)}")
                db.session.rollback()
                return None
        return dict(user=get_current_user())

    @app.context_processor
    def inject_notifications():
        return dict(get_all_notifications=get_all_notifications)

    @app.context_processor
    def inject_csrf_token():
        from flask_wtf.csrf import generate_csrf
        return dict(csrf_token=generate_csrf)

    # Initialize Celery
    init_celery(app)

# Logging configuration
    if not app.debug:
        if not os.path.exists('wlog'):
            os.makedirs('wlog')

        # Remove all handlers associated with the app logger
        for handler in app.logger.handlers[:]:
            app.logger.removeHandler(handler)

        file_handler = RotatingFileHandler('wlog/wegweiser.log', maxBytes=10485760, backupCount=10, delay=False)

        # Custom SourceFilter to ensure 'source' is present
        class SourceFilter(logging.Filter):
            def filter(self, record):
                if not hasattr(record, 'source'):
                    record.source = 'Unknown'
                return True

        file_handler.addFilter(SourceFilter())
        file_handler.addFilter(LogLevelFilter())

        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s [%(source)s]: %(message)s [in %(pathname)s:%(lineno)d]'
        ))

        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.DEBUG)

    # Call setup_logger to ensure filters are properly applied
    setup_logger(app)

    # Register blueprints
    register_blueprints(app)

    # Initialize custom commands
    init_commands(app)

    # Enhanced Markdown filter with additional extensions
    @app.template_filter('markdown')
    def markdown_filter(text):
        if not text:
            return ''
        return Markup(markdown.markdown(text, extensions=[
            'markdown.extensions.fenced_code',
            'markdown.extensions.tables',
            'markdown.extensions.codehilite',
            'markdown.extensions.sane_lists',
            'markdown.extensions.nl2br',
            'markdown.extensions.toc'
        ]))

    # FAQ HTML filter to ensure proper HTML rendering with Markdown support
    @app.template_filter('faq_html')
    def faq_html_filter(text):
        if not text:
            return ''

        # Import required modules
        import html
        import re
        from markdown_it import MarkdownIt

        # Handle multiple levels of HTML escaping that might have occurred
        unescaped = text
        # Keep unescaping until no more HTML entities are found
        prev_unescaped = None
        while prev_unescaped != unescaped:
            prev_unescaped = unescaped
            unescaped = html.unescape(unescaped)

        # Check if this looks like Markdown content
        markdown_indicators = [
            r'\*\*.*?\*\*',  # Bold text
            r'\*.*?\*',      # Italic text
            r'^#{1,6}\s',    # Headers
            r'^\s*[-*+]\s',  # Lists
            r'^\s*\d+\.\s',  # Numbered lists
            r'`.*?`',        # Code
        ]

        has_markdown = any(re.search(pattern, unescaped, re.MULTILINE) for pattern in markdown_indicators)

        if has_markdown:
            # Process as Markdown
            md = MarkdownIt()
            html_content = md.render(unescaped)
            return Markup(html_content)
        elif not re.search(r'<[^>]+>', unescaped):
            # No HTML tags and no Markdown found, treat as plain text and convert line breaks
            unescaped = unescaped.replace('\n', '<br>')

        # Return as safe markup
        return Markup(unescaped)

    # Timestamp to datetime filter for Lynis audit timestamps
    @app.template_filter('timestamp_to_datetime')
    def timestamp_to_datetime_filter(timestamp):
        """Convert Unix timestamp to formatted datetime string"""
        if not timestamp:
            return 'N/A'
        try:
            from datetime import datetime
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
            return 'Invalid date'

    # Security headers middleware
    @app.after_request
    def add_security_headers(response):
        """Add security headers to all responses"""
        # Prevent clickjacking
        response.headers['X-Frame-Options'] = 'DENY'

        # Prevent MIME type sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'

        # XSS protection
        response.headers['X-XSS-Protection'] = '1; mode=block'

        # Referrer policy
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # Content Security Policy (updated for external resources)
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://www.google.com https://www.gstatic.com https://fonts.googleapis.com https://js.stripe.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
            "img-src 'self' data: https:; "
            "font-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com https://fonts.gstatic.com; "
            "connect-src 'self' https://www.google.com https://ipapi.co https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://api.stripe.com; "
            "frame-src https://www.google.com https://js.stripe.com; "
            "frame-ancestors 'none';"
        )

        # Strict Transport Security (HSTS) - only in production
        if not app.debug:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

        return response

    # Session security middleware
    @app.before_request
    def check_session_security():
        """Check session validity and update activity tracking"""
        from app.utilities.session_manager import session_manager

        # Skip session checks for static files and certain routes
        if (request.endpoint and
            (request.endpoint.startswith('static') or
             request.endpoint in ['login_bp.login', 'login_bp.logout', 'register_bp.register'])):
            return

        # Handle session errors gracefully
        try:
            user_id = session.get('user_id')
            if user_id:
                # Update session activity tracking
                try:
                    session_manager.track_user_session(str(user_id))
                except Exception as e:
                    log_with_route(logging.WARNING, f"Failed to update session activity: {str(e)}")
        except Exception as e:
            # Session is corrupted, clear it and log details
            log_with_route(logging.ERROR, f"Session corruption detected, clearing session: {str(e)}")
            try:
                session.clear()
            except:
                # If even clearing fails, we have a serious session interface issue
                log_with_route(logging.CRITICAL, "Unable to clear corrupted session - session interface failure")

    # Set up Flask-Principal identity loader
    @identity_loaded.connect_via(app)
    def on_identity_loaded(sender, identity):
        try:
            user_id = identity.id
            db.session.expire_on_commit = False
            user = db.session.query(Accounts).filter(
                Accounts.useruuid == user_id
            ).populate_existing().first()

            if user:
                identity.provides.add(UserNeed(user.useruuid))
                if user.role and user.role.rolename:
                    identity.provides.add(RoleNeed(user.role.rolename))
        except Exception as e:
            log_with_route(logging.ERROR, f"Error in identity loading: {str(e)}")
            db.session.rollback()

    # Database connection cleanup after each request
    @app.after_request
    def cleanup_db_resources(response):
        try:
            db.session.remove()
        except Exception as e:
            log_with_route(logging.ERROR, f"Error during DB cleanup: {str(e)}")
        return response

    # Create the tables and insert initial values
    with app.app_context():
        try:
            create_servercore_table_and_insert_initial_values()
            create_roles_table_and_insert_initial_values()
        except Exception as e:
            # If it's a column not found error, it's likely a pending migration
            if "does not exist" in str(e) or "UndefinedColumn" in str(e):
                log_with_route(logging.WARNING, f"Pending database migration detected: {str(e)}")
                log_with_route(logging.WARNING, "Run 'flask db upgrade' to apply pending migrations")
            else:
                log_with_route(logging.ERROR, f"Error during initial table setup: {str(e)}")
                raise

    # Error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        # Get client IP from headers or remote address
        ip = request.headers.get('X-Real-IP') or request.headers.get('X-Forwarded-For') or request.remote_addr

        # Handle request data logging more intelligently to avoid blob data spam
        request_data = None
        try:
            raw_data = request.get_data()
            if raw_data:
                # Check content type to determine how to log the data
                content_type = request.headers.get('Content-Type', '').lower()
                if 'application/dns-message' in content_type:
                    # DNS-over-HTTPS probe - log as hex for analysis but keep it concise
                    request_data = f"DNS-DoH-Binary({len(raw_data)}B): {raw_data[:32].hex()}{'...' if len(raw_data) > 32 else ''}"
                elif content_type.startswith('text/') or 'json' in content_type:
                    # Text-based data - try to decode
                    request_data = raw_data.decode('utf-8', errors='replace')[:200]
                else:
                    # Other binary data - just show size and type
                    request_data = f"Binary({len(raw_data)}B, {content_type})"
            else:
                request_data = "None"
        except Exception:
            request_data = "Error reading request data"

        # Log the 404 error (log_with_route already appends headers/data)
        log_with_route(logging.ERROR, "404 error triggered", request_data_override=request_data)

        # Initialize IP blocker and handle the failed request
        blocker = IPBlocker()
        result = blocker.handle_failed_request(ip, request.url)

        if result and result.get("success"):
            log_with_route(logging.WARNING, f"Blocked IP {ip} after 404 error on {request.url}")
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        db.session.remove()  # Ensure any broken sessions are cleaned up
        log_with_route(logging.ERROR, "500 internal server error", request.path)

        # Send critical error alert
        try:
            from app.utilities.critical_error_monitor import monitor_error
            monitor_error(e, endpoint=request.path, status_code=500)
        except Exception as monitor_err:
            log_with_route(logging.ERROR, f"Error monitor failed: {str(monitor_err)}")

        return render_template('errors/500.html'), 500

    @app.errorhandler(Exception)
    def handle_exception(e):
        """Catch all unhandled exceptions and send alerts for critical ones."""
        # Let HTTP exceptions pass through to their specific handlers
        from werkzeug.exceptions import HTTPException
        if isinstance(e, HTTPException):
            return e

        # Log and monitor the exception
        db.session.remove()
        log_with_route(logging.ERROR, f"Unhandled exception: {type(e).__name__}: {str(e)}", exc_info=True)

        # Send critical error alert
        try:
            from app.utilities.critical_error_monitor import monitor_error
            monitor_error(e, endpoint=request.path, status_code=500)
        except Exception as monitor_err:
            log_with_route(logging.ERROR, f"Error monitor failed: {str(monitor_err)}")

        # Return generic 500 error
        return render_template('errors/500.html'), 500

    @app.errorhandler(403)
    def forbidden(e):
        log_with_route(logging.ERROR, "403 forbidden error", request.path)
        return render_template('errors/403.html'), 403

    # Handle Flask-Principal PermissionDenied exceptions
    from flask_principal import PermissionDenied
    @app.errorhandler(PermissionDenied)
    def handle_permission_denied(e):
        log_with_route(logging.ERROR, "403 forbidden error (PermissionDenied)", request.path)
        return render_template('errors/403.html'), 403


    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        # Friendly handling of expired/missing CSRF token (usually due to expired session)
        ip = request.headers.get('X-Real-IP') or request.headers.get('X-Forwarded-For') or request.remote_addr
        try:
            path = request.path
        except Exception:
            path = "unknown"
        # Keep logs terse; avoid leaking sensitive info
        log_with_route(logging.WARNING, f"CSRF error at {path} from {ip}: {getattr(e, 'description', str(e))}")
        return render_template('errors/csrf.html', reason=getattr(e, 'description', 'Your session expired.')), 400

    # Register CLI commands
    from app import cli_commands
    cli_commands.init_app(app)

    log_with_route(logging.INFO, "Application initialized successfully")
    return app

# Expose the Flask app instance at the module level
app = create_app