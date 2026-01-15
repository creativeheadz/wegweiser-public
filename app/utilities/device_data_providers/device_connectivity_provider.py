# Filepath: app/utilities/device_data_providers/device_connectivity_provider.py
"""
Device Connectivity Provider

Handles fetching device connectivity information including online status,
connection history, and heartbeat data.
"""

from typing import Dict, Any, Optional
from app.models import db, DeviceConnectivity
from .base_provider import BaseDeviceDataProvider


class DeviceConnectivityProvider(BaseDeviceDataProvider):
    """
    Provider for device connectivity information including online status,
    connection history, and agent information.
    """
    
    def get_component_name(self) -> str:
        return "connectivity"
    
    def get_data(self) -> Optional[Dict[str, Any]]:
        """
        Fetch device connectivity information using ORM.
        
        Returns:
            Dictionary containing connectivity data or None if not found
        """
        if not self.validate_uuids():
            return None
        
        try:
            connectivity = db.session.query(DeviceConnectivity)\
                .filter(DeviceConnectivity.deviceuuid == self.deviceuuid)\
                .first()
            
            if not connectivity:
                self.log_debug("No connectivity data found")
                return None
            
            # Build the connectivity data structure
            connectivity_data = {
                'is_online': connectivity.is_online,
                'last_online_change': connectivity.last_online_change,
                'last_seen_online': connectivity.last_seen_online,
                'last_heartbeat': connectivity.last_heartbeat,
                'agent_version': connectivity.agent_version,
                'connection_type': connectivity.connection_type,
                'connection_info': connectivity.connection_info,
                
                # Formatted data
                'last_online_change_formatted': self.format_timestamp(connectivity.last_online_change),
                'last_seen_online_formatted': self.format_timestamp(connectivity.last_seen_online),
                'last_heartbeat_formatted': self.format_timestamp(connectivity.last_heartbeat),
                'status': self._get_connection_status(connectivity),
                'connection_quality': self._get_connection_quality(connectivity),
            }
            
            self.log_debug(f"Successfully fetched connectivity data")
            return connectivity_data
            
        except Exception as e:
            self.log_error(f"Error fetching connectivity data: {str(e)}", exc_info=True)
            return None
    
    def _get_connection_status(self, connectivity: DeviceConnectivity) -> str:
        """
        Determine the connection status.
        
        Args:
            connectivity: DeviceConnectivity object
            
        Returns:
            String describing connection status
        """
        if connectivity.is_online:
            return "Online"
        else:
            return "Offline"
    
    def _get_connection_quality(self, connectivity: DeviceConnectivity) -> str:
        """
        Assess connection quality based on heartbeat data.
        
        Args:
            connectivity: DeviceConnectivity object
            
        Returns:
            String describing connection quality
        """
        if not connectivity.is_online:
            return "Disconnected"
        
        if connectivity.last_heartbeat is None:
            return "Unknown"
        
        import time
        current_time = int(time.time())
        heartbeat_age = current_time - connectivity.last_heartbeat
        
        # Assess quality based on heartbeat recency
        if heartbeat_age <= 60:  # Within 1 minute
            return "Excellent"
        elif heartbeat_age <= 300:  # Within 5 minutes
            return "Good"
        elif heartbeat_age <= 900:  # Within 15 minutes
            return "Fair"
        else:
            return "Poor"
    
    def is_online(self) -> bool:
        """
        Check if the device is currently online.
        
        Returns:
            True if device is online, False otherwise
        """
        try:
            connectivity = db.session.query(DeviceConnectivity)\
                .filter(DeviceConnectivity.deviceuuid == self.deviceuuid)\
                .first()
            
            return connectivity is not None and connectivity.is_online
            
        except Exception as e:
            self.log_error(f"Error checking online status: {str(e)}")
            return False
    
    def get_connection_summary(self) -> Optional[Dict[str, Any]]:
        """
        Get a summary of connection information for dashboard display.
        
        Returns:
            Dictionary containing connection summary or None if not found
        """
        if not self.validate_uuids():
            return None
        
        try:
            connectivity = db.session.query(DeviceConnectivity)\
                .filter(DeviceConnectivity.deviceuuid == self.deviceuuid)\
                .first()
            
            if not connectivity:
                return None
            
            return {
                'is_online': connectivity.is_online,
                'status': self._get_connection_status(connectivity),
                'quality': self._get_connection_quality(connectivity),
                'agent_version': connectivity.agent_version,
                'last_seen': self.format_timestamp(connectivity.last_seen_online),
            }
            
        except Exception as e:
            self.log_error(f"Error fetching connection summary: {str(e)}", exc_info=True)
            return None
