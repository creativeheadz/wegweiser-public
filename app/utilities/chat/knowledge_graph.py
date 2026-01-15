from typing import Dict, Any, List, Optional
from app.models import (
    db, DeviceStatus, DeviceDrives, DeviceMemory, 
    DeviceNetworks, DeviceCpu, DeviceGpu, Devices
)
import logging
import time

class KnowledgeGraph:
    """Knowledge graph for querying device information"""
    
    def __init__(self, device_uuid: str):
        self.device_uuid = device_uuid
        self._cache = {}  # Add cache
        self._cache_timestamps = {}  # Track when each cache entry was created
        self._cache_ttl = 30  # Cache time-to-live in seconds

    def query(self, query_type: str, force_refresh: bool = False) -> dict:
        """Query device information based on type with caching"""
        query_type = query_type.lower()
        
        # Add debug logging with stack trace
        logging.debug(f"KnowledgeGraph query called for type '{query_type}' from:", stack_info=True)
        
        # Special handling for health-related queries
        if 'health' in query_type or 'score' in query_type:
            return self._get_health_info(force_refresh=True)
        
        # Check if cache entry is expired
        current_time = time.time()
        is_expired = (
            query_type in self._cache_timestamps and 
            current_time - self._cache_timestamps.get(query_type, 0) > self._cache_ttl
        )
        
        # Check cache first if not expired and not forcing refresh
        if query_type in self._cache and not is_expired and not force_refresh:
            logging.debug(f"Returning cached result for {query_type}")
            return self._cache[query_type]
        
        try:
            result = None
            if 'storage' in query_type:
                result = self._get_storage_info()
            elif 'gpu' in query_type or 'graphics' in query_type:
                result = self._get_gpu_info()
            elif 'memory' in query_type or 'ram' in query_type:
                result = self._get_memory_info()
            elif 'network' in query_type:
                result = self._get_network_info()
            elif 'system' in query_type or 'cpu' in query_type:
                result = self._get_system_info()
            else:
                return {"error": f"Unknown query type: {query_type}"}

            # Cache successful results
            if result and 'error' not in result:
                logging.debug(f"Caching result for {query_type}")
                self._cache[query_type] = result
                self._cache_timestamps[query_type] = current_time
            return result

        except Exception as e:
            logging.error(f"Error querying device info: {str(e)}")
            return {"error": str(e)}

    def clear_cache(self, query_type: Optional[str] = None) -> None:
        """Clear the entire cache or just a specific query type"""
        if query_type:
            if query_type in self._cache:
                del self._cache[query_type]
                if query_type in self._cache_timestamps:
                    del self._cache_timestamps[query_type]
                logging.debug(f"Cleared cache entry for {query_type}")
        else:
            self._cache = {}
            self._cache_timestamps = {}
            logging.debug("Cleared entire knowledge graph cache")

    def _get_health_info(self, force_refresh: bool = False) -> dict:
        """Get health-related information with optional cache bypass"""
        cache_key = 'health'
        current_time = time.time()
        is_expired = (
            cache_key in self._cache_timestamps and 
            current_time - self._cache_timestamps.get(cache_key, 0) > self._cache_ttl
        )
        
        if not force_refresh and cache_key in self._cache and not is_expired:
            return self._cache[cache_key]
        
        device = Devices.query.get(self.device_uuid)
        if not device:
            return {"error": "Device not found"}
        
        # Get the latest health score from database
        db.session.refresh(device)  # Ensure we have the latest data
        
        result = {
            "type": "health",
            "health_score": device.health_score,
            "health_score_formatted": f"{device.health_score:.1f}%",
            "last_updated": getattr(device, 'health_score_updated_at', current_time)
        }
        
        # Cache the result
        self._cache[cache_key] = result
        self._cache_timestamps[cache_key] = current_time
        
        return result

    def _get_storage_info(self) -> dict:
        """Get storage information"""
        drives = DeviceDrives.query.filter_by(deviceuuid=self.device_uuid).all()
        if not drives:
            return {"error": "No storage information available"}
            
        return {
            "type": "storage",
            "drives": [{
                "name": drive.drive_name,
                "total_gb": round(drive.drive_total / (1024**3), 2),
                "used_gb": round(drive.drive_used / (1024**3), 2),
                "free_gb": round(drive.drive_free / (1024**3), 2),
                "used_percentage": drive.drive_used_percentage
            } for drive in drives]
        }

    def _get_system_info(self) -> dict:
        """Get system information"""
        status = DeviceStatus.query.filter_by(deviceuuid=self.device_uuid).first()
        cpu = DeviceCpu.query.filter_by(deviceuuid=self.device_uuid).first()
        
        if not status:
            return {"error": "No system information available"}
        
        # Parse CPU name for additional details if available
        cpu_details = {
            "count": status.cpu_count,
            "usage": status.cpu_usage,
            "name": "Unknown",
            "manufacturer": "Unknown",
            "model": "Unknown",
            "speed": "Unknown",
            "cores": status.cpu_count,
            "last_update": None
        }
        
        if cpu and cpu.cpu_name:
            cpu_details["name"] = cpu.cpu_name
            cpu_details["last_update"] = cpu.last_update
            
            # Try to parse detailed info from CPU name
            # Example: "Intel(R) Core(TM) i7-9700K CPU @ 3.60GHz"
            try:
                name_parts = cpu.cpu_name.split()
                if "Intel" in cpu.cpu_name:
                    cpu_details["manufacturer"] = "Intel"
                    # Try to extract model and speed
                    for part in name_parts:
                        if "i" in part and "-" in part:  # e.g., "i7-9700K"
                            cpu_details["model"] = part
                        if "GHz" in part:  # e.g., "3.60GHz"
                            cpu_details["speed"] = part.strip("@").strip()
                elif "AMD" in cpu.cpu_name:
                    cpu_details["manufacturer"] = "AMD"
                    # Add AMD-specific parsing if needed
            except Exception as e:
                logging.warning(f"Could not parse detailed CPU info: {str(e)}")
        
        return {
            "type": "system",
            "platform": status.agent_platform,
            "name": status.system_name,
            "manufacturer": status.system_manufacturer,
            "model": status.system_model,
            "cpu": cpu_details,
            "boot_time": status.boot_time
        }

    def _get_memory_info(self) -> dict:
        """Get memory information"""
        logging.info(f"Querying memory info for device: {self.device_uuid}")
        memory = DeviceMemory.query.filter_by(deviceuuid=self.device_uuid).first()
        
        if not memory:
            logging.warning(f"No memory information found for device {self.device_uuid}")
            return {"error": "No memory information available"}
        
        # Log raw values from database
        logging.info(f"Raw memory values from DB: total={memory.total_memory}, "
                    f"used={memory.used_memory}, free={memory.free_memory}")
            
        result = {
            "type": "memory",
            "total_gb": round(memory.total_memory / (1024**3), 2),
            "used_gb": round(memory.used_memory / (1024**3), 2),
            "free_gb": round(memory.free_memory / (1024**3), 2),
            "used_percentage": memory.mem_used_percent
        }
        
        # Log converted values
        logging.info(f"Converted memory values: {result}")
        return result

    def _get_network_info(self) -> dict:
        """Get network information"""
        networks = DeviceNetworks.query.filter_by(deviceuuid=self.device_uuid).all()
        if not networks:
            return {"error": "No network information available"}
            
        return {
            "type": "network",
            "interfaces": [{
                "name": net.network_name,
                "status": "up" if net.if_is_up else "down",
                "speed": net.if_speed,
                "bytes_sent": net.bytes_sent,
                "bytes_received": net.bytes_rec,
                "errors_in": net.err_in,
                "errors_out": net.err_out
            } for net in networks]
        }

    def _get_gpu_info(self) -> dict:
        """Get GPU information"""
        gpu = DeviceGpu.query.filter_by(deviceuuid=self.device_uuid).first()
        if not gpu:
            return {"error": "No GPU information available"}
            
        return {
            "type": "gpu",
            "vendor": gpu.gpu_vendor,
            "product": gpu.gpu_product,
            "resolution": f"{gpu.gpu_hres}x{gpu.gpu_vres}",
            "color_depth": gpu.gpu_colour
        }
