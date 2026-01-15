# Filepath: app/utilities/device_data_providers/device_printers_provider.py
"""
Device Printers Provider

Handles fetching device printer information including installed printers,
printer status, and printer configuration.
"""

from typing import Dict, Any, Optional, List
from app.models import db, DevicePrinters
from .base_provider import BaseDeviceDataProvider


class DevicePrintersProvider(BaseDeviceDataProvider):
    """
    Provider for device printer information including installed printers,
    status, and configuration details.
    """

    # Win32_Printer PrinterStatus codes mapping
    PRINTER_STATUS_MAP = {
        1: "Other",
        2: "Unknown",
        3: "Idle",
        4: "Printing",
        5: "Warming Up",
        6: "Stopped Printing",
        7: "Offline"
    }

    @staticmethod
    def convert_printer_status(status) -> str:
        """
        Convert numeric PrinterStatus code to human-readable string.

        Args:
            status: Numeric status code or string status

        Returns:
            Human-readable status string
        """
        if status is None:
            return "Unknown"

        # If already a string, check if it's numeric
        if isinstance(status, str):
            # Try to convert to int if it's a numeric string
            if status.isdigit():
                status = int(status)
            else:
                # Already a string status, return as-is
                return status

        # Convert numeric status to string
        if isinstance(status, int):
            return DevicePrintersProvider.PRINTER_STATUS_MAP.get(status, f"Unknown ({status})")

        return str(status)

    def get_component_name(self) -> str:
        return "printers"

    def get_data(self) -> Optional[Dict[str, Any]]:
        """
        Fetch device printers information using ORM.

        Returns:
            Dictionary containing printers data or None if not found
        """
        if not self.validate_uuids():
            return None

        try:
            printers = db.session.query(DevicePrinters)\
                .filter(DevicePrinters.deviceuuid == self.deviceuuid)\
                .all()

            if not printers:
                self.log_debug("No printers data found")
                return None

            # Build the printers data structure
            printers_data = {
                'printers': [],
                'printer_count': len(printers),
                'default_printers': 0,
                'network_printers': 0,
                'local_printers': 0,
                'active_printers': 0,
                'summary': self._get_printers_summary(printers),
            }

            for printer in printers:
                # Convert numeric status to human-readable string
                status_readable = self.convert_printer_status(printer.printer_status)

                printer_info = {
                    'printer_name': printer.printer_name,
                    'printer_driver': printer.printer_driver,
                    'printer_port': printer.printer_port,
                    'printer_location': printer.printer_location,
                    'printer_status': printer.printer_status,  # Keep original for reference
                    'printer_status_readable': status_readable,  # Human-readable status
                    'printer_default': printer.printer_default,
                    'last_update': printer.last_update,
                    'last_json': printer.last_json,

                    # Formatted data
                    'last_update_formatted': self.format_timestamp(printer.last_update),
                    'printer_summary': self._get_printer_summary(printer),
                    'is_network_printer': self._is_network_printer(printer),
                    'is_active': self._is_printer_active(printer),
                    'printer_type': self._get_printer_type(printer),
                }

                printers_data['printers'].append(printer_info)

                # Count printer types
                if printer.printer_default:
                    printers_data['default_printers'] += 1

                if printer_info['is_network_printer']:
                    printers_data['network_printers'] += 1
                else:
                    printers_data['local_printers'] += 1

                if printer_info['is_active']:
                    printers_data['active_printers'] += 1

            self.log_debug(f"Successfully fetched data for {len(printers)} printers")
            return printers_data

        except Exception as e:
            self.log_error(f"Error fetching printers data: {str(e)}", exc_info=True)
            return None

    def _is_network_printer(self, printer: DevicePrinters) -> bool:
        """
        Determine if a printer is a network printer.

        Args:
            printer: DevicePrinters object

        Returns:
            True if it's a network printer, False otherwise
        """
        # Check if it's a network printer based on port information
        # Since printer_server field doesn't exist, use port to determine network status

        if printer.printer_port:
            port = printer.printer_port.lower()
            network_indicators = ['ip_', 'tcp', 'http', 'lpd', 'socket', '\\\\']
            if any(indicator in port for indicator in network_indicators):
                return True

        # Note: printer_share_name field doesn't exist in current database schema
        # Only printer_name, printer_driver, printer_port, printer_location, printer_status, printer_default are available

        # Additional check: consider printer_location and broader indicators
        _loc = (printer.printer_location or '').lower()
        _port = (printer.printer_port or '').lower()
        _haystack = f"{_port} {_loc}"
        _extra_indicators = ['https', 'http', 'ipp', 'ipps', 'lpr', 'lpd', 'socket', 'tcp', 'ip_', 'wsd', '\\']
        if any(indicator in _haystack for indicator in _extra_indicators):
            return True

        return False

    def _is_printer_active(self, printer: DevicePrinters) -> bool:
        """
        Determine if a printer is active/available.

        Args:
            printer: DevicePrinters object

        Returns:
            True if printer is active, False otherwise
        """
        if printer.printer_status:
            status = printer.printer_status.lower()
            inactive_statuses = ['offline', 'error', 'paused', 'disabled', 'not available']
            if any(inactive in status for inactive in inactive_statuses):
                return False

        # Note: printer_state field doesn't exist in current database schema
        # printer_status is already checked above

        return True

    def _get_printer_type(self, printer: DevicePrinters) -> str:
        """
        Determine the printer type based on available information.

        Args:
            printer: DevicePrinters object

        Returns:
            String describing printer type
        """
        if self._is_network_printer(printer):
            return "Network"
        else:
            return "Local"

    def _get_printer_summary(self, printer: DevicePrinters) -> str:
        """
        Create a summary string for a printer.

        Args:
            printer: DevicePrinters object

        Returns:
            String summarizing printer information
        """
        parts = []

        if printer.printer_name:
            parts.append(printer.printer_name)

        printer_type = self._get_printer_type(printer)
        parts.append(printer_type)

        if printer.printer_default:
            parts.append("Default")

        if printer.printer_status:
            parts.append(printer.printer_status)

        if printer.printer_location:
            parts.append(f"@ {printer.printer_location}")

        return " • ".join(parts) if parts else "Unknown Printer"

    def _get_printers_summary(self, printers: List[DevicePrinters]) -> str:
        """
        Create a summary string for all printers.

        Args:
            printers: List of DevicePrinters objects

        Returns:
            String summarizing all printers
        """
        if not printers:
            return "No printers found"

        network_count = sum(1 for printer in printers if self._is_network_printer(printer))
        local_count = len(printers) - network_count
        default_count = sum(1 for printer in printers if printer.printer_default)
        active_count = sum(1 for printer in printers if self._is_printer_active(printer))

        parts = [f"{len(printers)} printers"]

        if network_count > 0:
            parts.append(f"{network_count} network")

        if local_count > 0:
            parts.append(f"{local_count} local")

        if default_count > 0:
            parts.append(f"{default_count} default")

        if active_count != len(printers):
            parts.append(f"{active_count} active")

        return " • ".join(parts)

    def get_printers_summary(self) -> Optional[Dict[str, Any]]:
        """
        Get a summary of printers information for dashboard display.

        Returns:
            Dictionary containing printers summary or None if not found
        """
        data = self.get_data()
        if not data:
            return None

        return {
            'printer_count': data['printer_count'],
            'network_printers': data['network_printers'],
            'local_printers': data['local_printers'],
            'default_printers': data['default_printers'],
            'active_printers': data['active_printers'],
            'summary': data['summary'],
        }

    def get_default_printer(self) -> Optional[Dict[str, Any]]:
        """
        Get the default printer information.

        Returns:
            Dictionary containing default printer info or None if not found
        """
        data = self.get_data()
        if not data or not data['printers']:
            return None

        # Look for printer marked as default
        for printer in data['printers']:
            if printer.get('printer_default'):
                return printer

        # If no default found, return first active printer
        for printer in data['printers']:
            if printer.get('is_active'):
                return printer

        # Fall back to first printer
        return data['printers'][0] if data['printers'] else None
