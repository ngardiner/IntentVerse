"""
Tests for MCP Client functionality.
"""

import asyncio
import json
import pytest
import subprocess
import tempfile
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call
from typing import Dict, Any

import httpx
import respx

from app.proxy.config import ServerConfig, ServerSettings
from app.proxy.client import (
    MCPClient, 
    MCPMessage, 
    MCPTool, 
    MCPServerInfo,
    ConnectionState,
    StdioTransport,
    SSETransport,
    HTTPTransport
)


class TestMCPMessage:
    """Test MCPMessage class."""

    def test_create_request_message(self):
        """Test creating a request message."""
        message = MCPMessage(
            id=1,
            method="tools/list",
            params={"filter": "test"}
        )
        
        assert message.jsonrpc == "2.0"
        assert message.id == 1
        assert message.method == "tools/list"
        assert message.params == {"filter": "test"}
        assert message.is_request() is True
        assert message.is_response() is False
        assert message.is_notification() is False

    def test_create_response_message(self):
        """Test creating a response message."""
        message = MCPMessage(
            id=1,
            result={"tools": []}
        )
        
        assert message.id == 1
        assert message.result == {"tools": []}
        assert message.is_request() is False
        assert message.is_response() is True
        assert message.is_notification() is False

    def test_create_notification_message(self):
        """Test creating a notification message."""
        message = MCPMessage(
            method="notifications/initialized"
        )
        
        assert message.method == "notifications/initialized"
        assert message.id is None
        assert message.is_request() is False
        assert message.is_response() is False
        assert message.is_notification() is True

    def test_to_dict(self):
        """Test converting message to dictionary."""
        message = MCPMessage(
            id=1,
            method="test",
            params={"key": "value"}
        )
        
        result = message.to_dict()
        expected = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "test",
            "params": {"key": "value"}
        }
        
        assert result == expected

    def test_from_dict(self):
        """Test creating message from dictionary."""
        data = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "test"}
        }
        
        message = MCPMessage.from_dict(data)
        assert message.jsonrpc == "2.0"
        assert message.id == 2
        assert message.method == "tools/call"
        assert message.params == {"name": "test"}


class TestMCPTool:
    """Test MCPTool class."""

    @pytest.fixture
    def sample_tool_data(self):
        """Sample tool data from MCP server."""
        return {
            "name": "read_file",
            "description": "Read contents of a file",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file"
                    },
                    "encoding": {
                        "type": "string",
                        "description": "File encoding",
                        "default": "utf-8"
                    },
                    "max_size": {
                        "type": "integer",
                        "description": "Maximum file size"
                    }
                },
                "required": ["path"]
            }
        }

    def test_create_from_mcp_response(self, sample_tool_data):
        """Test creating tool from MCP response."""
        tool = MCPTool.from_mcp_response(sample_tool_data, "test-server")
        
        assert tool.name == "read_file"
        assert tool.description == "Read contents of a file"
        assert tool.server_name == "test-server"
        assert tool.input_schema == sample_tool_data["inputSchema"]

    def test_validation_errors(self):
        """Test tool validation errors."""
        # Empty name
        with pytest.raises(ValueError, match="Tool name cannot be empty"):
            MCPTool(name="", description="test", input_schema={}, server_name="test")
        
        # Empty description
        with pytest.raises(ValueError, match="Tool description cannot be empty"):
            MCPTool(name="test", description="", input_schema={}, server_name="test")
        
        # Invalid schema
        with pytest.raises(ValueError, match="Tool input_schema must be a dictionary"):
            MCPTool(name="test", description="test", input_schema="invalid", server_name="test")

    def test_to_core_tool_format(self, sample_tool_data):
        """Test converting to core tool format."""
        tool = MCPTool.from_mcp_response(sample_tool_data, "test-server")
        core_format = tool.to_core_tool_format("fs_")
        
        assert core_format["name"] == "fs_read_file"
        assert core_format["description"] == "Read contents of a file"
        
        # Check parameters
        params = {p["name"]: p for p in core_format["parameters"]}
        
        # Path parameter (required)
        assert "path" in params
        assert params["path"]["annotation"] == "str"
        assert params["path"]["required"] is True
        assert params["path"]["description"] == "Path to the file"
        
        # Encoding parameter (optional with default)
        assert "encoding" in params
        assert params["encoding"]["annotation"] == "str"
        assert params["encoding"]["required"] is False
        assert params["encoding"]["default"] == "utf-8"
        
        # Max size parameter (integer type)
        assert "max_size" in params
        assert params["max_size"]["annotation"] == "int"
        assert params["max_size"]["required"] is False
        
        # Check metadata
        metadata = core_format["metadata"]
        assert metadata["source"] == "mcp_proxy"
        assert metadata["server_name"] == "test-server"
        assert metadata["original_name"] == "read_file"

    def test_type_mapping(self):
        """Test JSON Schema to Python type mapping."""
        tool_data = {
            "name": "type_test",
            "description": "Test type mapping",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "str_param": {"type": "string"},
                    "int_param": {"type": "integer"},
                    "float_param": {"type": "number"},
                    "bool_param": {"type": "boolean"},
                    "list_param": {"type": "array"},
                    "dict_param": {"type": "object"},
                    "unknown_param": {"type": "unknown"}
                }
            }
        }
        
        tool = MCPTool.from_mcp_response(tool_data, "test-server")
        core_format = tool.to_core_tool_format()
        
        params = {p["name"]: p["annotation"] for p in core_format["parameters"]}
        
        assert params["str_param"] == "str"
        assert params["int_param"] == "int"
        assert params["float_param"] == "float"
        assert params["bool_param"] == "bool"
        assert params["list_param"] == "list"
        assert params["dict_param"] == "dict"
        assert params["unknown_param"] == "str"  # Default fallback


class TestMCPServerInfo:
    """Test MCPServerInfo class."""

    def test_create_from_mcp_response(self):
        """Test creating server info from MCP response."""
        server_data = {
            "name": "filesystem-server",
            "version": "1.0.0",
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {},
                "resources": {}
            }
        }
        
        server_info = MCPServerInfo.from_mcp_response(server_data, "fs-server")
        
        assert server_info.name == "filesystem-server"
        assert server_info.version == "1.0.0"
        assert server_info.protocol_version == "2024-11-05"
        assert server_info.capabilities == {"tools": {}, "resources": {}}

    def test_defaults(self):
        """Test default values."""
        server_data = {}
        server_info = MCPServerInfo.from_mcp_response(server_data, "test-server")
        
        assert server_info.name == "test-server"  # Falls back to server name
        assert server_info.version == "unknown"
        assert server_info.protocol_version == "2024-11-05"
        assert server_info.capabilities == {}


class TestStdioTransport:
    """Test StdioTransport class."""

    @pytest.fixture
    def stdio_config(self):
        """Create stdio server config."""
        settings = ServerSettings(timeout=10)
        return ServerConfig(
            name="test-stdio",
            enabled=True,
            description="Test stdio server",
            type="stdio",
            settings=settings,
            command="/bin/echo",
            args=["test"]
        )

    def test_create_transport(self, stdio_config):
        """Test creating stdio transport."""
        transport = StdioTransport(stdio_config)
        assert transport.server_config == stdio_config
        assert transport.state == ConnectionState.DISCONNECTED

    @patch('subprocess.Popen')
    @pytest.mark.asyncio
    async def test_connect_success(self, mock_popen, stdio_config):
        """Test successful stdio connection."""
        # Mock process
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Process is running
        mock_popen.return_value = mock_process
        
        transport = StdioTransport(stdio_config)
        
        # Mock the read task to avoid hanging
        with patch.object(transport, '_read_messages', new_callable=AsyncMock):
            await transport.connect()
        
        assert transport.state == ConnectionState.CONNECTED
        assert transport.process == mock_process
        mock_popen.assert_called_once()

    @patch('subprocess.Popen')
    @pytest.mark.asyncio
    async def test_connect_failure(self, mock_popen, stdio_config):
        """Test stdio connection failure."""
        mock_popen.side_effect = OSError("Command not found")
        
        transport = StdioTransport(stdio_config)
        
        with pytest.raises(OSError):
            await transport.connect()
        
        assert transport.state == ConnectionState.FAILED

    @pytest.mark.asyncio
    async def test_send_message_not_connected(self, stdio_config):
        """Test sending message when not connected."""
        transport = StdioTransport(stdio_config)
        message = MCPMessage(method="test")
        
        with pytest.raises(RuntimeError, match="Not connected"):
            await transport.send_message(message)

    @pytest.mark.asyncio
    async def test_is_healthy(self, stdio_config):
        """Test health check."""
        transport = StdioTransport(stdio_config)
        
        # Not connected
        assert await transport.is_healthy() is False
        
        # Mock connected process
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Running
        transport.process = mock_process
        
        assert await transport.is_healthy() is True
        
        # Process died
        mock_process.poll.return_value = 1  # Exited
        assert await transport.is_healthy() is False


class TestHTTPTransport:
    """Test HTTPTransport class."""

    @pytest.fixture
    def http_config(self):
        """Create HTTP server config."""
        settings = ServerSettings(timeout=10)
        return ServerConfig(
            name="test-http",
            enabled=True,
            description="Test HTTP server",
            type="streamable-http",
            settings=settings,
            url="http://localhost:3000/mcp",
            headers={"Authorization": "Bearer test"}
        )

    def test_create_transport(self, http_config):
        """Test creating HTTP transport."""
        transport = HTTPTransport(http_config)
        assert transport.server_config == http_config
        assert transport.state == ConnectionState.DISCONNECTED

    @respx.mock
    @pytest.mark.asyncio
    async def test_connect_success(self, http_config):
        """Test successful HTTP connection."""
        # Mock successful connection
        respx.get("http://localhost:3000/mcp").mock(
            return_value=httpx.Response(200, json={"status": "ok"})
        )
        
        transport = HTTPTransport(http_config)
        await transport.connect()
        
        assert transport.state == ConnectionState.CONNECTED
        assert transport.client is not None

    @respx.mock
    @pytest.mark.asyncio
    async def test_connect_failure(self, http_config):
        """Test HTTP connection failure."""
        # Mock connection failure
        respx.get("http://localhost:3000/mcp").mock(
            return_value=httpx.Response(500, text="Server Error")
        )
        
        transport = HTTPTransport(http_config)
        
        with pytest.raises(httpx.HTTPStatusError):
            await transport.connect()
        
        assert transport.state == ConnectionState.FAILED

    @respx.mock
    @pytest.mark.asyncio
    async def test_send_message(self, http_config):
        """Test sending HTTP message."""
        # Mock connection and message sending
        respx.get("http://localhost:3000/mcp").mock(
            return_value=httpx.Response(200, json={"status": "ok"})
        )
        respx.post("http://localhost:3000/mcp").mock(
            return_value=httpx.Response(200, json={"result": "success"})
        )
        
        transport = HTTPTransport(http_config)
        await transport.connect()
        
        message = MCPMessage(id=1, method="test", params={})
        await transport.send_message(message)
        
        # Verify the POST request was made
        assert len(respx.calls) == 2  # GET for connect, POST for message

    @respx.mock
    @pytest.mark.asyncio
    async def test_is_healthy(self, http_config):
        """Test HTTP health check."""
        transport = HTTPTransport(http_config)
        
        # Not connected
        assert await transport.is_healthy() is False
        
        # Mock connection
        respx.get("http://localhost:3000/mcp").mock(
            return_value=httpx.Response(200, json={"status": "ok"})
        )
        await transport.connect()
        
        # Mock health check
        respx.head("http://localhost:3000/mcp").mock(
            return_value=httpx.Response(200)
        )
        
        assert await transport.is_healthy() is True


class TestMCPClient:
    """Test MCPClient class."""

    @pytest.fixture
    def stdio_config(self):
        """Create stdio server config."""
        settings = ServerSettings(timeout=5, retry_attempts=2)
        return ServerConfig(
            name="test-stdio",
            enabled=True,
            description="Test stdio server",
            type="stdio",
            settings=settings,
            command="/bin/echo",
            args=["test"]
        )

    @pytest.fixture
    def http_config(self):
        """Create HTTP server config."""
        settings = ServerSettings(timeout=5)
        return ServerConfig(
            name="test-http",
            enabled=True,
            description="Test HTTP server",
            type="streamable-http",
            settings=settings,
            url="http://localhost:3000/mcp"
        )

    def test_create_client(self, stdio_config):
        """Test creating MCP client."""
        client = MCPClient(stdio_config)
        
        assert client.server_config == stdio_config
        assert client.transport is not None
        assert isinstance(client.transport, StdioTransport)
        assert client.connection_state == ConnectionState.DISCONNECTED
        assert not client.is_connected

    def test_create_http_client(self, http_config):
        """Test creating HTTP MCP client."""
        client = MCPClient(http_config)
        assert isinstance(client.transport, HTTPTransport)

    def test_unsupported_transport(self):
        """Test unsupported transport type."""
        settings = ServerSettings()
        
        # The ServerConfig constructor will validate the type first
        with pytest.raises(ValueError, match="Unsupported server type: unsupported"):
            config = ServerConfig(
                name="test",
                enabled=True,
                description="Test",
                type="unsupported",
                settings=settings
            )
    
    def test_unimplemented_transport(self):
        """Test transport type that's valid in ServerConfig but not implemented in MCPClient."""
        settings = ServerSettings()
        
        # Create a config with a valid type for ServerConfig but not implemented in MCPClient
        config = ServerConfig(
            name="test",
            enabled=True,
            description="Test",
            type="websocket",  # Valid for ServerConfig but not implemented in MCPClient
            url="ws://localhost:8080",  # Required for websocket type
            settings=settings
        )
        
        # MCPClient should reject it
        with pytest.raises(ValueError, match="Unsupported transport type: websocket"):
            MCPClient(config)

    @pytest.mark.asyncio
    async def test_send_request_not_connected(self, stdio_config):
        """Test sending request when not connected."""
        client = MCPClient(stdio_config)
        
        with pytest.raises(RuntimeError, match="Not connected"):
            await client.send_request("test")

    @pytest.mark.asyncio
    async def test_message_id_generation(self, stdio_config):
        """Test message ID generation."""
        client = MCPClient(stdio_config)
        
        id1 = client._get_next_message_id()
        id2 = client._get_next_message_id()
        
        assert id1 == 1
        assert id2 == 2
        assert id1 != id2

    @pytest.mark.asyncio
    async def test_handle_response_message(self, stdio_config):
        """Test handling response messages."""
        client = MCPClient(stdio_config)
        
        # Create a pending request
        future = asyncio.Future()
        client._pending_requests[1] = future
        
        # Handle successful response
        response = MCPMessage(id=1, result={"success": True})
        client._handle_message(response)
        
        # Check that future was resolved
        assert future.done()
        assert await future == {"success": True}

    @pytest.mark.asyncio
    async def test_handle_error_response(self, stdio_config):
        """Test handling error responses."""
        client = MCPClient(stdio_config)
        
        # Create a pending request
        future = asyncio.Future()
        client._pending_requests[1] = future
        
        # Handle error response
        response = MCPMessage(id=1, error={"code": -1, "message": "Test error"})
        client._handle_message(response)
        
        # Check that future was resolved with exception
        assert future.done()
        with pytest.raises(Exception, match="MCP Error"):
            await future

    @pytest.mark.asyncio
    async def test_tool_discovery_not_connected(self, stdio_config):
        """Test tool discovery when not connected."""
        client = MCPClient(stdio_config)
        
        with pytest.raises(RuntimeError, match="Must be connected"):
            await client.discover_tools()

    @pytest.mark.asyncio
    async def test_tool_discovery_caching(self, stdio_config):
        """Test tool discovery caching."""
        client = MCPClient(stdio_config)
        
        # Mock connection state
        client.transport.state = ConnectionState.CONNECTED
        
        # Add some cached tools
        tool = MCPTool(
            name="test_tool",
            description="Test tool",
            input_schema={},
            server_name="test"
        )
        client._discovered_tools = [tool]
        client._last_discovery = time.time()
        
        # Should return cached tools without making request
        with patch.object(client, 'send_request') as mock_request:
            tools = await client.discover_tools()
            
            assert len(tools) == 1
            assert tools[0].name == "test_tool"
            mock_request.assert_not_called()

    @pytest.mark.asyncio
    async def test_tool_discovery_force_refresh(self, stdio_config):
        """Test forced tool discovery refresh."""
        client = MCPClient(stdio_config)
        
        # Mock connection state and send_request
        client.transport.state = ConnectionState.CONNECTED
        
        with patch.object(client, 'send_request') as mock_request:
            mock_request.return_value = {
                "tools": [
                    {
                        "name": "new_tool",
                        "description": "New tool",
                        "inputSchema": {"type": "object", "properties": {}}
                    }
                ]
            }
            
            # Add cached tools
            client._discovered_tools = [MCPTool("old_tool", "Old", {}, "test")]
            client._last_discovery = time.time()
            
            # Force refresh should ignore cache
            tools = await client.discover_tools(force_refresh=True)
            
            assert len(tools) == 1
            assert tools[0].name == "new_tool"
            mock_request.assert_called_once_with("tools/list")

    @pytest.mark.asyncio
    async def test_get_tool_by_name(self, stdio_config):
        """Test getting tool by name."""
        client = MCPClient(stdio_config)
        
        tool1 = MCPTool("tool1", "Tool 1", {}, "test")
        tool2 = MCPTool("tool2", "Tool 2", {}, "test")
        client._discovered_tools = [tool1, tool2]
        
        # Found
        found = client.get_tool_by_name("tool1")
        assert found == tool1
        
        # Not found
        not_found = client.get_tool_by_name("tool3")
        assert not_found is None

    @pytest.mark.asyncio
    async def test_clear_tool_cache(self, stdio_config):
        """Test clearing tool cache."""
        client = MCPClient(stdio_config)
        
        # Add cached tools
        tool = MCPTool("test", "Test", {}, "test")
        client._discovered_tools = [tool]
        client._last_discovery = time.time()
        
        # Clear cache
        client.clear_tool_cache()
        
        assert len(client._discovered_tools) == 0
        assert client._last_discovery == 0.0

    @pytest.mark.asyncio
    async def test_call_tool_not_connected(self, stdio_config):
        """Test calling tool when not connected."""
        client = MCPClient(stdio_config)
        
        with pytest.raises(RuntimeError, match="Must be connected"):
            await client.call_tool("test_tool", {})

    @pytest.mark.asyncio
    async def test_call_tool_success(self, stdio_config):
        """Test successful tool call."""
        client = MCPClient(stdio_config)
        client.transport.state = ConnectionState.CONNECTED
        
        with patch.object(client, 'send_request') as mock_request:
            mock_request.return_value = {
                "content": [
                    {"type": "text", "text": "Tool result"}
                ]
            }
            
            result = await client.call_tool("test_tool", {"param": "value"})
            
            assert result == "Tool result"
            mock_request.assert_called_once_with("tools/call", {
                "name": "test_tool",
                "arguments": {"param": "value"}
            })

    @pytest.mark.asyncio
    async def test_health_check_caching(self, stdio_config):
        """Test health check caching."""
        client = MCPClient(stdio_config)
        
        # Mock transport
        mock_transport = AsyncMock()
        mock_transport.is_healthy.return_value = True
        mock_transport.state = ConnectionState.CONNECTED
        client.transport = mock_transport
        
        # First call should check transport
        result1 = await client.is_healthy()
        assert result1 is True
        mock_transport.is_healthy.assert_called_once()
        
        # Second call within cache period should use cached result
        mock_transport.reset_mock()
        result2 = await client.is_healthy()
        assert result2 is True
        mock_transport.is_healthy.assert_not_called()

    @pytest.mark.asyncio
    async def test_reconnect_success(self, stdio_config):
        """Test successful reconnection."""
        client = MCPClient(stdio_config)
        
        with patch.object(client, 'disconnect') as mock_disconnect, \
             patch.object(client, 'connect') as mock_connect:
            
            mock_connect.return_value = None  # Successful connection
            
            result = await client.reconnect()
            
            assert result is True
            mock_disconnect.assert_called_once()
            mock_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_reconnect_failure(self, stdio_config):
        """Test failed reconnection."""
        client = MCPClient(stdio_config)
        
        with patch.object(client, 'disconnect') as mock_disconnect, \
             patch.object(client, 'connect') as mock_connect:
            
            mock_connect.side_effect = Exception("Connection failed")
            
            result = await client.reconnect()
            
            assert result is False
            assert mock_disconnect.call_count == 2  # Called for each attempt
            assert mock_connect.call_count == 2  # Two retry attempts

    def test_string_representations(self, stdio_config):
        """Test string representations."""
        client = MCPClient(stdio_config)
        
        str_repr = str(client)
        assert "test-stdio" in str_repr
        assert "disconnected" in str_repr
        
        repr_str = repr(client)
        assert "MCPClient" in repr_str
        assert "test-stdio" in repr_str
        assert "stdio" in repr_str