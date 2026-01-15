# Filepath: app/utilities/device_data_providers/device_networks_provider.py
"""
Device Networks Provider

Handles fetching device network information including network interfaces,
IP addresses, and network configuration.
"""

from typing import Dict, Any, Optional, List
from app.models import db, DeviceNetworks
from .base_provider import BaseDeviceDataProvider


class DeviceNetworksProvider(BaseDeviceDataProvider):
    """
    Provider for device network information including network interfaces,
    IP addresses, and network configuration.
    """
    
    def get_component_name(self) -> str:
        return "networks"
    
    def get_data(self) -> Optional[Dict[str, Any]]:
        """
        Fetch device networks information using ORM.
        
        Returns:
            Dictionary containing networks data or None if not found
        """
        if not self.validate_uuids():
            return None
        
        try:
            networks = db.session.query(DeviceNetworks)\
                .filter(DeviceNetworks.deviceuuid == self.deviceuuid)\
                .all()
            
            if not networks:
                self.log_debug("No networks data found")
                return None
            
            # Build the networks data structure
            networks_data = {
                'networks': [],
                'network_count': len(networks),
                'active_networks': 0,
                'wired_networks': 0,
                'wireless_networks': 0,
                'summary': self._get_networks_summary(networks),
            }
            
            for network in networks:
                network_info = {
                    'network_name': network.network_name,
                    'if_is_up': network.if_is_up,
                    'address_4': network.address_4,
                    'address_6': network.address_6,
                    'netmask_4': network.netmask_4,
                    'netmask_6': network.netmask_6,
                    'broadcast_4': network.broadcast_4,
                    'broadcast_6': network.broadcast_6,
                    'if_speed': network.if_speed,
                    'if_mtu': network.if_mtu,
                    'bytes_sent': network.bytes_sent,
                    'bytes_rec': network.bytes_rec,
                    'err_in': network.err_in,
                    'err_out': network.err_out,
                    'last_update': network.last_update,
                    'last_json': network.last_json,

                    # Formatted data
                    'last_update_formatted': self.format_timestamp(network.last_update),
                    'speed_formatted': self._format_speed(network.if_speed),
                    'network_summary': self._get_network_summary(network),
                    'is_active': self._is_network_active(network),
                    'connection_type': self._get_connection_type(network),
                }
                
                networks_data['networks'].append(network_info)
                
                # Count network types
                if network_info['is_active']:
                    networks_data['active_networks'] += 1
                
                connection_type = network_info['connection_type']
                if connection_type == 'Wired':
                    networks_data['wired_networks'] += 1
                elif connection_type == 'Wireless':
                    networks_data['wireless_networks'] += 1
            
            self.log_debug(f"Successfully fetched data for {len(networks)} networks")
            return networks_data
            
        except Exception as e:
            self.log_error(f"Error fetching networks data: {str(e)}", exc_info=True)
            return None
    
    def _format_speed(self, speed: Optional[int]) -> Optional[str]:
        """
        Format network speed for display.
        
        Args:
            speed: Speed in bits per second
            
        Returns:
            Formatted speed string or None if speed is None
        """
        if speed is None:
            return None
        
        try:
            if speed >= 1000000000:  # 1 Gbps
                return f"{speed / 1000000000:.1f} Gbps"
            elif speed >= 1000000:  # 1 Mbps
                return f"{speed / 1000000:.1f} Mbps"
            elif speed >= 1000:  # 1 Kbps
                return f"{speed / 1000:.1f} Kbps"
            else:
                return f"{speed} bps"
        except (TypeError, ZeroDivisionError):
            return None
    
    def _is_network_active(self, network: DeviceNetworks) -> bool:
        """
        Determine if a network interface is active.
        
        Args:
            network: DeviceNetworks object
            
        Returns:
            True if network is active, False otherwise
        """
        # Use if_is_up field from the database
        return network.if_is_up if hasattr(network, 'if_is_up') else False
        
        # If no status, check if it has an IP address
        return bool(network.address_4 or network.address_6)
    
    def _get_connection_type(self, network: DeviceNetworks) -> str:
        """
        Determine the connection type based on network information.
        
        Args:
            network: DeviceNetworks object
            
        Returns:
            String describing connection type
        """
        # Note: network_type field doesn't exist in current database schema
        # Only network_name, if_is_up, address_4, address_6, etc. are available
        
        if network.network_name:
            name = network.network_name.lower()
            if 'wifi' in name or 'wireless' in name or 'wlan' in name:
                return "Wireless"
            elif 'ethernet' in name or 'eth' in name or 'lan' in name:
                return "Wired"
        
        return "Unknown"
    
    def _get_network_summary(self, network: DeviceNetworks) -> str:
        """
        Create a summary string for a network interface.
        
        Args:
            network: DeviceNetworks object
            
        Returns:
            String summarizing network information
        """
        parts = []
        
        if network.network_name:
            parts.append(network.network_name)
        
        if network.address_4:
            parts.append(network.address_4)
        
        connection_type = self._get_connection_type(network)
        if connection_type != "Unknown":
            parts.append(connection_type)
        
        # Note: speed field doesn't exist in current database schema
        # Only if_speed is available
        if network.if_speed:
            speed_formatted = self._format_speed(network.if_speed)
            if speed_formatted:
                parts.append(speed_formatted)
        
        return " • ".join(parts) if parts else "Unknown Network"
    
    def _get_networks_summary(self, networks: List[DeviceNetworks]) -> str:
        """
        Create a summary string for all networks.
        
        Args:
            networks: List of DeviceNetworks objects
            
        Returns:
            String summarizing all networks
        """
        if not networks:
            return "No networks found"
        
        active_count = sum(1 for network in networks if self._is_network_active(network))
        wired_count = sum(1 for network in networks if self._get_connection_type(network) == "Wired")
        wireless_count = sum(1 for network in networks if self._get_connection_type(network) == "Wireless")
        
        parts = [f"{len(networks)} interfaces"]
        
        if active_count > 0:
            parts.append(f"{active_count} active")
        
        if wired_count > 0:
            parts.append(f"{wired_count} wired")
        
        if wireless_count > 0:
            parts.append(f"{wireless_count} wireless")
        
        return " • ".join(parts)
    
    def get_networks_summary(self) -> Optional[Dict[str, Any]]:
        """
        Get a summary of networks information for dashboard display.
        
        Returns:
            Dictionary containing networks summary or None if not found
        """
        data = self.get_data()
        if not data:
            return None
        
        return {
            'network_count': data['network_count'],
            'active_networks': data['active_networks'],
            'wired_networks': data['wired_networks'],
            'wireless_networks': data['wireless_networks'],
            'summary': data['summary'],
        }
    
    def get_primary_network(self) -> Optional[Dict[str, Any]]:
        """
        Get the primary network interface (usually the one with a default gateway).
        
        Returns:
            Dictionary containing primary network info or None if not found
        """
        data = self.get_data()
        if not data or not data['networks']:
            return None
        
        # Look for network with gateway first
        for network in data['networks']:
            if network.get('gateway_4') or network.get('gateway_6'):
                return network
        
        # Fall back to first active network
        for network in data['networks']:
            if network.get('is_active'):
                return network
        
        # Fall back to first network
        return data['networks'][0] if data['networks'] else None
