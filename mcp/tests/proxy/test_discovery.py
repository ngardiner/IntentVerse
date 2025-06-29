"""
Unit tests for the MCP Proxy Tool Discovery Service.

Tests the ToolDiscoveryService class that handles discovering and cataloging
tools from external MCP servers, including conflict resolution and tool registry management.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, List, Any

# Mock the imports to avoid dependency issues during testing
import sys
import os
from unittest.mock import Mock

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Create mock modules to avoid import errors
sys.modules['fastmcp'] = Mock()
sys.modules['fastmcp.tools'] = Mock()

from app.proxy.discovery import (
    ToolDiscoveryService, 
    ToolRegistry, 
    ToolConflict, 
    DiscoveryResult
)
from app.proxy.client import MCPClient, MCPTool, MCPServerInfo, ConnectionState
from app.proxy.config import ProxyConfig, ServerConfig, ServerSettings, GlobalSettings


class TestToolRegistry:
    """Test the ToolRegistry class."""
    
    def test_registry_initialization(self):
        """Test that registry initializes correctly."""
        registry = ToolRegistry()
        assert len(registry.tools_by_name) == 0
        assert len(registry.tools_by_server) == 0
        assert len(registry.conflicts) == 0
    
    def test_add_tool(self):
        """Test adding tools to the registry."""
        registry = ToolRegistry()
        
        tool = MCPTool(
            name="test_tool",
            description="A test tool",
            input_schema={"type": "object", "properties": {}},
            server_name="test_server"
        )
        
        final_name = registry.add_tool(tool)
        assert final_name == "test_tool"
        assert len(registry.tools_by_name) == 1
        assert "test_tool" in registry.tools_by_name
        assert registry.tools_by_name["test_tool"] == tool
    
    def test_add_duplicate_tool_conflict_resolution(self):
        """Test that adding duplicate tools resolves conflicts."""
        registry = ToolRegistry()
        
        # Add first tool
        tool1 = MCPTool(
            name="duplicate_tool",
            description="First tool",
            input_schema={"type": "object"},
            server_name="server1"
        )
        
        # Add second tool with same name from different server
        tool2 = MCPTool(
            name="duplicate_tool",
            description="Second tool",
            input_schema={"type": "object"},
            server_name="server2"
        )
        
        # Add first tool - should succeed with original name
        name1 = registry.add_tool(tool1)
        assert name1 == "duplicate_tool"
        
        # Add second tool - should be renamed to avoid conflict
        name2 = registry.add_tool(tool2)
        assert name2 == "server2_duplicate_tool"
        
        # Check that conflict was recorded
        assert len(registry.conflicts) == 1
        conflict = registry.conflicts[0]
        assert conflict.tool_name == "duplicate_tool"
        assert "server1" in conflict.servers
        assert "server2" in conflict.servers
    
    def test_remove_server_tools(self):
        """Test removing all tools from a server."""
        registry = ToolRegistry()
        
        # Add tools from two different servers
        tool1 = MCPTool(
            name="tool1",
            description="Tool from server1",
            input_schema={"type": "object"},
            server_name="server1"
        )
        
        tool2 = MCPTool(
            name="tool2",
            description="Tool from server2",
            input_schema={"type": "object"},
            server_name="server2"
        )
        
        registry.add_tool(tool1)
        registry.add_tool(tool2)
        
        # Verify tools were added
        assert len(registry.tools_by_name) == 2
        assert len(registry.tools_by_server["server1"]) == 1
        assert len(registry.tools_by_server["server2"]) == 1
        
        # Remove tools from server1
        count = registry.remove_server_tools("server1")
        
        # Verify tool was removed
        assert count == 1
        assert "tool1" not in registry.tools_by_name
        assert "tool2" in registry.tools_by_name
        assert "server1" not in registry.tools_by_server or len(registry.tools_by_server["server1"]) == 0
        assert len(registry.tools_by_server["server2"]) == 1
    
    def test_get_tools_by_server(self):
        """Test getting tools by server."""
        registry = ToolRegistry()
        
        # Add tools from different servers
        tool1 = MCPTool(
            name="tool1",
            description="Tool from server1",
            input_schema={"type": "object"},
            server_name="server1"
        )
        
        tool2 = MCPTool(
            name="tool2",
            description="Tool from server2",
            input_schema={"type": "object"},
            server_name="server2"
        )
        
        tool3 = MCPTool(
            name="tool3",
            description="Another tool from server1",
            input_schema={"type": "object"},
            server_name="server1"
        )
        
        registry.add_tool(tool1)
        registry.add_tool(tool2)
        registry.add_tool(tool3)
        
        # Check tools by server
        server1_tools = registry.tools_by_server["server1"]
        assert len(server1_tools) == 2
        assert any(t.name == "tool1" for t in server1_tools)
        assert any(t.name == "tool3" for t in server1_tools)
        
        server2_tools = registry.tools_by_server["server2"]
        assert len(server2_tools) == 1
        assert server2_tools[0].name == "tool2"
    
    # Note: clear_server_tools doesn't exist in the actual implementation
    # It's been replaced by remove_server_tools which we already tested


class TestToolDiscoveryService:
    """Test the ToolDiscoveryService class."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock proxy configuration."""
        config = ProxyConfig()
        config.version = "1.0"
        
        # Create server settings
        settings = ServerSettings(
            timeout=30,
            retry_attempts=3,
            retry_delay=5,
            tool_prefix="test_",
            health_check_interval=60
        )
        
        # Create server config
        server_config = ServerConfig(
            name="test_server",
            enabled=True,
            description="Test server",
            type="stdio",
            settings=settings,
            command="test_command",
            args=[]
        )
        
        # Add server to config
        config.servers = {"test_server": server_config}
        
        # Set global settings
        config.global_settings = GlobalSettings(
            discovery_interval=300,
            health_check_interval=60,
            max_concurrent_calls=10,
            enable_timeline_logging=True,
            log_level="INFO"
        )
        
        return config
    
    @pytest.fixture
    def discovery_service(self, mock_config):
        """Create a ToolDiscoveryService instance."""
        return ToolDiscoveryService(mock_config)
    
    def test_initialization(self, discovery_service, mock_config):
        """Test that discovery service initializes correctly."""
        assert discovery_service.config == mock_config
        assert isinstance(discovery_service.registry, ToolRegistry)
        assert len(discovery_service.registry.tools_by_name) == 0
        assert not discovery_service._running
    
    @pytest.mark.asyncio
    async def test_start_discovery(self, discovery_service):
        """Test starting the discovery service."""
        with patch.object(discovery_service, 'discover_all_tools') as mock_discover:
            mock_discover.return_value = AsyncMock()
            
            await discovery_service.start()
            assert discovery_service._running
            mock_discover.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stop_discovery(self, discovery_service):
        """Test stopping the discovery service."""
        # Start the service first
        discovery_service._running = True
        discovery_service._health_check_task = AsyncMock()
        discovery_service._health_check_task.cancel = Mock()
        
        await discovery_service.stop()
        assert not discovery_service._running
        discovery_service._health_check_task.cancel.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_discover_tools_from_client(self, discovery_service):
        """Test discovering tools from a single MCP client."""
        # Create mock client
        mock_client = Mock(spec=MCPClient)
        mock_client.server_name = "test_server"
        mock_client.is_connected = True
        mock_client.get_server_info = AsyncMock(return_value=MCPServerInfo(
            name="test_server",
            version="1.0",
            protocol_version="1.0",
            capabilities={}
        ))
        
        # Mock tools from the client
        mock_tools = [
            MCPTool(
                name="tool1",
                description="First tool",
                input_schema={"type": "object", "properties": {"param1": {"type": "string"}}},
                server_name="test_server"
            ),
            MCPTool(
                name="tool2",
                description="Second tool",
                input_schema={"type": "object", "properties": {"param2": {"type": "integer"}}},
                server_name="test_server"
            )
        ]
        mock_client.discover_tools = AsyncMock(return_value=mock_tools)
        mock_client.connect = AsyncMock()
        mock_client.initialize_server = AsyncMock()
        
        # Discover tools
        start_time = time.time()
        result = await discovery_service._discover_server_tools("test_server", mock_client)
        
        assert isinstance(result, DiscoveryResult)
        assert result.server_name == "test_server"
        assert result.success is True
        assert result.tools_discovered == 2
        assert result.error_message is None
        assert result.discovery_time > 0
        
        # Check that tools were added to registry with prefix
        assert "test_tool1" in discovery_service.registry.tools_by_name
        assert "test_tool2" in discovery_service.registry.tools_by_name
        
        tool1 = discovery_service.registry.tools_by_name["test_tool1"]
        assert tool1.name == "test_tool1"
        assert tool1.server_name == "test_server"
        assert tool1.description == "First tool"
    
    @pytest.mark.asyncio
    async def test_discover_tools_client_error(self, discovery_service):
        """Test handling errors when discovering tools from a client."""
        mock_client = Mock(spec=MCPClient)
        mock_client.server_name = "test_server"
        mock_client.is_connected = True
        mock_client.discover_tools = AsyncMock(side_effect=Exception("Connection error"))
        mock_client.get_server_info = AsyncMock(side_effect=Exception("Info error"))
        
        result = await discovery_service._discover_server_tools("test_server", mock_client)
        
        assert isinstance(result, DiscoveryResult)
        assert result.server_name == "test_server"
        assert result.success is False
        assert result.tools_discovered == 0
        assert "Connection error" in result.error_message
    
    @pytest.mark.asyncio
    async def test_discover_tools_disconnected_client(self, discovery_service):
        """Test discovering tools from a disconnected client."""
        mock_client = Mock(spec=MCPClient)
        mock_client.server_name = "test_server"
        mock_client.is_connected = False
        mock_client.connect = AsyncMock(side_effect=Exception("Connection failed"))
        mock_client.initialize_server = AsyncMock()
        
        result = await discovery_service._discover_server_tools("test_server", mock_client)
        
        assert isinstance(result, DiscoveryResult)
        assert result.server_name == "test_server"
        assert result.success is False
        assert result.tools_discovered == 0
        assert "not connected" in result.error_message.lower()
    
    # Note: The actual implementation doesn't have a separate conflict resolution method
    # Conflicts are handled directly in the add_tool method of ToolRegistry
    # We already tested this behavior in test_add_duplicate_tool_conflict_resolution
    
    def test_get_server_config(self, discovery_service):
        """Test getting server configuration."""
        # Test with existing server
        server_config = discovery_service.config.get_server("test_server")
        assert server_config is not None
        assert server_config.name == "test_server"
        assert server_config.settings.tool_prefix == "test_"
        
        # Test with nonexistent server
        unknown_config = discovery_service.config.get_server("unknown_server")
        assert unknown_config is None
    
    # Note: The actual implementation doesn't have a separate schema validation method
    # Schema validation is handled by the MCPTool class constructor
    
    # Note: The actual implementation doesn't have a get_discovery_stats method
    
    @pytest.mark.asyncio
    async def test_discover_all_tools(self, discovery_service):
        """Test discovering tools from all clients."""
        # Add a mock client
        mock_client = Mock(spec=MCPClient)
        mock_client.server_name = "test_server"
        mock_client.is_connected = True
        discovery_service.clients = {"test_server": mock_client}
        
        # Mock the _discover_server_tools method
        with patch.object(discovery_service, '_discover_server_tools') as mock_discover:
            mock_discover.return_value = DiscoveryResult(
                server_name="test_server",
                success=True,
                tools_discovered=2,
                error_message=None,
                discovery_time=0.1,
                server_info=MCPServerInfo(
                    name="test_server",
                    version="1.0",
                    protocol_version="1.0",
                    capabilities={}
                )
            )
            
            results = await discovery_service.discover_all_tools()
            
            assert len(results) == 1
            assert results[0].server_name == "test_server"
            assert results[0].success is True
            assert results[0].tools_discovered == 2
            mock_discover.assert_called_once_with("test_server", mock_client)


class TestToolConflict:
    """Test the ToolConflict class."""
    
    def test_tool_conflict_creation(self):
        """Test creating a ToolConflict."""
        servers = ["server1", "server2"]
        conflict = ToolConflict(
            tool_name="duplicate_tool",
            servers=servers,
            resolution="server_prefix"
        )
        
        assert conflict.tool_name == "duplicate_tool"
        assert conflict.servers == servers
        assert conflict.resolution == "server_prefix"
        assert "duplicate_tool" in str(conflict)
        assert "2" in str(conflict)  # Number of servers


class TestDiscoveryResult:
    """Test the DiscoveryResult dataclass."""
    
    def test_discovery_result_creation(self):
        """Test creating a DiscoveryResult."""
        server_info = MCPServerInfo(
            name="test_server",
            version="1.0",
            protocol_version="1.0",
            capabilities={}
        )
        
        result = DiscoveryResult(
            server_name="test_server",
            success=True,
            tools_discovered=2,
            error_message=None,
            discovery_time=0.5,
            server_info=server_info
        )
        
        assert result.server_name == "test_server"
        assert result.success is True
        assert result.tools_discovered == 2
        assert result.error_message is None
        assert result.discovery_time == 0.5
        assert result.server_info == server_info
        assert "test_server" in str(result)
        assert "2 tools" in str(result)
    
    def test_discovery_result_failure(self):
        """Test creating a failed DiscoveryResult."""
        result = DiscoveryResult(
            server_name="test_server",
            success=False,
            tools_discovered=0,
            error_message="Discovery failed",
            discovery_time=0.0
        )
        
        assert result.server_name == "test_server"
        assert result.success is False
        assert result.tools_discovered == 0
        assert result.error_message == "Discovery failed"
        assert result.discovery_time == 0.0
        assert "FAILED" in str(result)
        assert "Discovery failed" in str(result)


if __name__ == "__main__":
    pytest.main([__file__])