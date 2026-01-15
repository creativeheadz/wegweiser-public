"""
MCP Client for C2 - sends MCP requests to agents via NATS
"""

from .nats_client import NATSMCPClient

__all__ = ["NATSMCPClient"]
