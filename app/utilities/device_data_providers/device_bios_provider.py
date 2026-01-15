# Filepath: app/utilities/device_data_providers/device_bios_provider.py
"""
Device BIOS Provider

Handles fetching device BIOS information including BIOS vendor,
version, and system firmware details.
"""

from typing import Dict, Any, Optional
from app.models import db, DeviceBios
from .base_provider import BaseDeviceDataProvider


class DeviceBiosProvider(BaseDeviceDataProvider):
    """
    Provider for device BIOS information including vendor,
    version, and firmware details.
    """
    
    def get_component_name(self) -> str:
        return "bios"
    
    def get_data(self) -> Optional[Dict[str, Any]]:
        """
        Fetch device BIOS information using ORM.
        
        Returns:
            Dictionary containing BIOS data or None if not found
        """
        if not self.validate_uuids():
            return None
        
        try:
            bios = db.session.query(DeviceBios)\
                .filter(DeviceBios.deviceuuid == self.deviceuuid)\
                .first()
            
            if not bios:
                self.log_debug("No BIOS data found")
                return None
            
            # Build the BIOS data structure
            bios_data = {
                'bios_vendor': bios.bios_vendor,
                'bios_name': bios.bios_name,
                'bios_serial': bios.bios_serial,
                'bios_version': bios.bios_version,
                'last_update': bios.last_update,
                'last_json': bios.last_json,

                # Formatted data
                'last_update_formatted': self.format_timestamp(bios.last_update),
                'bios_summary': self._get_bios_summary(bios),
            }
            
            self.log_debug(f"Successfully fetched BIOS data")
            return bios_data
            
        except Exception as e:
            self.log_error(f"Error fetching BIOS data: {str(e)}", exc_info=True)
            return None
    
    def _get_bios_summary(self, bios: DeviceBios) -> str:
        """
        Create a summary string for the BIOS.
        
        Args:
            bios: DeviceBios object
            
        Returns:
            String summarizing BIOS information
        """
        parts = []
        
        if bios.bios_vendor:
            parts.append(bios.bios_vendor)
        
        if bios.bios_version:
            parts.append(f"v{bios.bios_version}")
        
        # Note: bios_date field doesn't exist in current database schema
        # Only bios_vendor, bios_name, bios_serial, bios_version are available
        
        return " • ".join(parts) if parts else "Unknown BIOS"
    
    def _get_system_summary(self, bios: DeviceBios) -> str:
        """
        Create a summary string for the system information.
        
        Args:
            bios: DeviceBios object
            
        Returns:
            String summarizing system information
        """
        parts = []
        
        if bios.system_manufacturer:
            parts.append(bios.system_manufacturer)
        
        if bios.system_product:
            parts.append(bios.system_product)
        
        if bios.system_version:
            parts.append(f"v{bios.system_version}")
        
        return " • ".join(parts) if parts else "Unknown System"
    
    def _get_baseboard_summary(self, bios: DeviceBios) -> str:
        """
        Create a summary string for the baseboard information.
        
        Args:
            bios: DeviceBios object
            
        Returns:
            String summarizing baseboard information
        """
        parts = []
        
        if bios.baseboard_manufacturer:
            parts.append(bios.baseboard_manufacturer)
        
        if bios.baseboard_product:
            parts.append(bios.baseboard_product)
        
        if bios.baseboard_version:
            parts.append(f"v{bios.baseboard_version}")
        
        return " • ".join(parts) if parts else "Unknown Baseboard"
    
    def get_bios_summary(self) -> Optional[Dict[str, Any]]:
        """
        Get a summary of BIOS information for dashboard display.
        
        Returns:
            Dictionary containing BIOS summary or None if not found
        """
        if not self.validate_uuids():
            return None
        
        try:
            bios = db.session.query(DeviceBios)\
                .filter(DeviceBios.deviceuuid == self.deviceuuid)\
                .first()
            
            if not bios:
                return None
            
            return {
                'vendor': bios.bios_vendor,
                'version': bios.bios_version,
                'date': self.format_timestamp(bios.bios_date) if bios.bios_date else None,
                'system_manufacturer': bios.system_manufacturer,
                'system_product': bios.system_product,
                'summary': self._get_bios_summary(bios),
                'last_update': self.format_timestamp(bios.last_update),
            }
            
        except Exception as e:
            self.log_error(f"Error fetching BIOS summary: {str(e)}", exc_info=True)
            return None
