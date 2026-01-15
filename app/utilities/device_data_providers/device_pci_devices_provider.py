# Filepath: app/utilities/device_data_providers/device_pci_devices_provider.py
"""
Device PCI Devices Provider

Handles fetching device PCI device information including PCI cards,
controllers, and hardware components connected via PCI bus.
"""

from typing import Dict, Any, Optional, List
from app.models import db, DevicePciDevices
from .base_provider import BaseDeviceDataProvider


class DevicePciDevicesProvider(BaseDeviceDataProvider):
    """
    Provider for device PCI devices information including PCI cards,
    controllers, and hardware components.
    """
    
    def get_component_name(self) -> str:
        return "pci_devices"
    
    def get_data(self) -> Optional[Dict[str, Any]]:
        """
        Fetch device PCI devices information using ORM.
        
        Returns:
            Dictionary containing PCI devices data or None if not found
        """
        if not self.validate_uuids():
            return None
        
        try:
            pci_devices = db.session.query(DevicePciDevices)\
                .filter(DevicePciDevices.deviceuuid == self.deviceuuid)\
                .all()
            
            if not pci_devices:
                self.log_debug("No PCI devices data found")
                return None
            
            # Build the PCI devices data structure
            pci_data = {
                'pci_devices': [],
                'device_count': len(pci_devices),
                'device_categories': {},
                'vendors': {},
                'summary': self._get_pci_devices_summary(pci_devices),
            }
            
            for pci_device in pci_devices:
                device_info = {
                    'pci_name': pci_device.pci_name,
                    'pci_vendor': pci_device.pci_vendor,
                    'pci_device_id': pci_device.pci_device_id,
                    'pci_vendor_id': pci_device.pci_vendor_id,
                    'pci_subsystem': pci_device.pci_subsystem,
                    'pci_class': pci_device.pci_class,
                    'pci_subclass': pci_device.pci_subclass,
                    'pci_driver': pci_device.pci_driver,
                    'pci_location': pci_device.pci_location,
                    'pci_status': pci_device.pci_status,
                    'last_update': pci_device.last_update,
                    'last_json': pci_device.last_json,
                    
                    # Formatted data
                    'last_update_formatted': self.format_timestamp(pci_device.last_update),
                    'device_summary': self._get_device_summary(pci_device),
                    'device_category': self._get_device_category(pci_device),
                    'is_critical': self._is_critical_device(pci_device),
                }
                
                pci_data['pci_devices'].append(device_info)
                
                # Count categories
                category = device_info['device_category']
                pci_data['device_categories'][category] = pci_data['device_categories'].get(category, 0) + 1
                
                # Count vendors
                vendor = pci_device.pci_vendor or 'Unknown'
                pci_data['vendors'][vendor] = pci_data['vendors'].get(vendor, 0) + 1
            
            self.log_debug(f"Successfully fetched data for {len(pci_devices)} PCI devices")
            return pci_data
            
        except Exception as e:
            self.log_error(f"Error fetching PCI devices data: {str(e)}", exc_info=True)
            return None
    
    def _get_device_category(self, pci_device: DevicePciDevices) -> str:
        """
        Determine the device category based on PCI class information.
        
        Args:
            pci_device: DevicePciDevices object
            
        Returns:
            String describing device category
        """
        if pci_device.pci_class:
            pci_class = pci_device.pci_class.lower()
            
            if 'network' in pci_class or 'ethernet' in pci_class:
                return "Network"
            elif 'display' in pci_class or 'vga' in pci_class or 'graphics' in pci_class:
                return "Graphics"
            elif 'audio' in pci_class or 'sound' in pci_class:
                return "Audio"
            elif 'storage' in pci_class or 'sata' in pci_class or 'ide' in pci_class:
                return "Storage"
            elif 'usb' in pci_class:
                return "USB Controller"
            elif 'bridge' in pci_class:
                return "Bridge"
            elif 'memory' in pci_class:
                return "Memory"
            elif 'processor' in pci_class or 'cpu' in pci_class:
                return "Processor"
        
        if pci_device.pci_name:
            name = pci_device.pci_name.lower()
            
            if any(keyword in name for keyword in ['ethernet', 'network', 'wifi', 'wireless']):
                return "Network"
            elif any(keyword in name for keyword in ['graphics', 'display', 'video', 'vga']):
                return "Graphics"
            elif any(keyword in name for keyword in ['audio', 'sound', 'speaker']):
                return "Audio"
            elif any(keyword in name for keyword in ['storage', 'sata', 'ide', 'nvme']):
                return "Storage"
            elif 'usb' in name:
                return "USB Controller"
        
        return "Other"
    
    def _is_critical_device(self, pci_device: DevicePciDevices) -> bool:
        """
        Determine if a PCI device is critical for system operation.
        
        Args:
            pci_device: DevicePciDevices object
            
        Returns:
            True if device is critical, False otherwise
        """
        category = self._get_device_category(pci_device)
        critical_categories = ["Storage", "Memory", "Processor", "Bridge"]
        
        return category in critical_categories
    
    def _get_device_summary(self, pci_device: DevicePciDevices) -> str:
        """
        Create a summary string for a PCI device.
        
        Args:
            pci_device: DevicePciDevices object
            
        Returns:
            String summarizing PCI device information
        """
        parts = []
        
        if pci_device.pci_name:
            parts.append(pci_device.pci_name)
        
        if pci_device.pci_vendor:
            parts.append(pci_device.pci_vendor)
        
        category = self._get_device_category(pci_device)
        if category != "Other":
            parts.append(category)
        
        if pci_device.pci_location:
            parts.append(f"@ {pci_device.pci_location}")
        
        return " • ".join(parts) if parts else "Unknown PCI Device"
    
    def _get_pci_devices_summary(self, pci_devices: List[DevicePciDevices]) -> str:
        """
        Create a summary string for all PCI devices.
        
        Args:
            pci_devices: List of DevicePciDevices objects
            
        Returns:
            String summarizing all PCI devices
        """
        if not pci_devices:
            return "No PCI devices found"
        
        # Count categories
        categories = {}
        for device in pci_devices:
            category = self._get_device_category(device)
            categories[category] = categories.get(category, 0) + 1
        
        parts = [f"{len(pci_devices)} PCI devices"]
        
        # Add top categories
        sorted_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)
        for category, count in sorted_categories[:3]:  # Top 3 categories
            if category != "Other":
                parts.append(f"{count} {category}")
        
        return " • ".join(parts)
    
    def get_pci_devices_summary(self) -> Optional[Dict[str, Any]]:
        """
        Get a summary of PCI devices information for dashboard display.
        
        Returns:
            Dictionary containing PCI devices summary or None if not found
        """
        data = self.get_data()
        if not data:
            return None
        
        return {
            'device_count': data['device_count'],
            'device_categories': data['device_categories'],
            'vendors': data['vendors'],
            'summary': data['summary'],
        }
    
    def get_devices_by_category(self, category: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get PCI devices filtered by category.
        
        Args:
            category: Device category to filter by
            
        Returns:
            List of devices in the specified category or None if not found
        """
        data = self.get_data()
        if not data or not data['pci_devices']:
            return None
        
        return [device for device in data['pci_devices'] 
                if device.get('device_category') == category]
