# Filepath: app/utilities/device_data_providers/device_memory_provider.py
"""
Device Memory Provider

Handles fetching device memory information including total memory,
usage statistics, and memory performance metrics.
"""

from typing import Dict, Any, Optional
from app.models import db, DeviceMemory
from .base_provider import BaseDeviceDataProvider


class DeviceMemoryProvider(BaseDeviceDataProvider):
    """
    Provider for device memory information including total memory,
    usage statistics, and performance metrics.
    """
    
    def get_component_name(self) -> str:
        return "memory"
    
    def get_data(self) -> Optional[Dict[str, Any]]:
        """
        Fetch device memory information using ORM.
        
        Returns:
            Dictionary containing memory data or None if not found
        """
        if not self.validate_uuids():
            return None
        
        try:
            memory = db.session.query(DeviceMemory)\
                .filter(DeviceMemory.deviceuuid == self.deviceuuid)\
                .first()
            
            if not memory:
                self.log_debug("No memory data found")
                return None
            
            # Build the memory data structure
            memory_data = {
                'total_memory': memory.total_memory,
                'available_memory': memory.available_memory,
                'used_memory': memory.used_memory,
                'free_memory': memory.free_memory,
                'cache_memory': memory.cache_memory,
                'mem_used_percent': memory.mem_used_percent,
                'mem_free_percent': memory.mem_free_percent,
                'last_update': memory.last_update,
                'last_json': memory.last_json,
                'memory_metrics_json': memory.memory_metrics_json,

                # Formatted data
                'last_update_formatted': self.format_timestamp(memory.last_update),
                'total_memory_gb': self._bytes_to_gb(memory.total_memory),
                'available_memory_gb': self._bytes_to_gb(memory.available_memory),
                'used_memory_gb': self._bytes_to_gb(memory.used_memory),
                'free_memory_gb': self._bytes_to_gb(memory.free_memory),
                'cache_memory_gb': self._bytes_to_gb(memory.cache_memory),
                'memory_status': self._get_memory_status(memory),
            }

            self.log_debug(f"Successfully fetched memory data")
            return memory_data
            
        except Exception as e:
            self.log_error(f"Error fetching memory data: {str(e)}", exc_info=True)
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
    
    def _get_memory_status(self, memory: DeviceMemory) -> str:
        """
        Determine memory status based on usage percentage.
        
        Args:
            memory: DeviceMemory object
            
        Returns:
            String describing memory status
        """
        if memory.mem_used_percent is None:
            return "Unknown"
        
        usage_percent = memory.mem_used_percent
        
        if usage_percent >= 90:
            return "Critical"
        elif usage_percent >= 80:
            return "High"
        elif usage_percent >= 60:
            return "Moderate"
        else:
            return "Normal"
    
    def get_memory_summary(self) -> Optional[Dict[str, Any]]:
        """
        Get a summary of memory information for dashboard display.
        
        Returns:
            Dictionary containing memory summary or None if not found
        """
        if not self.validate_uuids():
            return None
        
        try:
            memory = db.session.query(DeviceMemory)\
                .filter(DeviceMemory.deviceuuid == self.deviceuuid)\
                .first()
            
            if not memory:
                return None
            
            return {
                'total_gb': self._bytes_to_gb(memory.total_memory),
                'used_percent': memory.mem_used_percent,
                'status': self._get_memory_status(memory),
                'last_update': self.format_timestamp(memory.last_update),
            }
            
        except Exception as e:
            self.log_error(f"Error fetching memory summary: {str(e)}", exc_info=True)
            return None
