# Filepath: app/utilities/device_data_providers/device_battery_provider.py
"""
Device Battery Provider

Handles fetching device battery information including charge status,
power source, and battery health metrics.
"""

from typing import Dict, Any, Optional
from app.models import db, DeviceBattery
from .base_provider import BaseDeviceDataProvider


class DeviceBatteryProvider(BaseDeviceDataProvider):
    """
    Provider for device battery information including charge level,
    power source, and battery installation status.
    """
    
    def get_component_name(self) -> str:
        return "battery"
    
    def get_data(self) -> Optional[Dict[str, Any]]:
        """
        Fetch device battery information using ORM.
        
        Returns:
            Dictionary containing battery data or None if not found
        """
        if not self.validate_uuids():
            return None
        
        try:
            battery = db.session.query(DeviceBattery)\
                .filter(DeviceBattery.deviceuuid == self.deviceuuid)\
                .first()
            
            if not battery:
                self.log_debug("No battery data found")
                return None
            
            # Build the battery data structure
            battery_data = {
                'battery_installed': battery.battery_installed,
                'percent_charged': battery.percent_charged,
                'on_mains_power': battery.on_mains_power,
                'last_update': battery.last_update,
                'last_json': battery.last_json,
                
                # Formatted data
                'last_update_formatted': self.format_timestamp(battery.last_update),
                'charge_status': self._get_charge_status(battery),
                'power_source': self._get_power_source(battery),
                'battery_health': self._get_battery_health(battery),
            }
            
            self.log_debug(f"Successfully fetched battery data")
            return battery_data
            
        except Exception as e:
            self.log_error(f"Error fetching battery data: {str(e)}", exc_info=True)
            return None
    
    def _get_charge_status(self, battery: DeviceBattery) -> str:
        """
        Determine the charge status based on battery data.
        
        Args:
            battery: DeviceBattery object
            
        Returns:
            String describing charge status
        """
        if not battery.battery_installed:
            return "No Battery"
        
        if battery.on_mains_power:
            if battery.percent_charged >= 100:
                return "Fully Charged"
            else:
                return "Charging"
        else:
            if battery.percent_charged <= 10:
                return "Critical"
            elif battery.percent_charged <= 25:
                return "Low"
            else:
                return "Discharging"
    
    def _get_power_source(self, battery: DeviceBattery) -> str:
        """
        Determine the power source.
        
        Args:
            battery: DeviceBattery object
            
        Returns:
            String describing power source
        """
        if not battery.battery_installed:
            return "AC Power"
        
        return "AC Power" if battery.on_mains_power else "Battery"
    
    def _get_battery_health(self, battery: DeviceBattery) -> str:
        """
        Assess battery health based on available data.
        
        Args:
            battery: DeviceBattery object
            
        Returns:
            String describing battery health
        """
        if not battery.battery_installed:
            return "N/A"
        
        # Basic health assessment based on charge percentage patterns
        # This could be enhanced with more sophisticated health metrics
        if battery.percent_charged is None:
            return "Unknown"
        
        # Simple health indicator - could be enhanced with historical data
        return "Good"  # Placeholder - enhance with actual health logic
    
    def has_battery(self) -> bool:
        """
        Check if the device has a battery installed.
        
        Returns:
            True if battery is installed, False otherwise
        """
        try:
            battery = db.session.query(DeviceBattery)\
                .filter(DeviceBattery.deviceuuid == self.deviceuuid)\
                .first()
            
            return battery is not None and battery.battery_installed
            
        except Exception as e:
            self.log_error(f"Error checking battery installation: {str(e)}")
            return False
