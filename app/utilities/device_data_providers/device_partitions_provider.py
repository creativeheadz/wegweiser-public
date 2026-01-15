# Filepath: app/utilities/device_data_providers/device_partitions_provider.py
"""
Device Partitions Provider

Handles fetching device partition information including disk partitions,
mount points, and partition usage statistics.
"""

from typing import Dict, Any, Optional, List
from app.models import db, DevicePartitions
from .base_provider import BaseDeviceDataProvider


class DevicePartitionsProvider(BaseDeviceDataProvider):
    """
    Provider for device partition information including disk partitions,
    mount points, and usage statistics.
    """
    
    def get_component_name(self) -> str:
        return "partitions"
    
    def get_data(self) -> Optional[Dict[str, Any]]:
        """
        Fetch device partitions information using ORM.
        
        Returns:
            Dictionary containing partitions data or None if not found
        """
        if not self.validate_uuids():
            return None
        
        try:
            partitions = db.session.query(DevicePartitions)\
                .filter(DevicePartitions.deviceuuid == self.deviceuuid)\
                .all()
            
            if not partitions:
                self.log_debug("No partitions data found")
                return None
            
            # Build the partitions data structure
            partitions_data = {
                'partitions': [],
                'partition_count': len(partitions),
                'total_size': 0,
                'total_used': 0,
                'total_free': 0,
                'system_partitions': 0,
                'data_partitions': 0,
                'summary': self._get_partitions_summary(partitions),
            }
            
            for partition in partitions:
                # Calculate derived fields
                is_system_partition = self._is_system_partition(partition)

                partition_info = {
                    'partition_name': partition.partition_name,
                    'partition_device': partition.partition_device,
                    'partition_fs_type': partition.partition_fs_type,
                    'last_update': partition.last_update,
                    'last_json': partition.last_json,

                    # Derived fields
                    'is_system_partition': is_system_partition,

                    # Formatted data
                    'last_update_formatted': self.format_timestamp(partition.last_update),
                    'partition_summary': self._get_partition_summary(partition),
                }

                partitions_data['partitions'].append(partition_info)

                # Note: partition_size, partition_used, partition_free fields don't exist in current database schema
                # Only partition_name, partition_device, partition_fs_type are available

                # Count partition types
                if is_system_partition:
                    partitions_data['system_partitions'] += 1
                else:
                    partitions_data['data_partitions'] += 1
            
            # Add formatted totals
            partitions_data['total_size_gb'] = self._bytes_to_gb(partitions_data['total_size'])
            partitions_data['total_used_gb'] = self._bytes_to_gb(partitions_data['total_used'])
            partitions_data['total_free_gb'] = self._bytes_to_gb(partitions_data['total_free'])
            partitions_data['overall_usage_percent'] = self._calculate_overall_usage(partitions_data)
            
            self.log_debug(f"Successfully fetched data for {len(partitions)} partitions")
            return partitions_data
            
        except Exception as e:
            self.log_error(f"Error fetching partitions data: {str(e)}", exc_info=True)
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
    
    def _is_system_partition(self, partition: DevicePartitions) -> bool:
        """
        Determine if a partition is a system partition.
        
        Args:
            partition: DevicePartitions object
            
        Returns:
            True if it's a system partition, False otherwise
        """
        # Note: partition_bootable, partition_mountpoint, partition_type fields don't exist in current database schema
        # Only partition_name, partition_device, partition_fs_type are available

        # Use partition name or device to make a best guess
        if partition.partition_name:
            name = partition.partition_name.lower()
            if 'system' in name or 'boot' in name or 'c:' in name or 'windows' in name:
                return True

        if partition.partition_device:
            device = partition.partition_device.lower()
            if 'c:' in device or '/dev/sda1' in device or '/dev/nvme0n1p1' in device:
                return True
        
        return False
    
    def _get_partition_summary(self, partition: DevicePartitions) -> str:
        """
        Create a summary string for a partition.
        
        Args:
            partition: DevicePartitions object
            
        Returns:
            String summarizing partition information
        """
        parts = []
        
        if partition.partition_name:
            parts.append(partition.partition_name)
        elif partition.partition_device:
            parts.append(partition.partition_device)
        
        # Note: partition_mountpoint and partition_filesystem fields don't exist in current database schema
        # Only partition_fs_type is available

        if partition.partition_fs_type:
            parts.append(partition.partition_fs_type)
        
        # Note: partition_size field doesn't exist in current database schema
        # Only partition_name, partition_device, partition_fs_type are available
        
        # Note: partition_percent field doesn't exist in current database schema
        
        return " • ".join(parts) if parts else "Unknown Partition"
    
    def _get_partitions_summary(self, partitions: List[DevicePartitions]) -> str:
        """
        Create a summary string for all partitions.
        
        Args:
            partitions: List of DevicePartitions objects
            
        Returns:
            String summarizing all partitions
        """
        if not partitions:
            return "No partitions found"
        
        # Note: partition_size and partition_used fields don't exist in current database schema
        # Only partition_name, partition_device, partition_fs_type are available
        total_size = 0
        total_used = 0
        
        size_gb = self._bytes_to_gb(total_size)
        used_gb = self._bytes_to_gb(total_used)
        
        system_count = sum(1 for partition in partitions if self._is_system_partition(partition))
        data_count = len(partitions) - system_count
        
        parts = [f"{len(partitions)} partitions"]
        
        if size_gb and used_gb:
            usage_percent = (total_used / total_size) * 100 if total_size > 0 else 0
            parts.append(f"{size_gb} GB total")
            parts.append(f"{usage_percent:.1f}% used")
        
        if system_count > 0:
            parts.append(f"{system_count} system")
        
        if data_count > 0:
            parts.append(f"{data_count} data")
        
        return " • ".join(parts)
    
    def _calculate_overall_usage(self, partitions_data: Dict[str, Any]) -> Optional[float]:
        """
        Calculate overall usage percentage across all partitions.
        
        Args:
            partitions_data: Dictionary containing partitions data
            
        Returns:
            Overall usage percentage or None if cannot calculate
        """
        total_size = partitions_data.get('total_size', 0)
        total_used = partitions_data.get('total_used', 0)
        
        if total_size > 0:
            return round((total_used / total_size) * 100, 1)
        
        return None
    
    def get_partitions_summary(self) -> Optional[Dict[str, Any]]:
        """
        Get a summary of partitions information for dashboard display.
        
        Returns:
            Dictionary containing partitions summary or None if not found
        """
        data = self.get_data()
        if not data:
            return None
        
        return {
            'partition_count': data['partition_count'],
            'total_size_gb': data['total_size_gb'],
            'overall_usage_percent': data['overall_usage_percent'],
            'system_partitions': data['system_partitions'],
            'data_partitions': data['data_partitions'],
            'summary': data['summary'],
        }
