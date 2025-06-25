"""
MCP Proxy Engine - Main orchestrator for the MCP Proxy system.

This module provides the MCPProxyEngine class that coordinates all proxy
components and provides the main interface for the MCP proxy functionality.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass

from fastmcp import FastMCP
from fastmcp.tools import FunctionTool

from .config import ProxyConfig, load_proxy_config
from .discovery import ToolDiscoveryService, DiscoveryResult
from .generator import ProxyToolGenerator

logger = logging.getLogger(__name__)


@dataclass
class ProxyEngineStats:
    """Statistics for the proxy engine."""
    servers_configured: int
    servers_connected: int
    tools_discovered: int
    proxy_functions_generated: int
    tools_registered: int
    conflicts_detected: int
    uptime_seconds: float
    last_discovery: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary."""
        return {
            "servers_configured": self.servers_configured,
            "servers_connected": self.servers_connected,
            "tools_discovered": self.tools_discovered,
            "proxy_functions_generated": self.proxy_functions_generated,
            "tools_registered": self.tools_registered,
            "conflicts_detected": self.conflicts_detected,
            "uptime_seconds": self.uptime_seconds,
            "last_discovery": self.last_discovery
        }


class MCPProxyEngine:
    """
    Main orchestrator for the MCP Proxy Engine.
    
    Coordinates tool discovery, proxy generation, and integration with FastMCP.
    Provides a unified interface for managing external MCP server connections
    and proxying their tools.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the MCP Proxy Engine.
        
        Args:
            config_path: Path to configuration file. If None, uses default location.
        """
        self.config_path = config_path
        self.config: Optional[ProxyConfig] = None
        self.discovery_service: Optional[ToolDiscoveryService] = None
        self.proxy_generator: Optional[ProxyToolGenerator] = None
        
        # State tracking
        self._running = False
        self._start_time: Optional[float] = None
        self._registered_tools: Dict[str, FunctionTool] = {}
        self._fastmcp_server: Optional[FastMCP] = None
        
        # Background tasks
        self._discovery_task: Optional[asyncio.Task] = None
        self._health_task: Optional[asyncio.Task] = None
    
    async def initialize(self) -> None:
        """
        Initialize the proxy engine.
        
        Loads configuration, creates services, but doesn't start discovery.
        
        Raises:
            RuntimeError: If initialization fails
        """
        if self._running:
            logger.warning("Proxy engine is already running")
            return
        
        try:
            logger.info("Initializing MCP Proxy Engine")
            
            # Load configuration
            self.config = load_proxy_config(self.config_path)
            logger.info(f"Loaded configuration with {len(self.config.servers)} servers")
            
            # Create discovery service
            self.discovery_service = ToolDiscoveryService(self.config)
            logger.info("Created tool discovery service")
            
            # Create proxy generator
            self.proxy_generator = ProxyToolGenerator(self.discovery_service)
            logger.info("Created proxy tool generator")
            
            logger.info("MCP Proxy Engine initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize MCP Proxy Engine: {e}")
            raise RuntimeError(f"Proxy engine initialization failed: {e}")
    
    async def start(self) -> None:
        """
        Start the proxy engine.
        
        Begins tool discovery and starts background tasks.
        
        Raises:
            RuntimeError: If engine is not initialized or start fails
        """
        if not self.config or not self.discovery_service or not self.proxy_generator:
            raise RuntimeError("Proxy engine not initialized. Call initialize() first.")
        
        if self._running:
            logger.warning("Proxy engine is already running")
            return
        
        try:
            logger.info("Starting MCP Proxy Engine")
            self._start_time = time.time()
            self._running = True
            
            # Start discovery service
            await self.discovery_service.start()
            
            # Initial tool discovery and proxy generation
            await self._discover_and_generate_tools()
            
            # Start periodic discovery if configured
            if self.config.global_settings.discovery_interval > 0:
                self._discovery_task = asyncio.create_task(self._periodic_discovery_loop())
            
            logger.info("MCP Proxy Engine started successfully")
            
        except Exception as e:
            self._running = False
            logger.error(f"Failed to start MCP Proxy Engine: {e}")
            raise RuntimeError(f"Proxy engine start failed: {e}")
    
    async def stop(self) -> None:
        """Stop the proxy engine and cleanup resources."""
        if not self._running:
            return
        
        logger.info("Stopping MCP Proxy Engine")
        self._running = False
        
        # Cancel background tasks
        if self._discovery_task:
            self._discovery_task.cancel()
            try:
                await self._discovery_task
            except asyncio.CancelledError:
                pass
        
        if self._health_task:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass
        
        # Stop discovery service
        if self.discovery_service:
            await self.discovery_service.stop()
        
        # Clear registered tools
        self._registered_tools.clear()
        
        # Clear proxy functions
        if self.proxy_generator:
            self.proxy_generator.clear_all_functions()
        
        logger.info("MCP Proxy Engine stopped")
    
    async def register_proxy_tools(self, fastmcp_server: FastMCP) -> int:
        """
        Register all proxy tools with a FastMCP server.
        
        Args:
            fastmcp_server: The FastMCP server to register tools with
            
        Returns:
            Number of tools registered
            
        Raises:
            RuntimeError: If engine not running or registration fails
        """
        if not self._running or not self.proxy_generator:
            raise RuntimeError("Proxy engine not running")
        
        logger.info("Registering proxy tools with FastMCP server")
        self._fastmcp_server = fastmcp_server
        
        try:
            # Generate proxy functions for all discovered tools
            proxy_functions = self.proxy_generator.get_all_proxy_functions()
            
            registered_count = 0
            for tool_name, proxy_func in proxy_functions.items():
                try:
                    # Create FunctionTool from proxy function
                    function_tool = FunctionTool.from_function(proxy_func)
                    
                    # Register with FastMCP server
                    fastmcp_server.add_tool(function_tool)
                    
                    # Track registered tool
                    self._registered_tools[tool_name] = function_tool
                    registered_count += 1
                    
                    logger.debug(f"Registered proxy tool: {tool_name}")
                    
                except Exception as e:
                    logger.error(f"Failed to register proxy tool {tool_name}: {e}")
            
            logger.info(f"Registered {registered_count} proxy tools with FastMCP server")
            return registered_count
            
        except Exception as e:
            logger.error(f"Failed to register proxy tools: {e}")
            raise RuntimeError(f"Tool registration failed: {e}")
    
    async def refresh_tools(self, force_discovery: bool = False) -> DiscoveryResult:
        """
        Refresh tools from all servers and update proxy functions.
        
        Args:
            force_discovery: Force fresh discovery from all servers
            
        Returns:
            Combined discovery result
            
        Raises:
            RuntimeError: If engine not running
        """
        if not self._running or not self.discovery_service or not self.proxy_generator:
            raise RuntimeError("Proxy engine not running")
        
        logger.info("Refreshing proxy tools")
        
        try:
            # Discover tools from all servers
            discovery_results = await self.discovery_service.discover_all_tools(force_discovery)
            
            # Generate new proxy functions
            self.proxy_generator.refresh_proxy_functions()
            
            # Re-register tools if we have a FastMCP server
            if self._fastmcp_server:
                # Clear existing registrations
                for tool_name in list(self._registered_tools.keys()):
                    self._unregister_tool(tool_name)
                
                # Register new tools
                await self.register_proxy_tools(self._fastmcp_server)
            
            # Calculate combined result
            total_tools = sum(r.tools_discovered for r in discovery_results if r.success)
            successful_servers = sum(1 for r in discovery_results if r.success)
            
            combined_result = DiscoveryResult(
                server_name="all_servers",
                success=successful_servers > 0,
                tools_discovered=total_tools,
                discovery_time=max((r.discovery_time for r in discovery_results), default=0.0)
            )
            
            logger.info(f"Tool refresh completed: {total_tools} tools from {successful_servers} servers")
            return combined_result
            
        except Exception as e:
            logger.error(f"Failed to refresh tools: {e}")
            raise RuntimeError(f"Tool refresh failed: {e}")
    
    async def refresh_server_tools(self, server_name: str) -> DiscoveryResult:
        """
        Refresh tools from a specific server.
        
        Args:
            server_name: Name of the server to refresh
            
        Returns:
            Discovery result for the server
            
        Raises:
            RuntimeError: If engine not running
            ValueError: If server not found
        """
        if not self._running or not self.discovery_service:
            raise RuntimeError("Proxy engine not running")
        
        logger.info(f"Refreshing tools from server: {server_name}")
        
        try:
            # Refresh specific server
            result = await self.discovery_service.refresh_server(server_name)
            
            # Regenerate proxy functions for this server's tools
            server_tools = self.discovery_service.get_tools_by_server(server_name)
            for tool in server_tools:
                # Remove old proxy function if it exists
                if tool.name in self._registered_tools:
                    self._unregister_tool(tool.name)
                
                # Generate new proxy function
                proxy_func = self.proxy_generator.generate_proxy_function(tool)
                
                # Re-register if we have a FastMCP server
                if self._fastmcp_server:
                    function_tool = FunctionTool.from_function(proxy_func)
                    self._fastmcp_server.add_tool(function_tool)
                    self._registered_tools[tool.name] = function_tool
            
            logger.info(f"Refreshed {result.tools_discovered} tools from {server_name}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to refresh server {server_name}: {e}")
            raise
    
    def _unregister_tool(self, tool_name: str) -> bool:
        """
        Unregister a tool from FastMCP server.
        
        Args:
            tool_name: Name of the tool to unregister
            
        Returns:
            True if tool was unregistered, False if not found
        """
        if tool_name in self._registered_tools:
            # Note: FastMCP doesn't have a remove_tool method, so we just track it
            del self._registered_tools[tool_name]
            self.proxy_generator.remove_proxy_function(tool_name)
            logger.debug(f"Unregistered tool: {tool_name}")
            return True
        return False
    
    async def _discover_and_generate_tools(self) -> None:
        """Discover tools and generate proxy functions."""
        try:
            # Discover tools from all servers
            discovery_results = await self.discovery_service.discover_all_tools()
            
            # Generate proxy functions
            proxy_functions = self.proxy_generator.generate_all_proxy_functions()
            
            successful_servers = sum(1 for r in discovery_results if r.success)
            total_tools = len(proxy_functions)
            
            logger.info(f"Discovery completed: {total_tools} tools from {successful_servers} servers")
            
        except Exception as e:
            logger.error(f"Failed to discover and generate tools: {e}")
            raise
    
    async def _periodic_discovery_loop(self) -> None:
        """Periodic discovery loop."""
        interval = self.config.global_settings.discovery_interval
        
        while self._running:
            try:
                await asyncio.sleep(interval)
                
                if not self._running:
                    break
                
                logger.debug("Running periodic tool discovery")
                await self._discover_and_generate_tools()
                
                # Re-register tools if needed
                if self._fastmcp_server:
                    # Only register new tools, don't clear existing ones
                    proxy_functions = self.proxy_generator.get_all_proxy_functions()
                    for tool_name, proxy_func in proxy_functions.items():
                        if tool_name not in self._registered_tools:
                            try:
                                function_tool = FunctionTool.from_function(proxy_func)
                                self._fastmcp_server.add_tool(function_tool)
                                self._registered_tools[tool_name] = function_tool
                                logger.debug(f"Registered new tool: {tool_name}")
                            except Exception as e:
                                logger.error(f"Failed to register new tool {tool_name}: {e}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic discovery loop: {e}")
    
    def get_stats(self) -> ProxyEngineStats:
        """
        Get current proxy engine statistics.
        
        Returns:
            Current statistics
        """
        uptime = time.time() - self._start_time if self._start_time else 0.0
        
        # Get discovery stats
        discovery_stats = {}
        if self.discovery_service:
            discovery_stats = self.discovery_service.get_discovery_stats()
        
        # Get generator stats
        generator_stats = {}
        if self.proxy_generator:
            generator_stats = self.proxy_generator.get_generation_stats()
        
        return ProxyEngineStats(
            servers_configured=len(self.config.servers) if self.config else 0,
            servers_connected=discovery_stats.get("connected_servers", 0),
            tools_discovered=discovery_stats.get("total_tools", 0),
            proxy_functions_generated=generator_stats.get("total_functions", 0),
            tools_registered=len(self._registered_tools),
            conflicts_detected=discovery_stats.get("conflicts", 0),
            uptime_seconds=uptime,
            last_discovery=discovery_stats.get("last_updated")
        )
    
    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Tool information if found, None otherwise
        """
        if not self.discovery_service or not self.proxy_generator:
            return None
        
        tool = self.discovery_service.get_tool(tool_name)
        if not tool:
            return None
        
        metadata = self.proxy_generator.get_function_metadata(tool_name)
        param_info = self.proxy_generator.get_tool_parameter_info(tool_name)
        
        return {
            "name": tool.name,
            "description": tool.description,
            "server_name": tool.server_name,
            "original_name": tool.to_core_tool_format()["metadata"]["original_name"],
            "parameters": param_info,
            "registered": tool_name in self._registered_tools,
            "metadata": metadata.to_dict() if metadata else None
        }
    
    def get_all_tool_info(self) -> List[Dict[str, Any]]:
        """
        Get information about all discovered tools.
        
        Returns:
            List of tool information
        """
        if not self.discovery_service:
            return []
        
        tools = self.discovery_service.get_all_tools()
        return [self.get_tool_info(tool.name) for tool in tools]
    
    def get_server_info(self, server_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific server.
        
        Args:
            server_name: Name of the server
            
        Returns:
            Server information if found, None otherwise
        """
        if not self.discovery_service:
            return None
        
        server_info = self.discovery_service.get_server_info(server_name)
        server_tools = self.discovery_service.get_tools_by_server(server_name)
        
        if not server_info:
            return None
        
        return {
            "name": server_info.name,
            "version": server_info.version,
            "protocol_version": server_info.protocol_version,
            "capabilities": server_info.capabilities,
            "tools_count": len(server_tools),
            "tools": [tool.name for tool in server_tools]
        }
    
    def get_all_server_info(self) -> List[Dict[str, Any]]:
        """
        Get information about all configured servers.
        
        Returns:
            List of server information
        """
        if not self.config:
            return []
        
        server_info = []
        for server_name in self.config.servers.keys():
            info = self.get_server_info(server_name)
            if info:
                server_info.append(info)
        
        return server_info
    
    async def call_tool(self, tool_name: str, **kwargs) -> Any:
        """
        Call a proxy tool directly.
        
        Args:
            tool_name: Name of the tool to call
            **kwargs: Tool arguments
            
        Returns:
            Tool result
            
        Raises:
            RuntimeError: If engine not running
            ValueError: If tool not found
        """
        if not self._running or not self.discovery_service:
            raise RuntimeError("Proxy engine not running")
        
        return await self.discovery_service.call_tool(tool_name, kwargs)
    
    @property
    def is_running(self) -> bool:
        """Check if the proxy engine is running."""
        return self._running
    
    @property
    def is_initialized(self) -> bool:
        """Check if the proxy engine is initialized."""
        return self.config is not None
    
    def __str__(self) -> str:
        status = "running" if self._running else "stopped"
        return f"MCPProxyEngine({status}, {len(self._registered_tools)} tools)"
    
    def __repr__(self) -> str:
        return (f"MCPProxyEngine(running={self._running}, "
                f"tools={len(self._registered_tools)}, "
                f"config_path={self.config_path})")


# Convenience function for creating and starting the proxy engine
async def create_and_start_proxy_engine(config_path: Optional[str] = None) -> MCPProxyEngine:
    """
    Create and start a proxy engine with default configuration.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Started proxy engine
        
    Raises:
        RuntimeError: If creation or start fails
    """
    engine = MCPProxyEngine(config_path)
    await engine.initialize()
    await engine.start()
    return engine