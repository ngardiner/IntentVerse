"""
Integration tests for the MCP Proxy Engine.

Tests the complete proxy system working together, including real MCP client
connections, tool discovery, proxy generation, and FastMCP integration.
"""

import pytest
import asyncio
import json
import tempfile
import os
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, List, Any

# Mock the imports to avoid dependency issues during testing
import sys
from unittest.mock import Mock

# Create mock modules to avoid import errors
sys.modules['fastmcp'] = Mock()
sys.modules['fastmcp.tools'] = Mock()

from fastmcp import FastMCP
from fastmcp.tools import FunctionTool

from app.proxy.engine import MCPProxyEngine, create_and_start_proxy_engine
from app.proxy.config import ProxyConfig, ServerConfig, ServerSettings, GlobalSettings
from app.proxy.client import MCPClient, MCPTool, MCPServerInfo, ConnectionState
from app.proxy.discovery import ToolDiscoveryService, ToolRegistry
from app.proxy.generator import ProxyToolGenerator


class MockMCPServer:
    """Mock MCP server for testing."""
    
    def __init__(self, name: str, tools: List[Dict[str, Any]]):
        self.name = name
        self.tools = tools
        self.call_count = 0
        self.last_call = None
    
    async def list_tools(self) -> List[MCPTool]:
        """Return the mock tools."""
        return [
            MCPTool(
                name=tool["name"],
                description=tool["description"],
                input_schema=tool["schema"],
                server_name=self.name
            )
            for tool in self.tools
        ]
    
    async def call_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Mock tool execution."""
        self.call_count += 1
        self.last_call = {"tool_name": tool_name, "parameters": parameters}
        
        # Find the tool
        tool = next((t for t in self.tools if t["name"] == tool_name), None)
        if not tool:
            return {
                "success": False,
                "error": f"Tool '{tool_name}' not found"
            }
        
        # Simulate tool execution
        return {
            "success": True,
            "result": {
                "message": f"Executed {tool_name} with parameters {parameters}",
                "server": self.name
            }
        }


class TestProxyEngineIntegration:
    """Integration tests for the complete proxy engine."""
    
    @pytest.fixture
    def temp_config_file(self):
        """Create a temporary configuration file."""
        config_data = {
            "version": "1.0",
            "mcpServers": {
                "test-server": {
                    "enabled": True,
                    "description": "Test MCP server",
                    "type": "stdio",
                    "command": "echo",
                    "args": ["hello"],
                    "env": {},
                    "settings": {
                        "timeout": 30,
                        "retry_attempts": 3,
                        "retry_delay": 5,
                        "tool_prefix": "test_",
                        "health_check_interval": 60
                    }
                }
            },
            "global_settings": {
                "discovery_interval": 300,
                "health_check_interval": 60,
                "max_concurrent_calls": 10,
                "enable_timeline_logging": True,
                "log_level": "INFO"
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_file = f.name
        
        yield temp_file
        
        # Cleanup
        os.unlink(temp_file)
    
    @pytest.fixture
    def mock_server_tools(self):
        """Define mock tools for testing."""
        return [
            {
                "name": "echo_tool",
                "description": "Echoes the input message",
                "schema": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "description": "Message to echo"}
                    },
                    "required": ["message"]
                }
            },
            {
                "name": "math_tool",
                "description": "Performs basic math operations",
                "schema": {
                    "type": "object",
                    "properties": {
                        "operation": {"type": "string", "enum": ["add", "subtract", "multiply", "divide"]},
                        "a": {"type": "number", "description": "First number"},
                        "b": {"type": "number", "description": "Second number"}
                    },
                    "required": ["operation", "a", "b"]
                }
            }
        ]
    
    @pytest.mark.asyncio
    async def test_full_proxy_engine_lifecycle(self, temp_config_file, mock_server_tools):
        """Test the complete proxy engine lifecycle."""
        # Create mock MCP server
        mock_server = MockMCPServer("test-server", mock_server_tools)
        
        # Create proxy engine
        engine = MCPProxyEngine(temp_config_file)
        
        # Mock the MCP client creation to return our mock server
        def mock_client_factory(server_config):
            mock_client = Mock(spec=MCPClient)
            mock_client.server_name = server_config.name
            mock_client.is_connected = True
            mock_client.connect = AsyncMock(return_value=True)
            mock_client.disconnect = AsyncMock()
            mock_client.initialize_server = AsyncMock(return_value=MCPServerInfo(
                name=server_config.name,
                version="1.0",
                protocol_version="1.0",
                capabilities={}
            ))
            
            # Create the tools synchronously for the mock
            tools = []
            for tool_data in mock_server.tools:
                tools.append(MCPTool(
                    name=tool_data["name"],
                    description=tool_data["description"],
                    input_schema=tool_data["schema"],
                    server_name=mock_server.name
                ))
            
            mock_client.discover_tools = AsyncMock(return_value=tools)
            mock_client.call_tool = AsyncMock(side_effect=mock_server.call_tool)
            mock_client.is_healthy = AsyncMock(return_value=True)
            mock_client.get_server_info = Mock(return_value=MCPServerInfo(
                name=server_config.name,
                version="1.0",
                protocol_version="1.0",
                capabilities={}
            ))
            return mock_client
        
        with patch('app.proxy.discovery.MCPClient', side_effect=mock_client_factory):
            # Initialize the engine
            await engine.initialize()
            assert engine.config is not None
            assert engine.discovery_service is not None
            assert engine.proxy_generator is not None
            
            # Start the engine
            await engine.start()
            assert engine.is_running
            
            # Wait a bit for discovery to complete
            await asyncio.sleep(0.1)
            
            # Check that tools were discovered
            stats = engine.get_stats()
            assert stats.servers_configured == 1
            assert stats.servers_connected == 1
            assert stats.tools_discovered >= 2  # Our mock tools
            
            # Create a FastMCP server and register proxy tools
            fastmcp_server = Mock()
            fastmcp_server.add_tool = Mock()
            
            tools_registered = await engine.register_proxy_tools(fastmcp_server)
            assert tools_registered == 2  # Our two mock tools
            
            # Verify tools were registered (we can't easily check names due to mocking)
            assert tools_registered == 2  # Already checked above
            assert fastmcp_server.add_tool.call_count == 2
            
            # Test calling a proxy tool
            proxy_functions = engine.proxy_generator.generate_all_proxy_functions()
            
            # Debug: Print all available proxy functions
            print(f"DEBUG: Available proxy functions: {list(proxy_functions.keys())}")
            
            # The tool name should be prefixed with "test_" from the config
            expected_tool_name = "test_test_echo_tool"  # Server prefix + tool prefix applied
            assert expected_tool_name in proxy_functions, f"Expected tool {expected_tool_name} not found in {list(proxy_functions.keys())}"
            
            echo_func = proxy_functions[expected_tool_name]
            result = await echo_func(message="Hello, World!")
            
            print(f"DEBUG: Result = {result}")
            print(f"DEBUG: Result type = {type(result)}")
            print(f"DEBUG: Result keys = {result.keys() if isinstance(result, dict) else 'Not a dict'}")
            
            assert result["success"] is True
            assert "Hello, World!" in result["result"]["message"]
            assert result["metadata"]["tool_name"] == "echo_tool"  # Original tool name
            assert result["metadata"]["server_name"] == "test-server"
            
            # Verify the mock server was called
            assert mock_server.call_count == 1
            assert mock_server.last_call["tool_name"] == "echo_tool"
            assert mock_server.last_call["parameters"]["message"] == "Hello, World!"
            
            # Stop the engine
            await engine.stop()
            assert not engine.is_running
    
    @pytest.mark.asyncio
    async def test_proxy_engine_with_tool_conflicts(self, temp_config_file):
        """Test proxy engine handling tool name conflicts."""
        # Create two mock servers with conflicting tool names
        server1_tools = [
            {
                "name": "common_tool",
                "description": "Tool from server 1",
                "schema": {"type": "object", "properties": {"param1": {"type": "string"}}}
            }
        ]
        
        server2_tools = [
            {
                "name": "common_tool",
                "description": "Tool from server 2",
                "schema": {"type": "object", "properties": {"param2": {"type": "integer"}}}
            }
        ]
        
        mock_server1 = MockMCPServer("server1", server1_tools)
        mock_server2 = MockMCPServer("server2", server2_tools)
        
        # Update config to have two servers
        config_data = {
            "version": "1.0",
            "mcpServers": {
                "server1": {
                    "enabled": True,
                    "description": "First test server",
                    "type": "stdio",
                    "command": "echo",
                    "args": [],
                    "settings": {"tool_prefix": "s1_"}
                },
                "server2": {
                    "enabled": True,
                    "description": "Second test server",
                    "type": "stdio",
                    "command": "echo",
                    "args": [],
                    "settings": {"tool_prefix": "s2_"}
                }
            },
            "global_settings": {
                "discovery_interval": 300,
                "health_check_interval": 60,
                "max_concurrent_calls": 10,
                "enable_timeline_logging": True,
                "log_level": "INFO"
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            conflict_config_file = f.name
        
        try:
            engine = MCPProxyEngine(conflict_config_file)
            
            # Mock client creation for both servers
            def mock_client_factory(server_config):
                if server_config.name == "server1":
                    mock_server = mock_server1
                else:
                    mock_server = mock_server2
                
                mock_client = Mock(spec=MCPClient)
                mock_client.server_name = server_config.name
                mock_client.is_connected = True
                mock_client.connect = AsyncMock(return_value=True)
                mock_client.disconnect = AsyncMock()
                mock_client.initialize_server = AsyncMock(return_value=MCPServerInfo(
                    name=server_config.name,
                    version="1.0",
                    protocol_version="1.0",
                    capabilities={}
                ))
                
                # Create the tools synchronously for the mock
                tools = []
                for tool_data in mock_server.tools:
                    tools.append(MCPTool(
                        name=tool_data["name"],
                        description=tool_data["description"],
                        input_schema=tool_data["schema"],
                        server_name=mock_server.name
                    ))
                
                mock_client.discover_tools = AsyncMock(return_value=tools)
                mock_client.call_tool = AsyncMock(side_effect=mock_server.call_tool)
                mock_client.is_healthy = AsyncMock(return_value=True)
                mock_client.get_server_info = Mock(return_value=MCPServerInfo(
                    name=server_config.name,
                    version="1.0",
                    protocol_version="1.0",
                    capabilities={}
                ))
                return mock_client
            
            with patch('app.proxy.discovery.MCPClient', side_effect=mock_client_factory):
                await engine.initialize()
                await engine.start()
                
                # Wait for discovery
                await asyncio.sleep(0.1)
                
                # Check that both tools were registered with conflict resolution
                proxy_functions = engine.proxy_generator.generate_all_proxy_functions()
                
                # Debug: Print all available proxy functions
                print(f"DEBUG: Available proxy functions for conflict test: {list(proxy_functions.keys())}")
                
                # With conflict resolution, tools should be named with server prefix
                expected_tool1 = "s1_s1_common_tool"  # Server prefix + tool prefix applied
                expected_tool2 = "s2_s2_common_tool"  # Server prefix + tool prefix applied
                assert expected_tool1 in proxy_functions, f"Expected tool {expected_tool1} not found in {list(proxy_functions.keys())}"
                assert expected_tool2 in proxy_functions, f"Expected tool {expected_tool2} not found in {list(proxy_functions.keys())}"
                
                # Test calling both tools
                result1 = await proxy_functions[expected_tool1](param1="test")
                result2 = await proxy_functions[expected_tool2](param2=42)
                
                assert result1["success"] is True
                assert result2["success"] is True
                assert result1["result"]["server"] == "server1"
                assert result2["result"]["server"] == "server2"
                
                await engine.stop()
        
        finally:
            os.unlink(conflict_config_file)
    
    @pytest.mark.asyncio
    async def test_proxy_engine_with_disabled_server(self, temp_config_file):
        """Test proxy engine with some servers disabled."""
        # Update config to have one enabled and one disabled server
        config_data = {
            "version": "1.0",
            "mcpServers": {
                "enabled-server": {
                    "enabled": True,
                    "description": "Enabled test server",
                    "type": "stdio",
                    "command": "echo",
                    "args": [],
                    "settings": {"tool_prefix": "enabled_"}
                },
                "disabled-server": {
                    "enabled": False,
                    "description": "Disabled test server",
                    "type": "stdio",
                    "command": "echo",
                    "args": [],
                    "settings": {"tool_prefix": "disabled_"}
                }
            },
            "global_settings": {
                "discovery_interval": 300,
                "health_check_interval": 60,
                "max_concurrent_calls": 10,
                "enable_timeline_logging": True,
                "log_level": "INFO"
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            disabled_config_file = f.name
        
        try:
            engine = MCPProxyEngine(disabled_config_file)
            
            # Mock tools for enabled server only
            enabled_tools = [
                {
                    "name": "enabled_tool",
                    "description": "Tool from enabled server",
                    "schema": {"type": "object", "properties": {"param": {"type": "string"}}}
                }
            ]
            
            mock_enabled_server = MockMCPServer("enabled-server", enabled_tools)
            
            def mock_client_factory(server_config):
                # Should only be called for enabled server
                assert server_config.name == "enabled-server"
                
                mock_client = Mock(spec=MCPClient)
                mock_client.server_name = server_config.name
                mock_client.is_connected = True
                mock_client.connect = AsyncMock(return_value=True)
                mock_client.disconnect = AsyncMock()
                mock_client.initialize_server = AsyncMock(return_value=MCPServerInfo(
                    name=server_config.name,
                    version="1.0",
                    protocol_version="1.0",
                    capabilities={}
                ))
                
                # Create the tools synchronously for the mock
                tools = []
                for tool_data in mock_enabled_server.tools:
                    tools.append(MCPTool(
                        name=tool_data["name"],
                        description=tool_data["description"],
                        input_schema=tool_data["schema"],
                        server_name=mock_enabled_server.name
                    ))
                
                mock_client.discover_tools = AsyncMock(return_value=tools)
                mock_client.call_tool = AsyncMock(side_effect=mock_enabled_server.call_tool)
                mock_client.is_healthy = AsyncMock(return_value=True)
                mock_client.get_server_info = Mock(return_value=MCPServerInfo(
                    name=server_config.name,
                    version="1.0",
                    protocol_version="1.0",
                    capabilities={}
                ))
                return mock_client
            
            with patch('app.proxy.discovery.MCPClient', side_effect=mock_client_factory):
                await engine.initialize()
                await engine.start()
                
                # Wait for discovery
                await asyncio.sleep(0.1)
                
                # Check stats - should only have one server
                stats = engine.get_stats()
                assert stats.servers_configured == 2  # Both in config
                assert stats.servers_connected == 1   # Only enabled one connected
                
                # Check that only enabled server's tools are available
                proxy_functions = engine.proxy_generator.generate_all_proxy_functions()
                
                # Debug: Print all available proxy functions
                print(f"DEBUG: Available proxy functions for disabled server test: {list(proxy_functions.keys())}")
                
                expected_tool = "enabled_enabled_enabled_tool"  # Server prefix + tool prefix applied
                assert expected_tool in proxy_functions, f"Expected tool {expected_tool} not found in {list(proxy_functions.keys())}"
                assert len(proxy_functions) == 1  # Only one tool
                
                await engine.stop()
        
        finally:
            os.unlink(disabled_config_file)
    
    @pytest.mark.asyncio
    async def test_proxy_engine_connection_failure(self, temp_config_file):
        """Test proxy engine handling connection failures."""
        engine = MCPProxyEngine(temp_config_file)
        
        # Mock client that fails to connect
        def mock_failing_client_factory(server_config):
            mock_client = Mock(spec=MCPClient)
            mock_client.server_name = server_config.name
            mock_client.is_connected = False
            mock_client.connect = AsyncMock(return_value=False)  # Connection fails
            mock_client.disconnect = AsyncMock()
            mock_client.is_healthy = AsyncMock(return_value=False)
            return mock_client
        
        with patch('app.proxy.discovery.MCPClient', side_effect=mock_failing_client_factory):
            await engine.initialize()
            await engine.start()
            
            # Wait for connection attempts
            await asyncio.sleep(0.1)
            
            # Check stats - should show no connected servers
            stats = engine.get_stats()
            assert stats.servers_configured == 1
            assert stats.servers_connected == 0
            assert stats.tools_discovered == 0
            
            # No proxy functions should be generated
            proxy_functions = engine.proxy_generator.generate_all_proxy_functions()
            assert len(proxy_functions) == 0
            
            await engine.stop()
    
    @pytest.mark.asyncio
    async def test_create_and_start_proxy_engine_integration(self, temp_config_file, mock_server_tools):
        """Test the create_and_start_proxy_engine utility function."""
        mock_server = MockMCPServer("test-server", mock_server_tools)
        
        # Mock client creation
        def mock_client_factory(server_config):
            mock_client = Mock(spec=MCPClient)
            mock_client.server_name = server_config.name
            mock_client.is_connected = True
            mock_client.connect = AsyncMock(return_value=True)
            mock_client.disconnect = AsyncMock()
            mock_client.initialize_server = AsyncMock(return_value=MCPServerInfo(
                name=server_config.name,
                version="1.0",
                protocol_version="1.0",
                capabilities={}
            ))
            
            # Create the tools synchronously for the mock
            tools = []
            for tool_data in mock_server.tools:
                tools.append(MCPTool(
                    name=tool_data["name"],
                    description=tool_data["description"],
                    input_schema=tool_data["schema"],
                    server_name=mock_server.name
                ))
            
            mock_client.discover_tools = AsyncMock(return_value=tools)
            mock_client.call_tool = AsyncMock(side_effect=mock_server.call_tool)
            mock_client.is_healthy = AsyncMock(return_value=True)
            mock_client.get_server_info = Mock(return_value=MCPServerInfo(
                name=server_config.name,
                version="1.0",
                protocol_version="1.0",
                capabilities={}
            ))
            return mock_client
        
        with patch('app.proxy.discovery.MCPClient', side_effect=mock_client_factory):
            # Create and start engine using utility function
            engine = await create_and_start_proxy_engine(temp_config_file)
            
            assert engine.is_running
            assert engine.config is not None
            
            # Wait for discovery
            await asyncio.sleep(0.1)
            
            # Verify it's working
            stats = engine.get_stats()
            assert stats.servers_connected == 1
            assert stats.tools_discovered >= 2
            
            # Clean up
            await engine.stop()
    
    @pytest.mark.asyncio
    async def test_proxy_tool_parameter_validation_integration(self, temp_config_file):
        """Test parameter validation in the complete proxy system."""
        # Create a tool with strict parameter validation
        strict_tools = [
            {
                "name": "strict_tool",
                "description": "Tool with strict parameter validation",
                "schema": {
                    "type": "object",
                    "properties": {
                        "email": {
                            "type": "string",
                            "pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
                        },
                        "age": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 150
                        }
                    },
                    "required": ["email", "age"]
                }
            }
        ]
        
        mock_server = MockMCPServer("test-server", strict_tools)
        engine = MCPProxyEngine(temp_config_file)
        
        def mock_client_factory(server_config):
            mock_client = Mock(spec=MCPClient)
            mock_client.server_name = server_config.name
            mock_client.is_connected = True
            mock_client.connect = AsyncMock(return_value=True)
            mock_client.disconnect = AsyncMock()
            mock_client.initialize_server = AsyncMock(return_value=MCPServerInfo(
                name=server_config.name,
                version="1.0",
                protocol_version="1.0",
                capabilities={}
            ))
            
            # Create the tools synchronously for the mock
            tools = []
            for tool_data in mock_server.tools:
                tools.append(MCPTool(
                    name=tool_data["name"],
                    description=tool_data["description"],
                    input_schema=tool_data["schema"],
                    server_name=mock_server.name
                ))
            
            mock_client.discover_tools = AsyncMock(return_value=tools)
            mock_client.call_tool = AsyncMock(side_effect=mock_server.call_tool)
            mock_client.is_healthy = AsyncMock(return_value=True)
            mock_client.get_server_info = Mock(return_value=MCPServerInfo(
                name=server_config.name,
                version="1.0",
                protocol_version="1.0",
                capabilities={}
            ))
            return mock_client
        
        with patch('app.proxy.discovery.MCPClient', side_effect=mock_client_factory):
            await engine.initialize()
            await engine.start()
            
            # Wait for discovery
            await asyncio.sleep(0.1)
            
            proxy_functions = engine.proxy_generator.generate_all_proxy_functions()
            
            # Debug: Print all available proxy functions
            print(f"DEBUG: Available proxy functions for strict validation test: {list(proxy_functions.keys())}")
            
            expected_tool = "test_test_strict_tool"  # Server prefix + tool prefix applied
            assert expected_tool in proxy_functions, f"Expected tool {expected_tool} not found in {list(proxy_functions.keys())}"
            strict_func = proxy_functions[expected_tool]
            
            # Test valid parameters
            result = await strict_func(email="test@example.com", age=25)
            assert result["success"] is True
            
            # Test invalid email format
            try:
                await strict_func(email="invalid-email", age=25)
                assert False, "Should have raised ValidationError"
            except Exception as e:
                assert "email" in str(e).lower() or "pattern" in str(e).lower()
            
            # Test age out of range
            try:
                await strict_func(email="test@example.com", age=200)
                assert False, "Should have raised ValidationError"
            except Exception as e:
                assert "age" in str(e).lower() or "maximum" in str(e).lower()
            
            # Test missing required parameter
            try:
                await strict_func(email="test@example.com")
                assert False, "Should have raised ValidationError"
            except Exception as e:
                assert "required" in str(e).lower() or "age" in str(e).lower()
            
            await engine.stop()


if __name__ == "__main__":
    pytest.main([__file__])