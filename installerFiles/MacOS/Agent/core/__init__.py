"""Core agent components"""

from .config import ConfigManager
from .crypto import CryptoManager
from .api_client import APIClient

# Lazy import of WegweiserAgent to avoid circular imports
# when running standalone scripts like register_device.py
def __getattr__(name):
    if name == 'WegweiserAgent':
        from .agent import WegweiserAgent
        return WegweiserAgent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ['WegweiserAgent', 'ConfigManager', 'CryptoManager', 'APIClient']

