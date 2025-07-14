"""
DHCP Services module for IntentVerse.
Mock DHCP server environment for dynamic IP address management.
"""

from .tool import DhcpServicesTool
from .schema import UI_SCHEMA

__all__ = ["DhcpServicesTool", "UI_SCHEMA"]