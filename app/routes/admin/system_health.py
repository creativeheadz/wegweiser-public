# Filepath: app/routes/admin/system_health.py
"""
System Health Monitoring & Dependency Validation
Provides real-time system health status and alerts for admin/master users
"""

from flask import Blueprint, render_template, jsonify, session
from app import db, mail
from app.utilities.app_access_login_required import login_required
from app.utilities.app_access_role_required import role_required
import logging
from app.utilities.app_logging_helper import log_with_route
import importlib
import sys
import time
from datetime import datetime, timedelta

system_health_bp = Blueprint('system_health', __name__)


def check_critical_dependencies():
    """
    Validate all critical dependencies are installed and importable.
    Returns dict of dependency status.
    """
    dependencies = {
        'email-validator': {
            'package': 'email_validator',
            'critical': True,
            'reason': 'Required for user registration email validation'
        },
        'flask': {
            'package': 'flask',
            'critical': True,
            'reason': 'Core web framework'
        },
        'sqlalchemy': {
            'package': 'sqlalchemy',
            'critical': True,
            'reason': 'Database ORM'
        },
        'redis': {
            'package': 'redis',
            'critical': False,
            'reason': 'Session storage (fallback available)'
        },
        'celery': {
            'package': 'celery',
            'critical': True,
            'reason': 'Background task processing'
        },
        'flask_mail': {
            'package': 'flask_mail',
            'critical': True,
            'reason': 'Email sending for alerts'
        },
        'requests': {
            'package': 'requests',
            'critical': True,
            'reason': 'HTTP client for webhooks'
        },
        'psycopg2': {
            'package': 'psycopg2',
            'critical': True,
            'reason': 'PostgreSQL database driver'
        }
    }

    results = {}
    all_ok = True

    for name, config in dependencies.items():
        try:
            importlib.import_module(config['package'])
            results[name] = {
                'status': 'OK',
                'installed': True,
                'critical': config['critical'],
                'reason': config['reason']
            }
        except ImportError as e:
            results[name] = {
                'status': 'MISSING',
                'installed': False,
                'critical': config['critical'],
                'reason': config['reason'],
                'error': str(e)
            }
            if config['critical']:
                all_ok = False

    return {
        'all_ok': all_ok,
        'dependencies': results,
        'checked_at': datetime.utcnow().isoformat()
    }


def check_database_connection():
    """Test database connectivity."""
    try:
        db.session.execute(db.text('SELECT 1'))
        return {'status': 'OK', 'message': 'Database connection successful'}
    except Exception as e:
        return {'status': 'ERROR', 'message': str(e)}


def check_mail_config():
    """Verify mail configuration."""
    try:
        if not hasattr(mail, 'server'):
            return {'status': 'WARNING', 'message': 'Mail server not configured'}

        # Check if basic mail config exists
        from flask import current_app
        server = current_app.config.get('MAIL_SERVER')
        if not server:
            return {'status': 'WARNING', 'message': 'MAIL_SERVER not configured'}

        return {'status': 'OK', 'message': f'Mail configured for {server}'}
    except Exception as e:
        return {'status': 'ERROR', 'message': str(e)}


def get_recent_critical_errors():
    """
    Get recent critical errors from logs.
    Returns last 10 critical errors.
    """
    try:
        errors = []
        log_file = '/opt/wegweiser/wlog/wegweiser.log'

        with open(log_file, 'r') as f:
            lines = f.readlines()

        # Look for ERROR and CRITICAL log entries
        for line in reversed(lines[-1000:]):  # Check last 1000 lines
            if 'ERROR' in line or 'CRITICAL' in line:
                # Parse log line
                try:
                    parts = line.split(' - ')
                    if len(parts) >= 2:
                        timestamp = parts[0].strip()
                        message = ' - '.join(parts[1:]).strip()
                        errors.append({
                            'timestamp': timestamp,
                            'message': message[:200]  # Truncate long messages
                        })
                except:
                    continue

                if len(errors) >= 10:
                    break

        return errors

    except Exception as e:
        log_with_route(logging.ERROR, f"Error reading recent errors: {str(e)}")
        return []


@system_health_bp.route('/health/check', methods=['GET'])
@login_required
@role_required(['admin', 'master'])
def health_check():
    """
    Comprehensive health check endpoint.
    Returns JSON with system status.
    """
    health_status = {
        'timestamp': datetime.utcnow().isoformat(),
        'overall_status': 'OK',
        'checks': {}
    }

    # Check dependencies
    dep_check = check_critical_dependencies()
    health_status['checks']['dependencies'] = dep_check
    if not dep_check['all_ok']:
        health_status['overall_status'] = 'DEGRADED'

    # Check database
    db_check = check_database_connection()
    health_status['checks']['database'] = db_check
    if db_check['status'] != 'OK':
        health_status['overall_status'] = 'DEGRADED'

    # Check mail
    mail_check = check_mail_config()
    health_status['checks']['mail'] = mail_check

    # Get recent errors
    recent_errors = get_recent_critical_errors()
    health_status['recent_errors'] = recent_errors
    health_status['error_count'] = len(recent_errors)

    return jsonify(health_status)


@system_health_bp.route('/health/dashboard', methods=['GET'])
@login_required
@role_required(['admin', 'master'])
def health_dashboard():
    """
    System health dashboard page for admin/master users.
    Shows real-time system status and recent errors.
    """
    # Get comprehensive health status
    dep_check = check_critical_dependencies()
    db_check = check_database_connection()
    mail_check = check_mail_config()
    recent_errors = get_recent_critical_errors()

    # Calculate overall status
    overall_status = 'Healthy'
    if not dep_check['all_ok'] or db_check['status'] == 'ERROR':
        overall_status = 'Critical'
    elif mail_check['status'] == 'ERROR':
        overall_status = 'Warning'

    return render_template(
        'administration/system_health.html',
        overall_status=overall_status,
        dependencies=dep_check['dependencies'],
        database_status=db_check,
        mail_status=mail_check,
        recent_errors=recent_errors,
        checked_at=datetime.utcnow()
    )


@system_health_bp.route('/health/ping', methods=['GET'])
def ping():
    """
    Simple ping endpoint for external monitoring.
    No authentication required.
    """
    return jsonify({
        'status': 'ok',
        'timestamp': time.time()
    })
