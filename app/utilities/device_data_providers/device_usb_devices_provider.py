# Filepath: app/utilities/device_data_providers/device_usb_devices_provider.py
"""
Device USB Devices Provider

Handles fetching device USB device information including connected USB devices,
storage devices, and peripherals.
"""

from typing import Dict, Any, Optional, List
from app.models import db, DeviceUsbDevices
from .base_provider import BaseDeviceDataProvider


class DeviceUsbDevicesProvider(BaseDeviceDataProvider):
    """
    Provider for device USB devices information including connected devices,
    storage devices, and peripherals.
    """
    
    def get_component_name(self) -> str:
        return "usb_devices"
    
    def get_data(self) -> Optional[Dict[str, Any]]:
        """
        Fetch device USB devices information using ORM.
        
        Returns:
            Dictionary containing USB devices data or None if not found
        """
        if not self.validate_uuids():
            return None
        
        try:
            usb_devices = db.session.query(DeviceUsbDevices)\
                .filter(DeviceUsbDevices.deviceuuid == self.deviceuuid)\
                .all()
            
            if not usb_devices:
                self.log_debug("No USB devices data found")
                return None
            
            # Build the USB devices data structure
            usb_data = {
                'usb_devices': [],
                'device_count': len(usb_devices),
                'device_categories': {},
                'vendors': {},
                'summary': self._get_usb_devices_summary(usb_devices),
            }
            
            for usb_device in usb_devices:
                device_info = {
                    'usb_name': usb_device.usb_name,
                    'usb_address': usb_device.usb_address,
                    'usb_vendor': usb_device.usb_vendor,
                    'usb_product': usb_device.usb_product,
                    'usb_vendor_id': usb_device.usb_vendor_id,
                    'usb_product_id': usb_device.usb_product_id,
                    'usb_serial': usb_device.usb_serial,
                    'usb_class': usb_device.usb_class,
                    'usb_protocol': usb_device.usb_protocol,
                    'usb_version': usb_device.usb_version,
                    'usb_speed': usb_device.usb_speed,
                    'last_update': usb_device.last_update,
                    'last_json': usb_device.last_json,
                    
                    # Formatted data
                    'last_update_formatted': self.format_timestamp(usb_device.last_update),
                    'device_summary': self._get_device_summary(usb_device),
                    'device_category': self._get_device_category(usb_device),
                    'speed_formatted': self._format_usb_speed(usb_device.usb_speed),
                }
                
                usb_data['usb_devices'].append(device_info)
                
                # Count categories
                category = device_info['device_category']
                usb_data['device_categories'][category] = usb_data['device_categories'].get(category, 0) + 1
                
                # Count vendors
                vendor = usb_device.usb_vendor or 'Unknown'
                usb_data['vendors'][vendor] = usb_data['vendors'].get(vendor, 0) + 1
            
            self.log_debug(f"Successfully fetched data for {len(usb_devices)} USB devices")
            return usb_data
            
        except Exception as e:
            self.log_error(f"Error fetching USB devices data: {str(e)}", exc_info=True)
            return None
    
    def _get_device_category(self, usb_device: DeviceUsbDevices) -> str:
        """
        Determine the device category based on USB class or device name.
        
        Args:
            usb_device: DeviceUsbDevices object
            
        Returns:
            String describing device category
        """
        if usb_device.usb_class:
            usb_class = usb_device.usb_class.lower()
            
            if 'storage' in usb_class or 'mass storage' in usb_class:
                return "Storage"
            elif 'hub' in usb_class:
                return "Hub"
            elif 'hid' in usb_class or 'human interface' in usb_class:
                return "Input Device"
            elif 'audio' in usb_class:
                return "Audio"
            elif 'video' in usb_class or 'imaging' in usb_class:
                return "Video/Imaging"
            elif 'printer' in usb_class:
                return "Printer"
            elif 'communication' in usb_class or 'cdc' in usb_class:
                return "Communication"
        
        if usb_device.usb_name:
            name = usb_device.usb_name.lower()
            
            if any(keyword in name for keyword in ['mouse', 'keyboard', 'touchpad']):
                return "Input Device"
            elif any(keyword in name for keyword in ['storage', 'drive', 'disk', 'flash']):
                return "Storage"
            elif any(keyword in name for keyword in ['camera', 'webcam']):
                return "Video/Imaging"
            elif any(keyword in name for keyword in ['speaker', 'headset', 'microphone']):
                return "Audio"
            elif 'printer' in name:
                return "Printer"
            elif 'hub' in name:
                return "Hub"
        
        return "Other"
    
    def _format_usb_speed(self, speed: Optional[str]) -> Optional[str]:
        """
        Format USB speed for display.
        
        Args:
            speed: USB speed string
            
        Returns:
            Formatted speed string or None if speed is None
        """
        if not speed:
            return None
        
        speed_lower = speed.lower()
        
        if 'super' in speed_lower:
            return "USB 3.0+ (SuperSpeed)"
        elif 'high' in speed_lower:
            return "USB 2.0 (High Speed)"
        elif 'full' in speed_lower:
            return "USB 1.1 (Full Speed)"
        elif 'low' in speed_lower:
            return "USB 1.0 (Low Speed)"
        else:
            return speed
    
    def _get_device_summary(self, usb_device: DeviceUsbDevices) -> str:
        """
        Create a summary string for a USB device.
        
        Args:
            usb_device: DeviceUsbDevices object
            
        Returns:
            String summarizing USB device information
        """
        parts = []
        
        if usb_device.usb_name:
            parts.append(usb_device.usb_name)
        elif usb_device.usb_product:
            parts.append(usb_device.usb_product)
        
        if usb_device.usb_vendor:
            parts.append(usb_device.usb_vendor)
        
        category = self._get_device_category(usb_device)
        if category != "Other":
            parts.append(category)
        
        if usb_device.usb_address:
            parts.append(f"@ {usb_device.usb_address}")
        
        return " • ".join(parts) if parts else "Unknown USB Device"
    
    def _get_usb_devices_summary(self, usb_devices: List[DeviceUsbDevices]) -> str:
        """
        Create a summary string for all USB devices.
        
        Args:
            usb_devices: List of DeviceUsbDevices objects
            
        Returns:
            String summarizing all USB devices
        """
        if not usb_devices:
            return "No USB devices found"
        
        # Count categories
        categories = {}
        for device in usb_devices:
            category = self._get_device_category(device)
            categories[category] = categories.get(category, 0) + 1
        
        parts = [f"{len(usb_devices)} USB devices"]
        
        # Add top categories
        sorted_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)
        for category, count in sorted_categories[:3]:  # Top 3 categories
            if category != "Other":
                parts.append(f"{count} {category}")
        
        return " • ".join(parts)
    
    def get_usb_devices_summary(self) -> Optional[Dict[str, Any]]:
        """
        Get a summary of USB devices information for dashboard display.
        
        Returns:
            Dictionary containing USB devices summary or None if not found
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
