# Filepath: app/utilities/device_data_providers/device_basic_provider.py
"""
Device Basic Information Provider

Handles fetching basic device information including device details,
group information, and organization data.
"""

from typing import Dict, Any, Optional
from sqlalchemy.orm import joinedload
from app.models import db, Devices, Groups, Organisations
from .base_provider import BaseDeviceDataProvider


class DeviceBasicProvider(BaseDeviceDataProvider):
    """
    Provider for basic device information including device details,
    group membership, and organization data.
    """
    
    def get_component_name(self) -> str:
        return "basic"
    
    def get_data(self) -> Optional[Dict[str, Any]]:
        """
        Fetch basic device information using ORM.
        
        Returns:
            Dictionary containing basic device data or None if device not found
        """
        if not self.validate_uuids():
            return None
        
        try:
            # Use ORM with joinedload to fetch related data efficiently
            device = db.session.query(Devices)\
                .options(
                    joinedload(Devices.group),
                    joinedload(Devices.organisation)
                )\
                .filter(
                    Devices.deviceuuid == self.deviceuuid,
                    Devices.tenantuuid == self.tenantuuid
                )\
                .first()
            
            if not device:
                self.log_error(f"Device not found")
                return None
            
            # Build the basic device data structure
            device_data = {
                'deviceuuid': str(device.deviceuuid),
                'devicename': device.devicename,
                'hardwareinfo': device.hardwareinfo,
                'created_at': device.created_at,
                'health_score': device.health_score,
                'tenantuuid': str(device.tenantuuid),
                
                # Group information
                'groupuuid': str(device.groupuuid) if device.groupuuid else None,
                'groupname': device.group.groupname if device.group else None,
                
                # Organization information  
                'orguuid': str(device.orguuid) if device.orguuid else None,
                'orgname': device.organisation.orgname if device.organisation else None,
            }
            
            self.log_debug(f"Successfully fetched basic data for device {device.devicename}")
            return device_data
            
        except Exception as e:
            self.log_error(f"Error fetching basic device data: {str(e)}", exc_info=True)
            return None
    
    def get_device_with_relations(self) -> Optional[Devices]:
        """
        Get the device object with all relations loaded.
        
        Returns:
            Device object with relations or None if not found
        """
        if not self.validate_uuids():
            return None
        
        try:
            return db.session.query(Devices)\
                .options(
                    joinedload(Devices.group),
                    joinedload(Devices.organisation)
                )\
                .filter(
                    Devices.deviceuuid == self.deviceuuid,
                    Devices.tenantuuid == self.tenantuuid
                )\
                .first()
        except Exception as e:
            self.log_error(f"Error fetching device with relations: {str(e)}", exc_info=True)
            return None
