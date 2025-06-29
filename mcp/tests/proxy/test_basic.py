"""
Basic tests for MCP Proxy components.

Simple tests that validate core functionality without requiring
full dependency stack or complex mocking.
"""

import pytest
import sys
from unittest.mock import Mock

# Mock external dependencies
sys.modules['fastmcp'] = Mock()
sys.modules['fastmcp.tools'] = Mock()

def test_imports():
    """Test that all proxy modules can be imported."""
    try:
        from app.proxy.config import ProxyConfig, ServerConfig, ServerSettings, GlobalSettings
        from app.proxy.discovery import ToolRegistry, ToolConflict, DiscoveryResult
        from app.proxy.client import MCPTool, MCPServerInfo, ConnectionState
        assert True  # If we get here, imports worked
    except ImportError as e:
        pytest.fail(f"Import failed: {e}")


def test_tool_registry_basic():
    """Test basic ToolRegistry functionality."""
    from app.proxy.discovery import ToolRegistry
    from app.proxy.client import MCPTool
    
    registry = ToolRegistry()
    
    # Test empty registry
    assert len(registry.tools_by_name) == 0
    assert len(registry.tools_by_server) == 0
    assert len(registry.conflicts) == 0
    
    # Create a mock tool
    tool = MCPTool(
        name="test_tool",
        description="A test tool",
        input_schema={"type": "object"},
        server_name="test_server"
    )
    
    # Add tool to registry
    final_name = registry.add_tool(tool)
    
    # Verify tool was added
    assert final_name == "test_tool"
    assert len(registry.tools_by_name) == 1
    assert "test_tool" in registry.tools_by_name
    assert registry.tools_by_name["test_tool"] == tool
    assert len(registry.tools_by_server["test_server"]) == 1


def test_tool_registry_with_prefix():
    """Test ToolRegistry with tool prefix."""
    from app.proxy.discovery import ToolRegistry
    from app.proxy.client import MCPTool
    
    registry = ToolRegistry()
    
    tool = MCPTool(
        name="test_tool",
        description="A test tool",
        input_schema={"type": "object"},
        server_name="test_server"
    )
    
    # Add tool with prefix
    final_name = registry.add_tool(tool, prefix="prefix_")
    
    # Verify tool was added with prefix
    assert final_name == "prefix_test_tool"
    assert "prefix_test_tool" in registry.tools_by_name
    assert tool.name == "prefix_test_tool"  # Tool name should be updated


def test_tool_conflict_detection():
    """Test tool name conflict detection."""
    from app.proxy.discovery import ToolRegistry, ToolConflict
    from app.proxy.client import MCPTool
    
    registry = ToolRegistry()
    
    # Add first tool
    tool1 = MCPTool(
        name="duplicate_tool",
        description="First tool",
        input_schema={"type": "object"},
        server_name="server1"
    )
    
    final_name1 = registry.add_tool(tool1)
    assert final_name1 == "duplicate_tool"
    
    # Add second tool with same name from different server
    tool2 = MCPTool(
        name="duplicate_tool",
        description="Second tool",
        input_schema={"type": "object"},
        server_name="server2"
    )
    
    final_name2 = registry.add_tool(tool2)
    
    # Should resolve conflict with server prefix
    assert final_name2 == "server2_duplicate_tool"
    assert len(registry.conflicts) == 1
    assert registry.conflicts[0].tool_name == "duplicate_tool"
    assert "server1" in registry.conflicts[0].servers
    assert "server2" in registry.conflicts[0].servers


def test_config_creation():
    """Test basic configuration creation."""
    from app.proxy.config import ProxyConfig, ServerConfig, ServerSettings, GlobalSettings
    
    # Test ServerSettings
    settings = ServerSettings(
        timeout=30,
        retry_attempts=3,
        retry_delay=5,
        tool_prefix="test_",
        health_check_interval=60
    )
    assert settings.timeout == 30
    assert settings.tool_prefix == "test_"
    
    # Test ServerConfig
    server_config = ServerConfig(
        name="test_server",
        enabled=True,
        description="Test server",
        type="stdio",
        settings=settings,
        command="test_command",
        args=[]
    )
    assert server_config.name == "test_server"
    assert server_config.enabled is True
    assert server_config.settings.tool_prefix == "test_"
    
    # Test GlobalSettings
    global_settings = GlobalSettings(
        discovery_interval=300,
        health_check_interval=60,
        max_concurrent_calls=10,
        enable_timeline_logging=True,
        log_level="INFO"
    )
    assert global_settings.discovery_interval == 300
    assert global_settings.enable_timeline_logging is True
    
    # Test ProxyConfig
    config = ProxyConfig()
    config.version = "1.0"
    config.servers = {"test_server": server_config}
    config.global_settings = global_settings
    
    assert config.version == "1.0"
    assert len(config.servers) == 1
    assert "test_server" in config.servers


def test_mcp_tool_creation():
    """Test MCPTool creation and properties."""
    from app.proxy.client import MCPTool
    
    tool = MCPTool(
        name="test_tool",
        description="A test tool for validation",
        input_schema={
            "type": "object",
            "properties": {
                "param1": {"type": "string"},
                "param2": {"type": "integer"}
            },
            "required": ["param1"]
        },
        server_name="test_server"
    )
    
    assert tool.name == "test_tool"
    assert tool.description == "A test tool for validation"
    assert tool.input_schema["type"] == "object"
    assert "param1" in tool.input_schema["properties"]
    assert tool.server_name == "test_server"


def test_discovery_result():
    """Test DiscoveryResult creation."""
    from app.proxy.discovery import DiscoveryResult
    from app.proxy.client import MCPServerInfo
    
    # Test successful result
    server_info = MCPServerInfo(
        name="test_server",
        version="1.0",
        protocol_version="1.0",
        capabilities={}
    )
    
    result = DiscoveryResult(
        server_name="test_server",
        success=True,
        tools_discovered=5,
        error_message=None,
        discovery_time=1.5,
        server_info=server_info
    )
    
    assert result.server_name == "test_server"
    assert result.success is True
    assert result.tools_discovered == 5
    assert result.error_message is None
    assert result.discovery_time == 1.5
    assert result.server_info == server_info
    
    # Test failed result
    failed_result = DiscoveryResult(
        server_name="failed_server",
        success=False,
        tools_discovered=0,
        error_message="Connection failed",
        discovery_time=0.0
    )
    
    assert failed_result.success is False
    assert failed_result.error_message == "Connection failed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])