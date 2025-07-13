"""
Active Directory module for IntentVerse.
Mock Active Directory environment for user and group management.
"""

from .tool import ActiveDirectoryTool
from .schema import UI_SCHEMA

__all__ = ["ActiveDirectoryTool", "UI_SCHEMA"]