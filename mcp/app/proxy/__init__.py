"""
MCP Proxy Engine

A self-contained proxy system for connecting to external MCP servers,
discovering their tools, and integrating them into our tool ecosystem.
"""

from .config import ProxyConfig, ServerConfig, GlobalSettings
from .client import MCPClient, MCPMessage, ConnectionState, MCPTool, MCPServerInfo
from .discovery import (
    ToolDiscoveryService,
    ToolRegistry,
    ToolConflict,
    DiscoveryResult,
    ToolInfo,
)
from .generator import (
    ProxyToolGenerator,
    ParameterValidator,
    ResultProcessor,
    ProxyFunctionMetadata,
    ValidationError,
    ProcessingError,
)
from .engine import MCPProxyEngine, ProxyEngineStats, create_and_start_proxy_engine

__all__ = [
    "ProxyConfig",
    "ServerConfig",
    "GlobalSettings",
    "MCPClient",
    "MCPMessage",
    "ConnectionState",
    "MCPTool",
    "MCPServerInfo",
    "ToolDiscoveryService",
    "ToolRegistry",
    "ToolConflict",
    "DiscoveryResult",
    "ToolInfo",
    "ProxyToolGenerator",
    "ParameterValidator",
    "ResultProcessor",
    "ProxyFunctionMetadata",
    "ValidationError",
    "ProcessingError",
    "MCPProxyEngine",
    "ProxyEngineStats",
    "create_and_start_proxy_engine",
]
