"""
MCP Proxy Engine

A self-contained proxy system for connecting to external MCP servers,
discovering their tools, and integrating them into our tool ecosystem.
"""

from .config import ProxyConfig, ServerConfig, GlobalSettings

__all__ = [
    'ProxyConfig',
    'ServerConfig', 
    'GlobalSettings'
]