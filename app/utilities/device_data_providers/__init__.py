# Filepath: app/utilities/device_data_providers/__init__.py
"""
Device Data Providers Package

This package contains modular data providers for device information.
Each provider handles a specific aspect of device data using ORM queries.
"""

from .base_provider import BaseDeviceDataProvider
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
from .device_aggregator import DeviceDataAggregator

__all__ = [
    'BaseDeviceDataProvider',
    'DeviceBasicProvider',
    'DeviceStatusProvider',
    'DeviceConnectivityProvider',
    'DeviceMetadataProvider',
    'DeviceBatteryProvider',
    'DeviceMemoryProvider',
    'DeviceCpuProvider',
    'DeviceGpuProvider',
    'DeviceBiosProvider',
    'DeviceDrivesProvider',
    'DeviceNetworksProvider',
    'DevicePartitionsProvider',
    'DeviceUsersProvider',
    'DevicePrintersProvider',
    'DeviceUsbDevicesProvider',
    'DeviceDataAggregator'
]
