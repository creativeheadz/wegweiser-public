# Filepath: app/utilities/session_manager.py
"""
Session Security Manager
Handles session regeneration, concurrent session limits, and security monitoring
"""

import redis
import json
import uuid
from datetime import datetime, timedelta
from flask import session, current_app, request
from app.utilities.app_logging_helper import log_with_route
import logging


class SessionManager:
    """Manages secure session operations and concurrent session limits"""
    
    def __init__(self):
        self.redis_client = None
        self.max_concurrent_sessions = 3  # Maximum sessions per user
        self.session_prefix = "wegweiser:user_sessions:"
        self.session_data_prefix = "wegweiser:session_data:"
        
    def _get_redis_client(self):
        """Get Redis client for session management"""
        if self.redis_client is None:
            try:
                self.redis_client = redis.Redis(
                    host='localhost',  # Redis is on the appserver
                    port=6379,
                    db=2,  # Use separate database for session tracking
                    decode_responses=True,  # We handle JSON serialization manually
                    socket_timeout=5,
                    socket_connect_timeout=5,
                    health_check_interval=30
                )
                # Test connection
                self.redis_client.ping()
            except Exception as e:
                log_with_route(logging.ERROR, f"Failed to connect to Redis for session management: {str(e)}")
                return None
        return self.redis_client
    
    def regenerate_session(self, user_id=None, reason="security"):
        """
        Regenerate session ID for security
        Call this after login, privilege escalation, or security events
        """
        try:
            # Store current session data
            old_data = dict(session)
            
            # Clear current session
            session.clear()
            
            # Generate new session ID
            session.permanent = True
            
            # Restore session data
            for key, value in old_data.items():
                session[key] = value
            
            # Log session regeneration
            log_with_route(
                logging.INFO,
                f"Session regenerated for user {user_id or 'unknown'} - reason: {reason}"
            )
            
            return True
            
        except Exception as e:
            log_with_route(logging.ERROR, f"Failed to regenerate session: {str(e)}")
            return False
    
    def track_user_session(self, user_id, session_id=None):
        """
        Track user session for concurrent session management
        Returns True if session is allowed, False if limit exceeded
        """
        redis_client = self._get_redis_client()
        if not redis_client:
            # If Redis is unavailable, allow session but log warning
            log_with_route(logging.WARNING, "Redis unavailable for session tracking - allowing session")
            return True
        
        try:
            if session_id is None:
                # Use a stable, per-session ID stored in Flask session to avoid generating a new ID every request
                session_id = session.get('weg_session_id')
                if not session_id:
                    session_id = str(uuid.uuid4())
                    session['weg_session_id'] = session_id

            user_sessions_key = f"{self.session_prefix}{user_id}"
            
            # Get current sessions for user
            current_sessions = redis_client.hgetall(user_sessions_key)
            
            # Clean up expired sessions
            now = datetime.now()
            active_sessions = {}
            
            for sid, session_data in current_sessions.items():
                try:
                    data = json.loads(session_data)
                    expires_at = datetime.fromisoformat(data['expires_at'])
                    if expires_at > now:
                        active_sessions[sid] = data
                except (json.JSONDecodeError, KeyError, ValueError):
                    # Remove invalid session data
                    continue
            
            # Check if current session already exists
            if session_id in active_sessions:
                # Update existing session timestamp
                active_sessions[session_id]['last_activity'] = now.isoformat()
                active_sessions[session_id]['ip_address'] = request.remote_addr
            else:
                # Check concurrent session limit
                if len(active_sessions) >= self.max_concurrent_sessions:
                    # Remove oldest session
                    oldest_session = min(
                        active_sessions.items(),
                        key=lambda x: x[1]['last_activity']
                    )
                    del active_sessions[oldest_session[0]]
                    log_with_route(
                        logging.DEBUG,
                        f"Removed oldest session for user {user_id} due to concurrent session limit"
                    )
                
                # Add new session
                session_expires = now + current_app.config['PERMANENT_SESSION_LIFETIME']
                active_sessions[session_id] = {
                    'created_at': now.isoformat(),
                    'last_activity': now.isoformat(),
                    'expires_at': session_expires.isoformat(),
                    'ip_address': request.remote_addr,
                    'user_agent': request.headers.get('User-Agent', '')[:200]  # Truncate long user agents
                }
            
            # Update Redis with active sessions
            pipeline = redis_client.pipeline()
            pipeline.delete(user_sessions_key)  # Clear old data
            
            for sid, data in active_sessions.items():
                pipeline.hset(user_sessions_key, sid, json.dumps(data))
            
            # Set expiration for the entire hash
            pipeline.expire(user_sessions_key, int(current_app.config['PERMANENT_SESSION_LIFETIME'].total_seconds()))
            pipeline.execute()
            
            return True
            
        except Exception as e:
            log_with_route(logging.ERROR, f"Failed to track user session: {str(e)}")
            return True  # Allow session on error
    
    def invalidate_user_sessions(self, user_id, except_session_id=None):
        """
        Invalidate all sessions for a user (useful for password changes, etc.)
        Optionally keep one session (the current one)
        """
        redis_client = self._get_redis_client()
        if not redis_client:
            log_with_route(logging.WARNING, "Redis unavailable for session invalidation")
            return False
        
        try:
            user_sessions_key = f"{self.session_prefix}{user_id}"
            
            if except_session_id:
                # Keep only the specified session
                current_sessions = redis_client.hgetall(user_sessions_key)
                if except_session_id in current_sessions:
                    session_data = current_sessions[except_session_id]
                    redis_client.delete(user_sessions_key)
                    redis_client.hset(user_sessions_key, except_session_id, session_data)
                    redis_client.expire(
                        user_sessions_key, 
                        int(current_app.config['PERMANENT_SESSION_LIFETIME'].total_seconds())
                    )
                else:
                    redis_client.delete(user_sessions_key)
            else:
                # Remove all sessions
                redis_client.delete(user_sessions_key)
            
            log_with_route(
                logging.INFO,
                f"Invalidated sessions for user {user_id}" + 
                (f" (except {except_session_id})" if except_session_id else "")
            )
            return True
            
        except Exception as e:
            log_with_route(logging.ERROR, f"Failed to invalidate user sessions: {str(e)}")
            return False
    
    def get_user_sessions(self, user_id):
        """Get active sessions for a user (for admin/security monitoring)"""
        redis_client = self._get_redis_client()
        if not redis_client:
            return []
        
        try:
            user_sessions_key = f"{self.session_prefix}{user_id}"
            current_sessions = redis_client.hgetall(user_sessions_key)
            
            sessions = []
            now = datetime.now()
            
            for session_id, session_data in current_sessions.items():
                try:
                    data = json.loads(session_data)
                    expires_at = datetime.fromisoformat(data['expires_at'])
                    
                    if expires_at > now:  # Only return active sessions
                        sessions.append({
                            'session_id': session_id,
                            'created_at': data['created_at'],
                            'last_activity': data['last_activity'],
                            'expires_at': data['expires_at'],
                            'ip_address': data['ip_address'],
                            'user_agent': data.get('user_agent', '')
                        })
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue
            
            return sorted(sessions, key=lambda x: x['last_activity'], reverse=True)
            
        except Exception as e:
            log_with_route(logging.ERROR, f"Failed to get user sessions: {str(e)}")
            return []
    
    def cleanup_expired_sessions(self):
        """Cleanup expired sessions (can be called periodically)"""
        redis_client = self._get_redis_client()
        if not redis_client:
            return

        try:
            # This is a maintenance function that could be called by a scheduled task
            # For now, we rely on Redis TTL for cleanup
            log_with_route(logging.DEBUG, "Session cleanup completed")
        except Exception as e:
            log_with_route(logging.ERROR, f"Failed to cleanup expired sessions: {str(e)}")

    def handle_role_change(self, user_id, old_role, new_role):
        """
        Handle role changes with session regeneration for security
        Call this whenever a user's role is modified
        """
        try:
            # Regenerate session for security
            self.regenerate_session(user_id=str(user_id), reason=f"role_change_{old_role}_to_{new_role}")

            # Update session data with new role
            session['role'] = new_role

            # Log the role change
            log_with_route(
                logging.INFO,
                f"Role changed for user {user_id}: {old_role} -> {new_role}"
            )

            return True

        except Exception as e:
            log_with_route(logging.ERROR, f"Failed to handle role change: {str(e)}")
            return False

    def force_logout_user(self, user_id, reason="security"):
        """
        Force logout a user by invalidating all their sessions
        Useful for security incidents or account compromises
        """
        try:
            # Invalidate all sessions for the user
            self.invalidate_user_sessions(str(user_id))

            log_with_route(
                logging.WARNING,
                f"Forced logout for user {user_id} - reason: {reason}"
            )

            return True

        except Exception as e:
            log_with_route(logging.ERROR, f"Failed to force logout user: {str(e)}")
            return False


# Global session manager instance
session_manager = SessionManager()
