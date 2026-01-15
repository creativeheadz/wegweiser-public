# Filepath: app/utilities/device_data_providers/device_drives_provider.py
"""
Device Drives Provider

Handles fetching device drive information including disk drives,
storage capacity, and usage statistics.
"""

from typing import Dict, Any, Optional, List
from app.models import db, DeviceDrives
from .base_provider import BaseDeviceDataProvider


class DeviceDrivesProvider(BaseDeviceDataProvider):
    """
    Provider for device drive information including storage devices,
    capacity, usage, and drive health.
    """
    
    def get_component_name(self) -> str:
        return "drives"
    
    def get_data(self) -> Optional[Dict[str, Any]]:
        """
        Fetch device drives information using ORM.
        
        Returns:
            Dictionary containing drives data or None if not found
        """
        if not self.validate_uuids():
            return None
        
        try:
            drives = db.session.query(DeviceDrives)\
                .filter(DeviceDrives.deviceuuid == self.deviceuuid)\
                .all()
            
            if not drives:
                self.log_debug("No drives data found")
                return None
            
            # Build the drives data structure
            drives_data = {
                'drives': [],
                'total_capacity': 0,
                'total_used': 0,
                'total_free': 0,
                'drive_count': len(drives),
                'summary': self._get_drives_summary(drives),
            }
            
            for drive in drives:
                drive_info = {
                    'drive_name': drive.drive_name,
                    'drive_total': drive.drive_total,
                    'drive_used': drive.drive_used,
                    'drive_free': drive.drive_free,
                    'drive_used_percentage': drive.drive_used_percentage,
                    'drive_free_percentage': drive.drive_free_percentage,
                    'last_update': drive.last_update,
                    'last_json': drive.last_json,

                    # Formatted data
                    'last_update_formatted': self.format_timestamp(drive.last_update),
                    'drive_total_gb': self._bytes_to_gb(drive.drive_total),
                    'drive_used_gb': self._bytes_to_gb(drive.drive_used),
                    'drive_free_gb': self._bytes_to_gb(drive.drive_free),
                    'usage_status': self._get_usage_status(drive.drive_used_percentage),
                    'drive_summary': self._get_drive_summary(drive),
                }
                
                drives_data['drives'].append(drive_info)
                
                # Accumulate totals
                if drive.drive_total:
                    drives_data['total_capacity'] += drive.drive_total
                if drive.drive_used:
                    drives_data['total_used'] += drive.drive_used
                if drive.drive_free:
                    drives_data['total_free'] += drive.drive_free
            
            # Add formatted totals
            drives_data['total_capacity_gb'] = self._bytes_to_gb(drives_data['total_capacity'])
            drives_data['total_used_gb'] = self._bytes_to_gb(drives_data['total_used'])
            drives_data['total_free_gb'] = self._bytes_to_gb(drives_data['total_free'])
            drives_data['overall_usage_percent'] = self._calculate_overall_usage(drives_data)
            
            self.log_debug(f"Successfully fetched data for {len(drives)} drives")
            return drives_data
            
        except Exception as e:
            self.log_error(f"Error fetching drives data: {str(e)}", exc_info=True)
            return None
    
    def _bytes_to_gb(self, bytes_value: Optional[int]) -> Optional[float]:
        """
        Convert bytes to gigabytes.
        
        Args:
            bytes_value: Value in bytes
            
        Returns:
            Value in GB rounded to 2 decimal places, or None if input is None
        """
        if bytes_value is None:
            return None
        
        try:
            return round(bytes_value / (1024 ** 3), 2)
        except (TypeError, ZeroDivisionError):
            return None
    
    def _get_usage_status(self, usage_percent: Optional[float]) -> str:
        """
        Determine usage status based on percentage.
        
        Args:
            usage_percent: Usage percentage
            
        Returns:
            String describing usage status
        """
        if usage_percent is None:
            return "Unknown"
        
        if usage_percent >= 95:
            return "Critical"
        elif usage_percent >= 85:
            return "High"
        elif usage_percent >= 70:
            return "Moderate"
        else:
            return "Normal"
    
    def _get_drive_summary(self, drive: DeviceDrives) -> str:
        """
        Create a summary string for a drive.
        
        Args:
            drive: DeviceDrives object
            
        Returns:
            String summarizing drive information
        """
        parts = []
        
        if drive.drive_name:
            parts.append(drive.drive_name)
        
        # Note: drive_type field doesn't exist in current database schema
        # Only drive_name, drive_total, drive_used, drive_free, drive_used_percentage, drive_free_percentage are available

        if drive.drive_total:
            total_gb = self._bytes_to_gb(drive.drive_total)
            if total_gb:
                parts.append(f"{total_gb} GB")

        if drive.drive_used_percentage:
            parts.append(f"{drive.drive_used_percentage:.1f}% used")
        
        return " • ".join(parts) if parts else "Unknown Drive"
    
    def _get_drives_summary(self, drives: List[DeviceDrives]) -> str:
        """
        Create a summary string for all drives.
        
        Args:
            drives: List of DeviceDrives objects
            
        Returns:
            String summarizing all drives
        """
        if not drives:
            return "No drives found"
        
        total_capacity = sum(drive.drive_total or 0 for drive in drives)
        total_used = sum(drive.drive_used or 0 for drive in drives)
        
        capacity_gb = self._bytes_to_gb(total_capacity)
        used_gb = self._bytes_to_gb(total_used)
        
        if capacity_gb and used_gb:
            usage_percent = (total_used / total_capacity) * 100 if total_capacity > 0 else 0
            return f"{len(drives)} drives • {capacity_gb} GB total • {usage_percent:.1f}% used"
        else:
            return f"{len(drives)} drives"
    
    def _calculate_overall_usage(self, drives_data: Dict[str, Any]) -> Optional[float]:
        """
        Calculate overall usage percentage across all drives.
        
        Args:
            drives_data: Dictionary containing drives data
            
        Returns:
            Overall usage percentage or None if cannot calculate
        """
        total_capacity = drives_data.get('total_capacity', 0)
        total_used = drives_data.get('total_used', 0)
        
        if total_capacity > 0:
            return round((total_used / total_capacity) * 100, 1)
        
        return None
    
    def get_drives_summary(self) -> Optional[Dict[str, Any]]:
        """
        Get a summary of drives information for dashboard display.
        
        Returns:
            Dictionary containing drives summary or None if not found
        """
        data = self.get_data()
        if not data:
            return None
        
        return {
            'drive_count': data['drive_count'],
            'total_capacity_gb': data['total_capacity_gb'],
            'overall_usage_percent': data['overall_usage_percent'],
            'summary': data['summary'],
        }
