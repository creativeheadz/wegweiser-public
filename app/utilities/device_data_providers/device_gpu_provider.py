# Filepath: app/utilities/device_data_providers/device_gpu_provider.py
"""
Device GPU Provider

Handles fetching device GPU information including graphics card details,
vendor information, and GPU specifications.
"""

from typing import Dict, Any, Optional
from app.models import db, DeviceGpu
from .base_provider import BaseDeviceDataProvider


class DeviceGpuProvider(BaseDeviceDataProvider):
    """
    Provider for device GPU information including graphics card name,
    vendor, and GPU specifications.
    """
    
    def get_component_name(self) -> str:
        return "gpu"
    
    def get_data(self) -> Optional[Dict[str, Any]]:
        """
        Fetch device GPU information using ORM.
        
        Returns:
            Dictionary containing GPU data or None if not found
        """
        if not self.validate_uuids():
            return None
        
        try:
            gpu = db.session.query(DeviceGpu)\
                .filter(DeviceGpu.deviceuuid == self.deviceuuid)\
                .first()
            
            if not gpu:
                self.log_debug("No GPU data found")
                return None
            
            # Build the GPU data structure
            gpu_data = {
                'gpu_vendor': gpu.gpu_vendor,
                'gpu_product': gpu.gpu_product,
                'gpu_colour': gpu.gpu_colour,
                'gpu_hres': gpu.gpu_hres,
                'gpu_vres': gpu.gpu_vres,
                'last_update': gpu.last_update,
                'last_json': gpu.last_json,

                # Formatted data
                'last_update_formatted': self.format_timestamp(gpu.last_update),
                'gpu_summary': self._get_gpu_summary(gpu),
                'gpu_display_info': self._get_display_info(gpu),
            }
            
            self.log_debug(f"Successfully fetched GPU data")
            return gpu_data
            
        except Exception as e:
            self.log_error(f"Error fetching GPU data: {str(e)}", exc_info=True)
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
    
    def _get_gpu_summary(self, gpu: DeviceGpu) -> str:
        """
        Create a summary string for the GPU.
        
        Args:
            gpu: DeviceGpu object
            
        Returns:
            String summarizing GPU specifications
        """
        parts = []
        
        if gpu.gpu_vendor:
            parts.append(gpu.gpu_vendor)
        
        if gpu.gpu_product:
            parts.append(gpu.gpu_product)
        
        # Note: gpu_memory field doesn't exist in current database schema
        # Only gpu_vendor, gpu_product, gpu_colour, gpu_hres, gpu_vres are available

        if gpu.gpu_hres and gpu.gpu_vres:
            parts.append(f"{gpu.gpu_hres}x{gpu.gpu_vres}")

        if gpu.gpu_colour:
            parts.append(f"{gpu.gpu_colour}-bit")
        
        return " • ".join(parts) if parts else "Unknown GPU"
    
    def _get_display_info(self, gpu: DeviceGpu) -> Dict[str, Any]:
        """
        Extract display information from GPU data.
        
        Args:
            gpu: DeviceGpu object
            
        Returns:
            Dictionary containing display information
        """
        # Note: gpu_resolution, gpu_refresh_rate, gpu_driver_version fields don't exist in current database schema
        # Only gpu_hres, gpu_vres, gpu_colour are available
        resolution = None
        if gpu.gpu_hres and gpu.gpu_vres:
            resolution = f"{gpu.gpu_hres}x{gpu.gpu_vres}"

        return {
            'resolution': resolution,
            'color_depth': gpu.gpu_colour if hasattr(gpu, 'gpu_colour') else None,
        }
    
    def get_gpu_summary(self) -> Optional[Dict[str, Any]]:
        """
        Get a summary of GPU information for dashboard display.
        
        Returns:
            Dictionary containing GPU summary or None if not found
        """
        if not self.validate_uuids():
            return None
        
        try:
            gpu = db.session.query(DeviceGpu)\
                .filter(DeviceGpu.deviceuuid == self.deviceuuid)\
                .first()
            
            if not gpu:
                return None
            
            return {
                'vendor': gpu.gpu_vendor,
                'product': gpu.gpu_product,
                'memory_gb': self._bytes_to_gb(gpu.gpu_memory),
                'resolution': gpu.gpu_resolution,
                'summary': self._get_gpu_summary(gpu),
                'last_update': self.format_timestamp(gpu.last_update),
            }
            
        except Exception as e:
            self.log_error(f"Error fetching GPU summary: {str(e)}", exc_info=True)
            return None
