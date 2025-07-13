"""
Azure Entra ID module for IntentVerse.
Mock Azure Entra ID (formerly Azure AD) environment for cloud identity management.
"""

from .tool import AzureEntraIdTool
from .schema import UI_SCHEMA

__all__ = ["AzureEntraIdTool", "UI_SCHEMA"]