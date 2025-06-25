"""
MCP Proxy Engine

A self-contained proxy system for connecting to external MCP servers,
discovering their tools, and integrating them into our tool ecosystem.
"""

from .config import ProxyConfig, ServerConfig, GlobalSettings
from .client import MCPClient, MCPMessage, ConnectionState, MCPTool, MCPServerInfo
from .discovery import ToolDiscoveryService, ToolRegistry, ToolConflict, DiscoveryResult
from .generator import ProxyToolGenerator, ParameterValidator, ResultProcessor, ProxyFunctionMetadata

__all__ = [
    'ProxyConfig',
    'ServerConfig', 
    'GlobalSettings',
    'MCPClient',
    'MCPMessage',
    'ConnectionState',
    'MCPTool',
    'MCPServerInfo',
    'ToolDiscoveryService',
    'ToolRegistry',
    'ToolConflict',
    'DiscoveryResult',
    'ProxyToolGenerator',
    'ParameterValidator',
    'ResultProcessor',
    'ProxyFunctionMetadata'
]