# Filepath: app/routes/admin/session_management.py
"""
Admin routes for session management and security monitoring
"""

from flask import Blueprint, render_template, request, jsonify, session, flash, redirect, url_for
from flask_principal import Permission, RoleNeed
from app.utilities.session_manager import session_manager
from app.utilities.app_logging_helper import log_with_route
from app.utilities.app_get_current_user import get_current_user
from app.models.accounts import Accounts
from app.models import db
import logging
from datetime import datetime
import uuid

session_admin_bp = Blueprint('session_admin_bp', __name__)
admin_permission = Permission(RoleNeed('admin'))


@session_admin_bp.route('/admin/sessions')
@admin_permission.require(http_exception=403)
def view_sessions():
    """View active sessions across all users"""
    user = get_current_user()
    user_email = user.companyemail if user else 'unknown'
    log_with_route(logging.INFO, f"Session management page accessed by {user_email}")
    
    return render_template('administration/admin_sessions.html')


@session_admin_bp.route('/api/admin/sessions/list')
@admin_permission.require(http_exception=403)
def list_all_sessions():
    """API endpoint to list all active sessions"""
    try:
        # Get all users in the current tenant
        current_user = get_current_user()
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        tenant_uuid = current_user.tenantuuid
        users = Accounts.query.filter_by(tenantuuid=tenant_uuid).all()
        
        all_sessions = []
        for user in users:
            user_sessions = session_manager.get_user_sessions(str(user.useruuid))
            for sess in user_sessions:
                sess['user_info'] = {
                    'user_id': str(user.useruuid),
                    'name': f"{user.firstname} {user.lastname}",
                    'email': user.companyemail,
                    'role': user.role.rolename if user.role else 'unknown'
                }
                all_sessions.append(sess)
        
        # Sort by last activity (most recent first)
        all_sessions.sort(key=lambda x: x['last_activity'], reverse=True)
        
        return jsonify({
            'sessions': all_sessions,
            'total_count': len(all_sessions)
        })
        
    except Exception as e:
        log_with_route(logging.ERROR, f"Failed to list sessions: {str(e)}")
        return jsonify({'error': 'Failed to retrieve sessions'}), 500


@session_admin_bp.route('/api/admin/sessions/user/<user_id>')
@admin_permission.require(http_exception=403)
def get_user_sessions(user_id):
    """Get sessions for a specific user"""
    try:
        # Validate user exists and is in same tenant
        current_user = get_current_user()
        if not current_user:
            return jsonify({'error': 'Current user not found'}), 404
        
        target_user = Accounts.query.filter_by(
            useruuid=user_id,
            tenantuuid=current_user.tenantuuid
        ).first()
        
        if not target_user:
            return jsonify({'error': 'User not found'}), 404
        
        user_sessions = session_manager.get_user_sessions(user_id)
        
        return jsonify({
            'user_info': {
                'user_id': str(target_user.useruuid),
                'name': f"{target_user.firstname} {target_user.lastname}",
                'email': target_user.companyemail,
                'role': target_user.role.rolename if target_user.role else 'unknown'
            },
            'sessions': user_sessions,
            'session_count': len(user_sessions)
        })
        
    except Exception as e:
        log_with_route(logging.ERROR, f"Failed to get user sessions: {str(e)}")
        return jsonify({'error': 'Failed to retrieve user sessions'}), 500


@session_admin_bp.route('/api/admin/sessions/invalidate', methods=['POST'])
@admin_permission.require(http_exception=403)
def invalidate_user_sessions():
    """Invalidate all sessions for a user"""
    try:
        data = request.get_json()
        target_user_id = data.get('user_id')
        reason = data.get('reason', 'admin_action')
        
        if not target_user_id:
            return jsonify({'error': 'User ID required'}), 400
        
        # Validate user exists and is in same tenant
        current_user = get_current_user()
        if not current_user:
            return jsonify({'error': 'Current user not found'}), 404
        
        target_user = Accounts.query.filter_by(
            useruuid=target_user_id,
            tenantuuid=current_user.tenantuuid
        ).first()
        
        if not target_user:
            return jsonify({'error': 'User not found'}), 404
        
        # Don't allow admins to invalidate their own sessions
        if str(target_user.useruuid) == str(current_user.useruuid):
            return jsonify({'error': 'Cannot invalidate your own sessions'}), 400
        
        # Invalidate sessions
        success = session_manager.invalidate_user_sessions(target_user_id)
        
        if success:
            log_with_route(
                logging.WARNING,
                f"Admin {current_user.companyemail} invalidated all sessions for user {target_user.companyemail} - reason: {reason}"
            )
            return jsonify({'message': 'Sessions invalidated successfully'})
        else:
            return jsonify({'error': 'Failed to invalidate sessions'}), 500
        
    except Exception as e:
        log_with_route(logging.ERROR, f"Failed to invalidate sessions: {str(e)}")
        return jsonify({'error': 'Failed to invalidate sessions'}), 500


@session_admin_bp.route('/api/admin/sessions/force-logout', methods=['POST'])
@admin_permission.require(http_exception=403)
def force_logout_user():
    """Force logout a user (invalidate all sessions)"""
    try:
        data = request.get_json()
        target_user_id = data.get('user_id')
        reason = data.get('reason', 'admin_force_logout')
        
        if not target_user_id:
            return jsonify({'error': 'User ID required'}), 400
        
        # Validate user exists and is in same tenant
        current_user = get_current_user()
        if not current_user:
            return jsonify({'error': 'Current user not found'}), 404
        
        target_user = Accounts.query.filter_by(
            useruuid=target_user_id,
            tenantuuid=current_user.tenantuuid
        ).first()
        
        if not target_user:
            return jsonify({'error': 'User not found'}), 404
        
        # Don't allow admins to force logout themselves
        if str(target_user.useruuid) == str(current_user.useruuid):
            return jsonify({'error': 'Cannot force logout yourself'}), 400
        
        # Force logout
        success = session_manager.force_logout_user(target_user_id, reason)
        
        if success:
            log_with_route(
                logging.WARNING,
                f"Admin {current_user.companyemail} forced logout for user {target_user.companyemail} - reason: {reason}"
            )
            return jsonify({'message': 'User logged out successfully'})
        else:
            return jsonify({'error': 'Failed to force logout'}), 500
        
    except Exception as e:
        log_with_route(logging.ERROR, f"Failed to force logout: {str(e)}")
        return jsonify({'error': 'Failed to force logout'}), 500


@session_admin_bp.route('/api/admin/sessions/stats')
@admin_permission.require(http_exception=403)
def get_session_stats():
    """Get session statistics for the tenant"""
    try:
        current_user = get_current_user()
        if not current_user:
            return jsonify({'error': 'Current user not found'}), 404
        
        tenant_uuid = current_user.tenantuuid
        users = Accounts.query.filter_by(tenantuuid=tenant_uuid).all()
        
        total_users = len(users)
        active_users = 0
        total_sessions = 0
        
        for user in users:
            user_sessions = session_manager.get_user_sessions(str(user.useruuid))
            if user_sessions:
                active_users += 1
                total_sessions += len(user_sessions)
        
        return jsonify({
            'total_users': total_users,
            'active_users': active_users,
            'total_sessions': total_sessions,
            'max_sessions_per_user': session_manager.max_concurrent_sessions
        })
        
    except Exception as e:
        log_with_route(logging.ERROR, f"Failed to get session stats: {str(e)}")
        return jsonify({'error': 'Failed to retrieve session statistics'}), 500


@session_admin_bp.route('/api/admin/sessions/config', methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def session_config():
    """Get or update session configuration"""
    if request.method == 'GET':
        try:
            return jsonify({
                'max_concurrent_sessions': session_manager.max_concurrent_sessions,
                'session_timeout_hours': 2,  # From app config
                'redis_connected': session_manager._get_redis_client() is not None
            })
        except Exception as e:
            log_with_route(logging.ERROR, f"Failed to get session config: {str(e)}")
            return jsonify({'error': 'Failed to retrieve configuration'}), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            max_sessions = data.get('max_concurrent_sessions')
            
            if max_sessions and isinstance(max_sessions, int) and 1 <= max_sessions <= 10:
                session_manager.max_concurrent_sessions = max_sessions
                
                current_user = get_current_user()
                user_email = current_user.companyemail if current_user else 'unknown'
                
                log_with_route(
                    logging.INFO,
                    f"Session configuration updated by {user_email}: max_concurrent_sessions={max_sessions}"
                )
                
                return jsonify({'message': 'Configuration updated successfully'})
            else:
                return jsonify({'error': 'Invalid max_concurrent_sessions value (must be 1-10)'}), 400
                
        except Exception as e:
            log_with_route(logging.ERROR, f"Failed to update session config: {str(e)}")
            return jsonify({'error': 'Failed to update configuration'}), 500
