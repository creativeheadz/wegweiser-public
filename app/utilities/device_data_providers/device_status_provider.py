# Filepath: app/utilities/device_data_providers/device_status_provider.py
"""
Device Status Provider

Handles fetching device status information including system information,
performance metrics, and current operational status.
"""

from typing import Dict, Any, Optional
from app.models import db, DeviceStatus
from .base_provider import BaseDeviceDataProvider


class DeviceStatusProvider(BaseDeviceDataProvider):
    """
    Provider for device status information including system details,
    performance metrics, and operational status.
    """
    
    def get_component_name(self) -> str:
        return "status"
    
    def get_data(self) -> Optional[Dict[str, Any]]:
        """
        Fetch device status information using ORM.
        
        Returns:
            Dictionary containing device status data or None if not found
        """
        if not self.validate_uuids():
            return None
        
        try:
            status = db.session.query(DeviceStatus)\
                .filter(DeviceStatus.deviceuuid == self.deviceuuid)\
                .first()
            
            if not status:
                self.log_debug("No status data found")
                return None
            
            # Build the status data structure
            status_data = {
                'agent_platform': status.agent_platform,
                'system_name': status.system_name,
                'logged_on_user': status.logged_on_user,
                'last_update': status.last_update,
                'last_json': status.last_json,
                
                # Performance metrics
                'cpu_usage': status.cpu_usage,
                'cpu_count': status.cpu_count,
                'boot_time': status.boot_time,
                
                # Network information
                'publicIp': status.publicIp,
                'country': status.country,
                
                # System information
                'system_model': status.system_model,
                'system_manufacturer': status.system_manufacturer,
                'system_locale': status.system_locale,
                
                # Formatted timestamps
                'last_update_formatted': self.format_timestamp(status.last_update),
                'boot_time_formatted': self.format_timestamp(status.boot_time),
            }
            
            self.log_debug(f"Successfully fetched status data")
            return status_data
            
        except Exception as e:
            self.log_error(f"Error fetching device status: {str(e)}", exc_info=True)
            return None
    
    def get_performance_metrics(self) -> Optional[Dict[str, Any]]:
        """
        Get only performance-related metrics.
        
        Returns:
            Dictionary containing performance metrics or None if not found
        """
        if not self.validate_uuids():
            return None
        
        try:
            status = db.session.query(DeviceStatus)\
                .filter(DeviceStatus.deviceuuid == self.deviceuuid)\
                .first()
            
            if not status:
                return None
            
            return {
                'cpu_usage': status.cpu_usage,
                'cpu_count': status.cpu_count,
                'boot_time': status.boot_time,
                'boot_time_formatted': self.format_timestamp(status.boot_time),
            }
            
        except Exception as e:
            self.log_error(f"Error fetching performance metrics: {str(e)}", exc_info=True)
            return None
    
    def get_system_info(self) -> Optional[Dict[str, Any]]:
        """
        Get only system information.
        
        Returns:
            Dictionary containing system information or None if not found
        """
        if not self.validate_uuids():
            return None
        
        try:
            status = db.session.query(DeviceStatus)\
                .filter(DeviceStatus.deviceuuid == self.deviceuuid)\
                .first()
            
            if not status:
                return None
            
            return {
                'agent_platform': status.agent_platform,
                'system_name': status.system_name,
                'system_model': status.system_model,
                'system_manufacturer': status.system_manufacturer,
                'system_locale': status.system_locale,
                'logged_on_user': status.logged_on_user,
                'publicIp': status.publicIp,
                'country': status.country,
            }
            
        except Exception as e:
            self.log_error(f"Error fetching system info: {str(e)}", exc_info=True)
            return None
