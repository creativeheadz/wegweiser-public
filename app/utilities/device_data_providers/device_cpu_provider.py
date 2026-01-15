# Filepath: app/utilities/device_data_providers/device_cpu_provider.py
"""
Device CPU Provider

Handles fetching device CPU information including processor details,
core count, and CPU specifications.
"""

from typing import Dict, Any, Optional
from app.models import db, DeviceCpu
from .base_provider import BaseDeviceDataProvider


class DeviceCpuProvider(BaseDeviceDataProvider):
    """
    Provider for device CPU information including processor name,
    core count, and CPU specifications.
    """
    
    def get_component_name(self) -> str:
        return "cpu"
    
    def get_data(self) -> Optional[Dict[str, Any]]:
        """
        Fetch device CPU information using ORM.
        
        Returns:
            Dictionary containing CPU data or None if not found
        """
        if not self.validate_uuids():
            return None
        
        try:
            cpu = db.session.query(DeviceCpu)\
                .filter(DeviceCpu.deviceuuid == self.deviceuuid)\
                .first()
            
            if not cpu:
                self.log_debug("No CPU data found")
                return None
            
            # Build the CPU data structure
            cpu_data = {
                'cpu_name': cpu.cpu_name,
                'last_update': cpu.last_update,
                'last_json': cpu.last_json,
                'cpu_metrics_json': cpu.cpu_metrics_json,

                # Formatted data
                'last_update_formatted': self.format_timestamp(cpu.last_update),
                'cpu_summary': self._get_cpu_summary(cpu),
            }

            self.log_debug(f"Successfully fetched CPU data")
            return cpu_data
            
        except Exception as e:
            self.log_error(f"Error fetching CPU data: {str(e)}", exc_info=True)
            return None
    
    def _hz_to_ghz(self, hz_value: Optional[int]) -> Optional[float]:
        """
        Convert Hz to GHz.
        
        Args:
            hz_value: Value in Hz
            
        Returns:
            Value in GHz rounded to 2 decimal places, or None if input is None
        """
        if hz_value is None:
            return None
        
        try:
            return round(hz_value / (1000 ** 3), 2)
        except (TypeError, ZeroDivisionError):
            return None
    
    def _get_cpu_summary(self, cpu: DeviceCpu) -> str:
        """
        Create a summary string for the CPU.
        
        Args:
            cpu: DeviceCpu object
            
        Returns:
            String summarizing CPU specifications
        """
        parts = []
        
        if cpu.cpu_name:
            parts.append(cpu.cpu_name)
        
        # Note: Only cpu_name is available in the current database schema
        
        return " • ".join(parts) if parts else "Unknown CPU"
    
    def get_cpu_summary(self) -> Optional[Dict[str, Any]]:
        """
        Get a summary of CPU information for dashboard display.
        
        Returns:
            Dictionary containing CPU summary or None if not found
        """
        if not self.validate_uuids():
            return None
        
        try:
            cpu = db.session.query(DeviceCpu)\
                .filter(DeviceCpu.deviceuuid == self.deviceuuid)\
                .first()
            
            if not cpu:
                return None
            
            return {
                'name': cpu.cpu_name,
                'summary': self._get_cpu_summary(cpu),
                'last_update': self.format_timestamp(cpu.last_update),
            }
            
        except Exception as e:
            self.log_error(f"Error fetching CPU summary: {str(e)}", exc_info=True)
            return None
