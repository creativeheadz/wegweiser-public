# Filepath: app/utilities/device_data_providers/device_users_provider.py
"""
Device Users Provider

Handles fetching device user information including user accounts,
login sessions, and user privileges.
"""

from typing import Dict, Any, Optional, List
from app.models import db, DeviceUsers
from .base_provider import BaseDeviceDataProvider


class DeviceUsersProvider(BaseDeviceDataProvider):
    """
    Provider for device user information including user accounts,
    login sessions, and user privileges.
    """
    
    def get_component_name(self) -> str:
        return "users"
    
    def get_data(self) -> Optional[Dict[str, Any]]:
        """
        Fetch device users information using ORM.
        
        Returns:
            Dictionary containing users data or None if not found
        """
        if not self.validate_uuids():
            return None
        
        try:
            users = db.session.query(DeviceUsers)\
                .filter(DeviceUsers.deviceuuid == self.deviceuuid)\
                .all()
            
            if not users:
                self.log_debug("No users data found")
                return None
            
            # Build the users data structure
            users_data = {
                'users': [],
                'user_count': len(users),
                'admin_users': 0,
                'standard_users': 0,
                'active_users': 0,
                'inactive_users': 0,
                'summary': self._get_users_summary(users),
            }
            
            for user in users:
                # Calculate derived fields
                is_admin = self._is_admin_user(user)
                is_active = self._is_active_user(user)

                user_info = {
                    'users_name': user.users_name,
                    'terminal': user.terminal,
                    'host': user.host,
                    'loggedin': user.loggedin,
                    'pid': user.pid,
                    'last_update': user.last_update,
                    'last_json': user.last_json,

                    # Derived fields
                    'is_admin': is_admin,
                    'is_active': is_active,

                    # Formatted data
                    'last_update_formatted': self.format_timestamp(user.last_update),
                    'loggedin_formatted': self.format_timestamp(user.loggedin) if user.loggedin else None,
                    'user_summary': self._get_user_summary(user),
                }

                users_data['users'].append(user_info)

                # Count user types
                if is_admin:
                    users_data['admin_users'] += 1
                else:
                    users_data['standard_users'] += 1

                if is_active:
                    users_data['active_users'] += 1
                else:
                    users_data['inactive_users'] += 1
            
            self.log_debug(f"Successfully fetched data for {len(users)} users")
            return users_data
            
        except Exception as e:
            self.log_error(f"Error fetching users data: {str(e)}", exc_info=True)
            return None
    
    def _is_admin_user(self, user: DeviceUsers) -> bool:
        """
        Determine if a user has administrative privileges.
        
        Args:
            user: DeviceUsers object
            
        Returns:
            True if user is an administrator, False otherwise
        """
        # Note: user_type and user_privileges fields don't exist in current database schema
        # Only users_name, terminal, host, loggedin, pid are available

        if user.users_name:
            username = user.users_name.lower()
            if username in ['administrator', 'admin', 'root']:
                return True
        
        return False
    
    def _is_active_user(self, user: DeviceUsers) -> bool:
        """
        Determine if a user account is active.
        
        Args:
            user: DeviceUsers object
            
        Returns:
            True if user is active, False otherwise
        """
        # Note: user_disabled field doesn't exist in current database schema
        # Use loggedin timestamp to determine if user is active

        # Check if user has a recent login timestamp
        if user.loggedin:
            return True

        # If no login timestamp, assume inactive
        return False
    
    def _get_account_status(self, user: DeviceUsers) -> str:
        """
        Get a descriptive account status.
        
        Args:
            user: DeviceUsers object
            
        Returns:
            String describing account status
        """
        # Note: user_disabled, user_locked, user_status fields don't exist in current database schema
        # Only users_name, terminal, host, loggedin, pid are available

        # Use loggedin timestamp to determine status
        if user.loggedin:
            return "Active"

        return "Inactive"
    
    def _get_user_summary(self, user: DeviceUsers) -> str:
        """
        Create a summary string for a user.
        
        Args:
            user: DeviceUsers object
            
        Returns:
            String summarizing user information
        """
        parts = []
        
        if user.users_name:
            parts.append(user.users_name)
        
        # Note: user_fullname field doesn't exist in current database schema
        # Only users_name, terminal, host, loggedin, pid are available
        
        if self._is_admin_user(user):
            parts.append("Administrator")
        
        account_status = self._get_account_status(user)
        if account_status != "Active":
            parts.append(account_status)
        
        # Use loggedin field instead of non-existent user_last_logon
        if user.loggedin:
            last_logon = self.format_timestamp(user.loggedin)
            if last_logon:
                parts.append(f"Last: {last_logon.split()[0]}")  # Just the date
        
        return " • ".join(parts) if parts else "Unknown User"
    
    def _get_users_summary(self, users: List[DeviceUsers]) -> str:
        """
        Create a summary string for all users.
        
        Args:
            users: List of DeviceUsers objects
            
        Returns:
            String summarizing all users
        """
        if not users:
            return "No users found"
        
        admin_count = sum(1 for user in users if self._is_admin_user(user))
        active_count = sum(1 for user in users if self._is_active_user(user))
        
        parts = [f"{len(users)} users"]
        
        if admin_count > 0:
            parts.append(f"{admin_count} admin")
        
        if active_count != len(users):
            parts.append(f"{active_count} active")
        
        return " • ".join(parts)
    
    def get_users_summary(self) -> Optional[Dict[str, Any]]:
        """
        Get a summary of users information for dashboard display.
        
        Returns:
            Dictionary containing users summary or None if not found
        """
        data = self.get_data()
        if not data:
            return None
        
        return {
            'user_count': data['user_count'],
            'admin_users': data['admin_users'],
            'standard_users': data['standard_users'],
            'active_users': data['active_users'],
            'inactive_users': data['inactive_users'],
            'summary': data['summary'],
        }
    
    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the currently logged-in user.
        
        Returns:
            Dictionary containing current user info or None if not found
        """
        data = self.get_data()
        if not data or not data['users']:
            return None
        
        # Look for user with most recent logon
        current_user = None
        latest_logon = 0
        
        for user in data['users']:
            if user.get('user_last_logon') and user['user_last_logon'] > latest_logon:
                latest_logon = user['user_last_logon']
                current_user = user
        
        return current_user
