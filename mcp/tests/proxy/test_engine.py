"""
Unit tests for the MCP Proxy Engine.

Tests the MCPProxyEngine class that orchestrates the entire proxy system,
including initialization, tool discovery, proxy generation, and FastMCP integration.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, List, Any, Optional

# Mock the imports to avoid dependency issues during testing
import sys
from unittest.mock import Mock

# Create mock modules to avoid import errors
sys.modules['fastmcp'] = Mock()
sys.modules['fastmcp.tools'] = Mock()

from fastmcp import FastMCP
from fastmcp.tools import FunctionTool

from app.proxy.engine import (
    MCPProxyEngine,
    ProxyEngineStats,
    create_and_start_proxy_engine
)
from app.proxy.config import ProxyConfig, ServerConfig, ServerSettings, GlobalSettings
from app.proxy.discovery import ToolDiscoveryService, ToolRegistry, ToolInfo
from app.proxy.generator import ProxyToolGenerator
from app.proxy.client import MCPClient


class TestProxyEngineStats:
    """Test the ProxyEngineStats dataclass."""
    
    def test_stats_creation(self):
        """Test creating ProxyEngineStats."""
        stats = ProxyEngineStats(
            servers_configured=3,
            servers_connected=2,
            tools_discovered=10,
            proxy_functions_generated=8,
            tools_registered=8,
            conflicts_detected=2,
            uptime_seconds=120.5,
            last_discovery=1234567890.0
        )
        
        assert stats.servers_configured == 3
        assert stats.servers_connected == 2
        assert stats.tools_discovered == 10
        assert stats.proxy_functions_generated == 8
        assert stats.tools_registered == 8
        assert stats.conflicts_detected == 2
        assert stats.uptime_seconds == 120.5
        assert stats.last_discovery == 1234567890.0
    
    def test_stats_to_dict(self):
        """Test converting stats to dictionary."""
        stats = ProxyEngineStats(
            servers_configured=2,
            servers_connected=1,
            tools_discovered=5,
            proxy_functions_generated=5,
            tools_registered=5,
            conflicts_detected=0,
            uptime_seconds=60.0
        )
        
        stats_dict = stats.to_dict()
        
        assert stats_dict["servers_configured"] == 2
        assert stats_dict["servers_connected"] == 1
        assert stats_dict["tools_discovered"] == 5
        assert stats_dict["proxy_functions_generated"] == 5
        assert stats_dict["tools_registered"] == 5
        assert stats_dict["conflicts_detected"] == 0
        assert stats_dict["uptime_seconds"] == 60.0
        assert stats_dict["last_discovery"] is None


class TestMCPProxyEngine:
    """Test the MCPProxyEngine class."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock proxy configuration."""
        config = ProxyConfig()
        config.version = "1.0"
        config.servers = {
            "test_server1": ServerConfig(
                name="test_server1",
                enabled=True,
                description="Test server 1",
                type="stdio",
                settings=ServerSettings(
                    timeout=30,
                    retry_attempts=3,
                    retry_delay=5,
                    tool_prefix="test1_",
                    health_check_interval=60
                ),
                command="test_command1",
                args=[]
            ),
            "test_server2": ServerConfig(
                name="test_server2",
                enabled=False,  # Disabled server
                description="Test server 2",
                type="sse",
                settings=ServerSettings(
                    timeout=60,
                    retry_attempts=5,
                    retry_delay=10,
                    tool_prefix="test2_",
                    health_check_interval=60
                ),
                url="http://localhost:3000/sse"
            )
        }
        config.global_settings = GlobalSettings(
            discovery_interval=300,
            health_check_interval=60,
            max_concurrent_calls=10,
            enable_timeline_logging=True,
            log_level="INFO"
        )
        config._loaded = True
        return config
    
    @pytest.fixture
    def engine(self):
        """Create an MCPProxyEngine instance."""
        return MCPProxyEngine()
    
    def test_initialization(self, engine):
        """Test that engine initializes correctly."""
        assert engine.config is None
        assert engine.discovery_service is None
        assert engine.proxy_generator is None
        assert not engine._running
        assert engine._start_time is None
        assert engine._registered_tools == {}
        assert engine._fastmcp_server is None
        assert engine._discovery_task is None
        assert engine._health_task is None
    
    @pytest.mark.asyncio
    async def test_initialize_success(self, engine, mock_config):
        """Test successful engine initialization."""
        with patch('app.proxy.engine.load_proxy_config', return_value=mock_config):
            await engine.initialize()
            
            assert engine.config == mock_config
            assert isinstance(engine.discovery_service, ToolDiscoveryService)
            assert isinstance(engine.proxy_generator, ProxyToolGenerator)
            assert not engine._running  # Not started yet
    
    @pytest.mark.asyncio
    async def test_initialize_already_running(self, engine, mock_config):
        """Test initializing when already running."""
        engine._running = True
        
        with patch('app.proxy.engine.load_proxy_config', return_value=mock_config):
            await engine.initialize()
            
            # Should not reinitialize
            assert engine.config is None
    
    @pytest.mark.asyncio
    async def test_initialize_config_error(self, engine):
        """Test initialization with configuration error."""
        with patch('app.proxy.engine.load_proxy_config', side_effect=Exception("Config error")):
            with pytest.raises(RuntimeError) as exc_info:
                await engine.initialize()
            
            assert "Config error" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_start_engine(self, engine, mock_config):
        """Test starting the proxy engine."""
        # Initialize first
        with patch('app.proxy.engine.load_proxy_config', return_value=mock_config):
            await engine.initialize()
        
        # Mock the discovery service start method
        with patch.object(engine.discovery_service, 'start') as mock_discovery_start, \
             patch.object(engine, '_discover_and_generate_tools') as mock_discover:
            
            mock_discovery_start.return_value = AsyncMock()
            mock_discover.return_value = AsyncMock()
            
            await engine.start()
            
            assert engine._running
            assert engine._start_time is not None
            mock_discovery_start.assert_called_once()
            mock_discover.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_start_engine_not_initialized(self, engine):
        """Test starting engine without initialization."""
        with pytest.raises(RuntimeError) as exc_info:
            await engine.start()
        
        assert "not initialized" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_start_engine_already_running(self, engine, mock_config):
        """Test starting engine when already running."""
        # Initialize and start
        with patch('app.proxy.engine.load_proxy_config', return_value=mock_config):
            await engine.initialize()
        
        engine._running = True
        
        await engine.start()  # Should not raise error, just log warning
        assert engine._running
    
    @pytest.mark.asyncio
    async def test_stop_engine(self, engine, mock_config):
        """Test stopping the proxy engine."""
        # Initialize and start
        with patch('app.proxy.engine.load_proxy_config', return_value=mock_config):
            await engine.initialize()
        
        # Mock background tasks
        mock_discovery_task = Mock()
        mock_discovery_task.cancel = Mock()
        mock_health_task = Mock()
        mock_health_task.cancel = Mock()
        
        engine._running = True
        engine._discovery_task = mock_discovery_task
        engine._health_task = mock_health_task
        
        # Mock discovery service stop method
        with patch.object(engine.discovery_service, 'stop') as mock_discovery_stop:
            mock_discovery_stop.return_value = AsyncMock()
            
            await engine.stop()
            
            assert not engine._running
            mock_discovery_task.cancel.assert_called_once()
            mock_health_task.cancel.assert_called_once()
            mock_discovery_stop.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stop_engine_not_running(self, engine):
        """Test stopping engine when not running."""
        await engine.stop()  # Should not raise error
        assert not engine._running
    
    @pytest.mark.asyncio
    async def test_register_proxy_tools(self, engine, mock_config):
        """Test registering proxy tools with FastMCP server."""
        # Initialize engine
        with patch('app.proxy.engine.load_proxy_config', return_value=mock_config):
            await engine.initialize()
        
        # Set engine as running
        engine._running = True
        
        # Mock FastMCP server
        mock_server = Mock()
        mock_server.add_tool = Mock()
        
        # Mock proxy generator with some functions
        mock_functions = {
            "test_tool1": Mock(),
            "test_tool2": Mock()
        }
        engine.proxy_generator.get_all_proxy_functions = Mock(return_value=mock_functions)
        
        # Mock FunctionTool.from_function
        with patch('app.proxy.engine.FunctionTool') as mock_function_tool:
            mock_tool1 = Mock()
            mock_tool2 = Mock()
            mock_function_tool.from_function.side_effect = [mock_tool1, mock_tool2]
            
            # Register tools
            count = await engine.register_proxy_tools(mock_server)
            
            assert count == 2
            assert mock_server.add_tool.call_count == 2
            assert len(engine._registered_tools) == 2
            assert engine._fastmcp_server == mock_server
    
    @pytest.mark.asyncio
    async def test_register_proxy_tools_not_initialized(self, engine):
        """Test registering tools when engine not running."""
        mock_server = Mock()
        
        with pytest.raises(RuntimeError) as exc_info:
            await engine.register_proxy_tools(mock_server)
        
        assert "not running" in str(exc_info.value).lower()
    
    def test_get_stats(self, engine, mock_config):
        """Test getting engine statistics."""
        # Test when not initialized
        stats = engine.get_stats()
        assert stats.servers_configured == 0
        assert stats.servers_connected == 0
        assert stats.uptime_seconds == 0.0
        
        # Initialize engine
        with patch('app.proxy.engine.load_proxy_config', return_value=mock_config):
            asyncio.run(engine.initialize())
        
        # Mock some state
        engine._start_time = time.time() - 60  # Started 60 seconds ago
        engine._registered_tools = {"tool1": Mock(), "tool2": Mock()}
        
        # Mock discovery service stats
        mock_discovery_stats = {
            "connected_servers": 1,
            "total_tools": 5,
            "conflicts": 0,
            "last_updated": time.time()
        }
        engine.discovery_service.get_discovery_stats = Mock(return_value=mock_discovery_stats)
        
        # Mock generator stats - store reference first
        original_generator = engine.proxy_generator
        mock_generator_stats = {
            "total_functions": 5
        }
        mock_get_generation_stats = Mock(return_value=mock_generator_stats)
        original_generator.get_generation_stats = mock_get_generation_stats
        
        stats = engine.get_stats()
        
        assert stats.servers_configured == 2  # From mock_config
        assert stats.servers_connected == 1   # From mock discovery stats
        assert stats.tools_discovered == 5
        assert stats.proxy_functions_generated == 5
        assert stats.tools_registered == 2
        assert 59 < stats.uptime_seconds < 61  # Approximately 60 seconds
    
    def test_is_running_property(self, engine):
        """Test the is_running property."""
        assert not engine.is_running
        
        engine._running = True
        assert engine.is_running
    
    def test_get_tool_info(self, engine, mock_config):
        """Test getting information about a specific tool."""
        # Initialize engine
        with patch('app.proxy.engine.load_proxy_config', return_value=mock_config):
            asyncio.run(engine.initialize())
        
        # Mock tool in registry
        mock_tool_info = ToolInfo(
            name="test_tool",
            description="A test tool",
            server_name="test_server",
            original_name="original_tool",
            schema={"type": "object"},
            metadata={"version": "1.0"}
        )
        
        engine.discovery_service.registry.get_tool = Mock(return_value=mock_tool_info)
        
        tool_info = engine.get_tool_info("test_tool")
        
        assert tool_info is not None
        assert tool_info["name"] == "test_tool"
        assert tool_info["description"] == "A test tool"
        assert tool_info["server_name"] == "test_server"
        assert tool_info["original_name"] == "original_tool"
    
    def test_get_tool_info_not_found(self, engine, mock_config):
        """Test getting info for non-existent tool."""
        # Initialize engine
        with patch('app.proxy.engine.load_proxy_config', return_value=mock_config):
            asyncio.run(engine.initialize())
        
        engine.discovery_service.registry.get_tool = Mock(return_value=None)
        
        tool_info = engine.get_tool_info("nonexistent_tool")
        assert tool_info is None
    
    def test_get_tool_info_not_initialized(self, engine):
        """Test getting tool info when not initialized."""
        tool_info = engine.get_tool_info("test_tool")
        assert tool_info is None
    
    def test_get_all_tool_info(self, engine, mock_config):
        """Test getting information about all tools."""
        # Initialize engine
        with patch('app.proxy.engine.load_proxy_config', return_value=mock_config):
            asyncio.run(engine.initialize())
        
        # Mock tools in discovery service
        mock_tools = [
            ToolInfo(
                name="tool1",
                description="First tool",
                server_name="server1",
                original_name="tool1",
                schema={"type": "object"},
                metadata={}
            ),
            ToolInfo(
                name="tool2",
                description="Second tool",
                server_name="server2",
                original_name="tool2",
                schema={"type": "object"},
                metadata={}
            )
        ]
        
        engine.discovery_service.get_all_tools = Mock(return_value=mock_tools)
        
        # Mock get_tool_info for each tool
        def mock_get_tool_info(tool_name):
            for tool in mock_tools:
                if tool.name == tool_name:
                    return {
                        "name": tool.name,
                        "description": tool.description,
                        "server_name": tool.server_name,
                        "original_name": tool.original_name,
                        "parameters": {},
                        "registered": False,
                        "metadata": None
                    }
            return None
        
        engine.get_tool_info = Mock(side_effect=mock_get_tool_info)
        
        all_tools = engine.get_all_tool_info()
        
        assert len(all_tools) == 2
        assert all_tools[0]["name"] == "tool1"
        assert all_tools[1]["name"] == "tool2"
    
    def test_get_all_tool_info_not_initialized(self, engine):
        """Test getting all tool info when not initialized."""
        all_tools = engine.get_all_tool_info()
        assert all_tools == []
    
    @pytest.mark.asyncio
    async def test_create_clients(self, engine, mock_config):
        """Test that discovery service creates clients for enabled servers."""
        # Initialize engine
        with patch('app.proxy.engine.load_proxy_config', return_value=mock_config):
            await engine.initialize()
        
        # Check that discovery service was created with the config
        assert engine.discovery_service is not None
        assert engine.discovery_service.config == mock_config
        
        # The discovery service handles client creation internally
        # We can verify it was initialized with the correct config
        assert len(mock_config.servers) == 2
        assert "test_server1" in mock_config.servers
        assert "test_server2" in mock_config.servers
    
    @pytest.mark.asyncio
    async def test_discovery_loop(self, engine, mock_config):
        """Test the periodic discovery loop."""
        # Initialize engine
        with patch('app.proxy.engine.load_proxy_config', return_value=mock_config):
            await engine.initialize()
        
        # Mock discovery and generation methods
        engine._discover_and_generate_tools = AsyncMock()
        
        # Set up the discovery interval to be very short for testing
        engine.config.global_settings.discovery_interval = 0.01
        
        # Mock sleep to control the loop
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            # Make sleep return immediately for the first call, then raise CancelledError
            call_count = 0
            async def mock_sleep_side_effect(delay):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return  # First sleep returns immediately
                else:
                    raise asyncio.CancelledError()  # Stop the loop
            
            mock_sleep.side_effect = mock_sleep_side_effect
            
            # Run the loop
            engine._running = True
            
            try:
                await engine._periodic_discovery_loop()
            except asyncio.CancelledError:
                pass
            
            # Verify discovery was called
            engine._discover_and_generate_tools.assert_called()
    
    @pytest.mark.asyncio
    async def test_health_check_loop(self, engine, mock_config):
        """Test the health check loop (handled by discovery service)."""
        # Initialize engine
        with patch('app.proxy.engine.load_proxy_config', return_value=mock_config):
            await engine.initialize()
        
        # Test the backward compatibility method
        task = await engine._start_health_check_loop()
        
        # Should return a task (even if it's a dummy task)
        assert task is not None
        assert asyncio.iscoroutine(task) or hasattr(task, '__await__')
        
        # Cancel the task to clean up
        if hasattr(task, 'cancel'):
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    
    def test_repr(self, engine):
        """Test string representation of engine."""
        repr_str = repr(engine)
        assert "MCPProxyEngine" in repr_str
        assert "running=False" in repr_str
        
        engine._running = True
        repr_str = repr(engine)
        assert "running=True" in repr_str


class TestCreateAndStartProxyEngine:
    """Test the create_and_start_proxy_engine utility function."""
    
    @pytest.mark.asyncio
    async def test_create_and_start_success(self):
        """Test successfully creating and starting a proxy engine."""
        mock_config = ProxyConfig()
        mock_config.version = "1.0"
        mock_config.servers = {}
        mock_config.global_settings = GlobalSettings()
        mock_config._loaded = True
        
        with patch('app.proxy.engine.load_proxy_config', return_value=mock_config), \
             patch.object(MCPProxyEngine, 'initialize') as mock_init, \
             patch.object(MCPProxyEngine, 'start') as mock_start:
            
            mock_init.return_value = AsyncMock()
            mock_start.return_value = AsyncMock()
            
            engine = await create_and_start_proxy_engine()
            
            assert isinstance(engine, MCPProxyEngine)
            mock_init.assert_called_once()
            mock_start.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_and_start_with_config_path(self):
        """Test creating and starting with custom config path."""
        mock_config = ProxyConfig()
        mock_config.version = "1.0"
        mock_config.servers = {}
        mock_config.global_settings = GlobalSettings()
        mock_config._loaded = True
        
        with patch('app.proxy.engine.load_proxy_config', return_value=mock_config) as mock_load, \
             patch.object(MCPProxyEngine, 'initialize') as mock_init, \
             patch.object(MCPProxyEngine, 'start') as mock_start:
            
            mock_init.return_value = AsyncMock()
            mock_start.return_value = AsyncMock()
            
            engine = await create_and_start_proxy_engine("/custom/config/path.json")
            
            assert isinstance(engine, MCPProxyEngine)
            # Verify the custom config path was used
            assert engine.config_path == "/custom/config/path.json"
    
    @pytest.mark.asyncio
    async def test_create_and_start_initialization_error(self):
        """Test handling initialization errors."""
        with patch.object(MCPProxyEngine, 'initialize', side_effect=Exception("Init failed")):
            
            with pytest.raises(Exception) as exc_info:
                await create_and_start_proxy_engine()
            
            assert "Init failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_create_and_start_start_error(self):
        """Test handling start errors."""
        with patch.object(MCPProxyEngine, 'initialize') as mock_init, \
             patch.object(MCPProxyEngine, 'start', side_effect=Exception("Start failed")):
            
            mock_init.return_value = AsyncMock()
            
            with pytest.raises(Exception) as exc_info:
                await create_and_start_proxy_engine()
            
            assert "Start failed" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__])