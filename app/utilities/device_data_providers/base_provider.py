# Filepath: app/utilities/device_data_providers/base_provider.py
"""
Base Device Data Provider

Abstract base class that defines the interface for all device data providers.
Ensures consistency across all device component data fetchers.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from uuid import UUID
import logging
from app.utilities.app_logging_helper import log_with_route


class BaseDeviceDataProvider(ABC):
    """
    Abstract base class for all device data providers.
    
    Each provider should inherit from this class and implement the required methods.
    This ensures a consistent interface across all device data components.
    """
    
    def __init__(self, deviceuuid: str, tenantuuid: str):
        """
        Initialize the provider with device and tenant UUIDs.
        
        Args:
            deviceuuid: The device UUID as string
            tenantuuid: The tenant UUID as string
        """
        self.deviceuuid = deviceuuid
        self.tenantuuid = tenantuuid
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def get_data(self) -> Optional[Dict[str, Any]]:
        """
        Fetch and return the device data for this provider.
        
        Returns:
            Dictionary containing the device data, or None if no data found
        """
        pass
    
    @abstractmethod
    def get_component_name(self) -> str:
        """
        Return the name of this component for identification.
        
        Returns:
            String name of the component (e.g., 'battery', 'memory', 'cpu')
        """
        pass
    
    def validate_uuids(self) -> bool:
        """
        Validate that the provided UUIDs are in correct format.
        
        Returns:
            True if UUIDs are valid, False otherwise
        """
        try:
            UUID(self.deviceuuid)
            UUID(self.tenantuuid)
            return True
        except (ValueError, TypeError):
            log_with_route(
                logging.ERROR, 
                f"Invalid UUID format in {self.__class__.__name__}: "
                f"device={self.deviceuuid}, tenant={self.tenantuuid}"
            )
            return False
    
    def log_error(self, message: str, exc_info: bool = False) -> None:
        """
        Log an error message with consistent formatting.
        
        Args:
            message: Error message to log
            exc_info: Whether to include exception information
        """
        log_with_route(
            logging.ERROR,
            f"{self.__class__.__name__}: {message} (device: {self.deviceuuid})",
            exc_info=exc_info
        )
    
    def log_debug(self, message: str) -> None:
        """
        Log a debug message with consistent formatting.
        
        Args:
            message: Debug message to log
        """
        log_with_route(
            logging.DEBUG,
            f"{self.__class__.__name__}: {message} (device: {self.deviceuuid})"
        )
    
    def format_timestamp(self, timestamp: Optional[int]) -> Optional[str]:
        """
        Format a Unix timestamp to a readable string.
        
        Args:
            timestamp: Unix timestamp as integer
            
        Returns:
            Formatted timestamp string or None if timestamp is None
        """
        if timestamp is None:
            return None
        
        try:
            from datetime import datetime
            return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
        except (ValueError, OSError):
            self.log_error(f"Invalid timestamp: {timestamp}")
            return None
    
    def safe_get_attribute(self, obj: Any, attr: str, default: Any = None) -> Any:
        """
        Safely get an attribute from an object with default fallback.
        
        Args:
            obj: Object to get attribute from
            attr: Attribute name
            default: Default value if attribute doesn't exist
            
        Returns:
            Attribute value or default
        """
        try:
            return getattr(obj, attr, default)
        except Exception:
            return default
