# Filepath: app/utilities/device_data_providers/device_aggregator.py
"""
Device Data Aggregator

Central service that coordinates all device data providers and provides
a clean interface for fetching device information modularly.
"""

from typing import Dict, Any, Optional, List, Set
import logging
from app.utilities.app_logging_helper import log_with_route
from .device_basic_provider import DeviceBasicProvider
from .device_status_provider import DeviceStatusProvider
from .device_connectivity_provider import DeviceConnectivityProvider
from .device_metadata_provider import DeviceMetadataProvider
from .device_battery_provider import DeviceBatteryProvider
from .device_memory_provider import DeviceMemoryProvider
from .device_cpu_provider import DeviceCpuProvider
from .device_gpu_provider import DeviceGpuProvider
from .device_bios_provider import DeviceBiosProvider
from .device_drives_provider import DeviceDrivesProvider
from .device_networks_provider import DeviceNetworksProvider
from .device_partitions_provider import DevicePartitionsProvider
from .device_users_provider import DeviceUsersProvider
from .device_printers_provider import DevicePrintersProvider
from .device_usb_devices_provider import DeviceUsbDevicesProvider


class DeviceDataAggregator:
    """
    Central aggregator that coordinates all device data providers.
    
    This class provides a clean interface for fetching device data
    modularly, allowing components to be requested individually or
    in groups.
    """
    
    def __init__(self, deviceuuid: str, tenantuuid: str):
        """
        Initialize the aggregator with device and tenant UUIDs.
        
        Args:
            deviceuuid: The device UUID as string
            tenantuuid: The tenant UUID as string
        """
        self.deviceuuid = deviceuuid
        self.tenantuuid = tenantuuid
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize all providers
        self.providers = {
            'basic': DeviceBasicProvider(deviceuuid, tenantuuid),
            'status': DeviceStatusProvider(deviceuuid, tenantuuid),
            'connectivity': DeviceConnectivityProvider(deviceuuid, tenantuuid),
            'metadata': DeviceMetadataProvider(deviceuuid, tenantuuid),
            'battery': DeviceBatteryProvider(deviceuuid, tenantuuid),
            'memory': DeviceMemoryProvider(deviceuuid, tenantuuid),
            'cpu': DeviceCpuProvider(deviceuuid, tenantuuid),
            'gpu': DeviceGpuProvider(deviceuuid, tenantuuid),
            'bios': DeviceBiosProvider(deviceuuid, tenantuuid),
            'drives': DeviceDrivesProvider(deviceuuid, tenantuuid),
            'networks': DeviceNetworksProvider(deviceuuid, tenantuuid),
            'partitions': DevicePartitionsProvider(deviceuuid, tenantuuid),
            'users': DeviceUsersProvider(deviceuuid, tenantuuid),
            'printers': DevicePrintersProvider(deviceuuid, tenantuuid),
            'usb_devices': DeviceUsbDevicesProvider(deviceuuid, tenantuuid),
        }
    
    def get_all_data(self) -> Dict[str, Any]:
        """
        Fetch data from all available providers.
        
        Returns:
            Dictionary containing all device data organized by component
        """
        device_data = {}
        
        for component_name, provider in self.providers.items():
            try:
                data = provider.get_data()
                if data is not None:
                    device_data[component_name] = data
                else:
                    log_with_route(
                        logging.DEBUG,
                        f"No data returned from {component_name} provider for device {self.deviceuuid}"
                    )
            except Exception as e:
                log_with_route(
                    logging.ERROR,
                    f"Error fetching data from {component_name} provider: {str(e)}",
                    exc_info=True
                )
        
        return device_data
    
    def get_components_data(self, components: List[str]) -> Dict[str, Any]:
        """
        Fetch data from specific components only.
        
        Args:
            components: List of component names to fetch data for
            
        Returns:
            Dictionary containing requested component data
        """
        device_data = {}
        
        for component_name in components:
            if component_name not in self.providers:
                log_with_route(
                    logging.WARNING,
                    f"Unknown component requested: {component_name}"
                )
                continue
            
            try:
                provider = self.providers[component_name]
                data = provider.get_data()
                if data is not None:
                    device_data[component_name] = data
            except Exception as e:
                log_with_route(
                    logging.ERROR,
                    f"Error fetching data from {component_name} provider: {str(e)}",
                    exc_info=True
                )
        
        return device_data
    
    def get_essential_data(self) -> Dict[str, Any]:
        """
        Fetch only essential device data for basic display.

        Returns:
            Dictionary containing essential device data
        """
        essential_components = ['basic', 'status', 'connectivity', 'metadata', 'battery', 'memory', 'cpu']
        return self.get_components_data(essential_components)
    
    def get_hardware_data(self) -> Dict[str, Any]:
        """
        Fetch only hardware-related data.
        
        Returns:
            Dictionary containing hardware component data
        """
        hardware_components = ['cpu', 'memory', 'battery']  # Add 'gpu', 'bios' when implemented
        return self.get_components_data(hardware_components)
    
    def get_available_components(self) -> List[str]:
        """
        Get list of available component names.
        
        Returns:
            List of available component names
        """
        return list(self.providers.keys())
    
    def has_component_data(self, component: str) -> bool:
        """
        Check if a specific component has data available.
        
        Args:
            component: Component name to check
            
        Returns:
            True if component has data, False otherwise
        """
        if component not in self.providers:
            return False
        
        try:
            provider = self.providers[component]
            data = provider.get_data()
            return data is not None
        except Exception:
            return False
    
    def get_device_summary(self) -> Dict[str, Any]:
        """
        Get a summary of device information suitable for dashboard display.
        
        Returns:
            Dictionary containing device summary data
        """
        summary = {}
        
        # Get basic device info
        basic_data = self.get_components_data(['basic'])
        if 'basic' in basic_data:
            summary.update({
                'deviceuuid': basic_data['basic']['deviceuuid'],
                'devicename': basic_data['basic']['devicename'],
                'health_score': basic_data['basic']['health_score'],
                'groupname': basic_data['basic']['groupname'],
                'orgname': basic_data['basic']['orgname'],
            })
        
        # Get status info
        status_data = self.get_components_data(['status'])
        if 'status' in status_data:
            summary.update({
                'agent_platform': status_data['status']['agent_platform'],
                'logged_on_user': status_data['status']['logged_on_user'],
                'publicIp': status_data['status']['publicIp'],
                'last_update': status_data['status']['last_update_formatted'],
            })
        
        return summary
