"""
Unit tests for the MCP Proxy Tool Discovery Service.

Tests the ToolDiscoveryService class that handles discovering and cataloging
tools from external MCP servers, including conflict resolution and tool registry management.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, List, Any

# Mock the imports to avoid dependency issues during testing
import sys
from unittest.mock import Mock

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
        assert len(registry) == 0
        assert registry.is_empty()
        assert list(registry.get_all_tools()) == []
    
    def test_add_tool(self):
        """Test adding tools to the registry."""
        registry = ToolRegistry()
        
        tool = MCPTool(
            name="test_tool",
            description="A test tool",
            input_schema={"type": "object", "properties": {}},
            metadata={}
        )
        tool.server_name = "test_server"  # Add server name
        
        final_name = registry.add_tool(tool)
        assert final_name == "test_tool"
        assert len(registry.tools_by_name) == 1
        assert "test_tool" in registry.tools_by_name
        assert registry.tools_by_name["test_tool"] == tool
    
    def test_add_duplicate_tool_raises_conflict(self):
        """Test that adding duplicate tools raises ToolConflict."""
        registry = ToolRegistry()
        
        tool1 = ToolInfo(
            name="duplicate_tool",
            description="First tool",
            server_name="server1",
            original_name="duplicate_tool",
            schema={"type": "object"},
            metadata={}
        )
        
        tool2 = ToolInfo(
            name="duplicate_tool",
            description="Second tool",
            server_name="server2",
            original_name="duplicate_tool",
            schema={"type": "object"},
            metadata={}
        )
        
        registry.add_tool(tool1)
        
        with pytest.raises(ToolConflict) as exc_info:
            registry.add_tool(tool2)
        
        conflict = exc_info.value
        assert conflict.tool_name == "duplicate_tool"
        assert conflict.existing_server == "server1"
        assert conflict.new_server == "server2"
    
    def test_remove_tool(self):
        """Test removing tools from the registry."""
        registry = ToolRegistry()
        
        tool_info = ToolInfo(
            name="removable_tool",
            description="A removable tool",
            server_name="test_server",
            original_name="removable_tool",
            schema={"type": "object"},
            metadata={}
        )
        
        registry.add_tool(tool_info)
        assert registry.has_tool("removable_tool")
        
        removed = registry.remove_tool("removable_tool")
        assert removed == tool_info
        assert not registry.has_tool("removable_tool")
        assert len(registry) == 0
    
    def test_remove_nonexistent_tool(self):
        """Test removing a tool that doesn't exist."""
        registry = ToolRegistry()
        
        removed = registry.remove_tool("nonexistent_tool")
        assert removed is None
    
    def test_get_tools_by_server(self):
        """Test getting tools filtered by server."""
        registry = ToolRegistry()
        
        tool1 = ToolInfo(
            name="tool1",
            description="Tool from server1",
            server_name="server1",
            original_name="tool1",
            schema={"type": "object"},
            metadata={}
        )
        
        tool2 = ToolInfo(
            name="tool2",
            description="Tool from server2",
            server_name="server2",
            original_name="tool2",
            schema={"type": "object"},
            metadata={}
        )
        
        tool3 = ToolInfo(
            name="tool3",
            description="Another tool from server1",
            server_name="server1",
            original_name="tool3",
            schema={"type": "object"},
            metadata={}
        )
        
        registry.add_tool(tool1)
        registry.add_tool(tool2)
        registry.add_tool(tool3)
        
        server1_tools = list(registry.get_tools_by_server("server1"))
        assert len(server1_tools) == 2
        assert tool1 in server1_tools
        assert tool3 in server1_tools
        
        server2_tools = list(registry.get_tools_by_server("server2"))
        assert len(server2_tools) == 1
        assert tool2 in server2_tools
    
    def test_clear_server_tools(self):
        """Test clearing all tools from a specific server."""
        registry = ToolRegistry()
        
        tool1 = ToolInfo(
            name="tool1",
            description="Tool from server1",
            server_name="server1",
            original_name="tool1",
            schema={"type": "object"},
            metadata={}
        )
        
        tool2 = ToolInfo(
            name="tool2",
            description="Tool from server2",
            server_name="server2",
            original_name="tool2",
            schema={"type": "object"},
            metadata={}
        )
        
        registry.add_tool(tool1)
        registry.add_tool(tool2)
        assert len(registry) == 2
        
        removed_tools = registry.clear_server_tools("server1")
        assert len(removed_tools) == 1
        assert tool1 in removed_tools
        assert len(registry) == 1
        assert registry.has_tool("tool2")
        assert not registry.has_tool("tool1")


class TestToolDiscoveryService:
    """Test the ToolDiscoveryService class."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock proxy configuration."""
        return ProxyConfig(
            version="1.0",
            servers={
                "test_server": ServerConfig(
                    name="test_server",
                    enabled=True,
                    description="Test server",
                    type="stdio",
                    settings=ServerSettings(
                        timeout=30,
                        retry_attempts=3,
                        retry_delay=5,
                        tool_prefix="test_",
                        health_check_interval=60
                    ),
                    command="test_command",
                    args=[]
                )
            },
            global_settings=GlobalSettings(
                discovery_interval=300,
                health_check_interval=60,
                max_concurrent_calls=10,
                enable_timeline_logging=True,
                log_level="INFO"
            )
        )
    
    @pytest.fixture
    def discovery_service(self, mock_config):
        """Create a ToolDiscoveryService instance."""
        return ToolDiscoveryService(mock_config)
    
    def test_initialization(self, discovery_service, mock_config):
        """Test that discovery service initializes correctly."""
        assert discovery_service.config == mock_config
        assert isinstance(discovery_service.registry, ToolRegistry)
        assert discovery_service.registry.is_empty()
        assert not discovery_service.is_running
    
    @pytest.mark.asyncio
    async def test_start_discovery(self, discovery_service):
        """Test starting the discovery service."""
        with patch.object(discovery_service, '_discovery_loop') as mock_loop:
            mock_loop.return_value = AsyncMock()
            
            await discovery_service.start()
            assert discovery_service.is_running
            mock_loop.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stop_discovery(self, discovery_service):
        """Test stopping the discovery service."""
        # Start the service first
        discovery_service._running = True
        discovery_service._discovery_task = Mock()
        discovery_service._discovery_task.cancel = Mock()
        
        await discovery_service.stop()
        assert not discovery_service.is_running
        discovery_service._discovery_task.cancel.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_discover_tools_from_client(self, discovery_service):
        """Test discovering tools from a single MCP client."""
        # Create mock client
        mock_client = Mock(spec=MCPClient)
        mock_client.server_name = "test_server"
        mock_client.is_connected = True
        mock_client.get_server_info.return_value = MCPServerInfo(
            name="test_server",
            version="1.0",
            protocol_version="1.0",
            capabilities={}
        )
        
        # Mock tools from the client
        mock_tools = [
            MCPTool(
                name="tool1",
                description="First tool",
                input_schema={"type": "object", "properties": {"param1": {"type": "string"}}},
                metadata={}
            ),
            MCPTool(
                name="tool2",
                description="Second tool",
                input_schema={"type": "object", "properties": {"param2": {"type": "integer"}}},
                metadata={}
            )
        ]
        mock_client.list_tools = AsyncMock(return_value=mock_tools)
        
        # Discover tools
        result = await discovery_service._discover_tools_from_client(mock_client)
        
        assert isinstance(result, DiscoveryResult)
        assert result.server_name == "test_server"
        assert result.success is True
        assert len(result.tools_discovered) == 2
        assert result.error is None
        
        # Check that tools were added to registry with prefix
        assert discovery_service.registry.has_tool("test_tool1")
        assert discovery_service.registry.has_tool("test_tool2")
        
        tool1_info = discovery_service.registry.get_tool("test_tool1")
        assert tool1_info.original_name == "tool1"
        assert tool1_info.server_name == "test_server"
        assert tool1_info.description == "First tool"
    
    @pytest.mark.asyncio
    async def test_discover_tools_client_error(self, discovery_service):
        """Test handling errors when discovering tools from a client."""
        mock_client = Mock(spec=MCPClient)
        mock_client.server_name = "test_server"
        mock_client.is_connected = True
        mock_client.list_tools = AsyncMock(side_effect=Exception("Connection error"))
        
        result = await discovery_service._discover_tools_from_client(mock_client)
        
        assert isinstance(result, DiscoveryResult)
        assert result.server_name == "test_server"
        assert result.success is False
        assert result.tools_discovered == []
        assert "Connection error" in str(result.error)
    
    @pytest.mark.asyncio
    async def test_discover_tools_disconnected_client(self, discovery_service):
        """Test discovering tools from a disconnected client."""
        mock_client = Mock(spec=MCPClient)
        mock_client.server_name = "test_server"
        mock_client.is_connected = False
        
        result = await discovery_service._discover_tools_from_client(mock_client)
        
        assert isinstance(result, DiscoveryResult)
        assert result.server_name == "test_server"
        assert result.success is False
        assert result.tools_discovered == []
        assert "not connected" in str(result.error).lower()
    
    def test_resolve_tool_name_conflict_prefix(self, discovery_service):
        """Test resolving tool name conflicts using prefix strategy."""
        # Add a tool to create a conflict
        existing_tool = ToolInfo(
            name="conflicted_tool",
            description="Existing tool",
            server_name="server1",
            original_name="conflicted_tool",
            schema={"type": "object"},
            metadata={}
        )
        discovery_service.registry.add_tool(existing_tool)
        
        # Try to resolve conflict
        resolved_name = discovery_service._resolve_tool_name_conflict(
            "conflicted_tool", "server2", ConflictResolution.PREFIX
        )
        
        assert resolved_name == "server2_conflicted_tool"
    
    def test_resolve_tool_name_conflict_suffix(self, discovery_service):
        """Test resolving tool name conflicts using suffix strategy."""
        # Add a tool to create a conflict
        existing_tool = ToolInfo(
            name="conflicted_tool",
            description="Existing tool",
            server_name="server1",
            original_name="conflicted_tool",
            schema={"type": "object"},
            metadata={}
        )
        discovery_service.registry.add_tool(existing_tool)
        
        # Try to resolve conflict
        resolved_name = discovery_service._resolve_tool_name_conflict(
            "conflicted_tool", "server2", ConflictResolution.SUFFIX
        )
        
        assert resolved_name == "conflicted_tool_server2"
    
    def test_resolve_tool_name_conflict_skip(self, discovery_service):
        """Test resolving tool name conflicts using skip strategy."""
        # Add a tool to create a conflict
        existing_tool = ToolInfo(
            name="conflicted_tool",
            description="Existing tool",
            server_name="server1",
            original_name="conflicted_tool",
            schema={"type": "object"},
            metadata={}
        )
        discovery_service.registry.add_tool(existing_tool)
        
        # Try to resolve conflict
        resolved_name = discovery_service._resolve_tool_name_conflict(
            "conflicted_tool", "server2", ConflictResolution.SKIP
        )
        
        assert resolved_name is None
    
    def test_apply_tool_prefix(self, discovery_service):
        """Test applying tool prefix from server configuration."""
        # Test with prefix configured
        prefixed_name = discovery_service._apply_tool_prefix("tool_name", "test_server")
        assert prefixed_name == "test_tool_name"
        
        # Test with server that has no prefix configured
        discovery_service.config.servers["no_prefix_server"] = ServerConfig(
            name="no_prefix_server",
            enabled=True,
            description="Server without prefix",
            type="stdio",
            settings=ServerSettings(tool_prefix=""),
            command="test_command"
        )
        
        no_prefix_name = discovery_service._apply_tool_prefix("tool_name", "no_prefix_server")
        assert no_prefix_name == "tool_name"
    
    def test_validate_tool_schema(self, discovery_service):
        """Test tool schema validation."""
        # Valid schema
        valid_schema = {
            "type": "object",
            "properties": {
                "param1": {"type": "string"},
                "param2": {"type": "integer", "description": "A number"}
            },
            "required": ["param1"]
        }
        
        assert discovery_service._validate_tool_schema(valid_schema) is True
        
        # Invalid schema (missing type)
        invalid_schema = {
            "properties": {
                "param1": {"type": "string"}
            }
        }
        
        assert discovery_service._validate_tool_schema(invalid_schema) is False
        
        # Invalid schema (not a dict)
        assert discovery_service._validate_tool_schema("not a dict") is False
        assert discovery_service._validate_tool_schema(None) is False
    
    def test_get_discovery_stats(self, discovery_service):
        """Test getting discovery statistics."""
        # Add some tools to the registry
        tool1 = ToolInfo(
            name="tool1",
            description="Tool 1",
            server_name="server1",
            original_name="tool1",
            schema={"type": "object"},
            metadata={}
        )
        
        tool2 = ToolInfo(
            name="tool2",
            description="Tool 2",
            server_name="server2",
            original_name="tool2",
            schema={"type": "object"},
            metadata={}
        )
        
        discovery_service.registry.add_tool(tool1)
        discovery_service.registry.add_tool(tool2)
        
        stats = discovery_service.get_discovery_stats()
        
        assert stats["total_tools"] == 2
        assert stats["servers_with_tools"] == 2
        assert stats["is_running"] is False
        assert "server1" in stats["tools_by_server"]
        assert "server2" in stats["tools_by_server"]
        assert stats["tools_by_server"]["server1"] == 1
        assert stats["tools_by_server"]["server2"] == 1
    
    @pytest.mark.asyncio
    async def test_rediscover_tools(self, discovery_service):
        """Test rediscovering tools (clearing and discovering again)."""
        # Add some initial tools
        tool1 = ToolInfo(
            name="tool1",
            description="Tool 1",
            server_name="server1",
            original_name="tool1",
            schema={"type": "object"},
            metadata={}
        )
        discovery_service.registry.add_tool(tool1)
        assert len(discovery_service.registry) == 1
        
        # Mock clients for rediscovery
        mock_clients = {}
        
        with patch.object(discovery_service, '_discover_tools_from_client') as mock_discover:
            mock_discover.return_value = DiscoveryResult(
                server_name="server1",
                success=True,
                tools_discovered=["new_tool1", "new_tool2"],
                error=None,
                discovery_time=0.1
            )
            
            results = await discovery_service.rediscover_tools(mock_clients)
            
            assert len(results) == 0  # No clients provided
            # Registry should be cleared but no new tools added since no clients
            assert len(discovery_service.registry) == 0


class TestToolConflict:
    """Test the ToolConflict exception class."""
    
    def test_tool_conflict_creation(self):
        """Test creating a ToolConflict exception."""
        conflict = ToolConflict("duplicate_tool", "server1", "server2")
        
        assert conflict.tool_name == "duplicate_tool"
        assert conflict.existing_server == "server1"
        assert conflict.new_server == "server2"
        assert "duplicate_tool" in str(conflict)
        assert "server1" in str(conflict)
        assert "server2" in str(conflict)


class TestDiscoveryResult:
    """Test the DiscoveryResult dataclass."""
    
    def test_discovery_result_creation(self):
        """Test creating a DiscoveryResult."""
        result = DiscoveryResult(
            server_name="test_server",
            success=True,
            tools_discovered=["tool1", "tool2"],
            error=None,
            discovery_time=0.5
        )
        
        assert result.server_name == "test_server"
        assert result.success is True
        assert result.tools_discovered == ["tool1", "tool2"]
        assert result.error is None
        assert result.discovery_time == 0.5
    
    def test_discovery_result_failure(self):
        """Test creating a failed DiscoveryResult."""
        error = Exception("Discovery failed")
        result = DiscoveryResult(
            server_name="test_server",
            success=False,
            tools_discovered=[],
            error=error,
            discovery_time=0.0
        )
        
        assert result.server_name == "test_server"
        assert result.success is False
        assert result.tools_discovered == []
        assert result.error == error
        assert result.discovery_time == 0.0


if __name__ == "__main__":
    pytest.main([__file__])