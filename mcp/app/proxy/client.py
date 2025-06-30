"""
MCP Client for connecting to external MCP servers.

This module provides the MCPClient class that handles connections to external
MCP servers using various transport protocols (stdio, SSE, HTTP, WebSocket).
"""

import asyncio
import json
import logging
import subprocess
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Callable
from pathlib import Path

import httpx

from .config import ServerConfig

logger = logging.getLogger(__name__)


@dataclass
class MCPTool:
    """Represents a tool discovered from an MCP server."""

    name: str
    description: str
    input_schema: Dict[str, Any]
    server_name: str

    def __post_init__(self):
        """Validate tool after initialization."""
        if not self.name:
            raise ValueError("Tool name cannot be empty")
        if not self.description:
            raise ValueError("Tool description cannot be empty")
        if not isinstance(self.input_schema, dict):
            raise ValueError("Tool input_schema must be a dictionary")

    @classmethod
    def from_mcp_response(
        cls, tool_data: Dict[str, Any], server_name: str
    ) -> "MCPTool":
        """Create MCPTool from MCP server response data."""
        return cls(
            name=tool_data.get("name", ""),
            description=tool_data.get("description", ""),
            input_schema=tool_data.get("inputSchema", {}),
            server_name=server_name,
        )

    def to_core_tool_format(self, tool_prefix: str = "") -> Dict[str, Any]:
        """Convert to core engine tool format."""
        prefixed_name = f"{tool_prefix}{self.name}" if tool_prefix else self.name

        # Convert MCP input schema to core tool format
        parameters = []
        properties = self.input_schema.get("properties", {})
        required = self.input_schema.get("required", [])

        for param_name, param_info in properties.items():
            param_type = param_info.get("type", "string")
            param_desc = param_info.get("description", "")

            # Map JSON Schema types to Python types
            type_mapping = {
                "string": "str",
                "integer": "int",
                "number": "float",
                "boolean": "bool",
                "array": "list",
                "object": "dict",
            }

            parameters.append(
                {
                    "name": param_name,
                    "annotation": type_mapping.get(param_type, "str"),
                    "description": param_desc,
                    "required": param_name in required,
                    "default": param_info.get("default"),
                }
            )

        # Use the stored original name if available, otherwise use current name
        original_name = getattr(self, "_original_name", self.name)

        return {
            "name": prefixed_name,
            "description": self.description,
            "parameters": parameters,
            "metadata": {
                "source": "mcp_proxy",
                "server_name": self.server_name,
                "original_name": original_name,
                "input_schema": self.input_schema,
            },
        }

    def __str__(self) -> str:
        return f"MCPTool({self.name} from {self.server_name})"

    def __repr__(self) -> str:
        return f"MCPTool(name={self.name}, server={self.server_name})"


@dataclass
class MCPServerInfo:
    """Information about an MCP server."""

    name: str
    version: str
    protocol_version: str = "2024-11-05"
    capabilities: Optional[Dict[str, Any]] = None

    @classmethod
    def from_mcp_response(
        cls, info_data: Dict[str, Any], server_name: str
    ) -> "MCPServerInfo":
        """Create MCPServerInfo from MCP server response."""
        return cls(
            name=info_data.get("name", server_name),
            version=info_data.get("version", "unknown"),
            protocol_version=info_data.get("protocolVersion", "2024-11-05"),
            capabilities=info_data.get("capabilities", {}),
        )


class ConnectionState(Enum):
    """Connection state enumeration."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


@dataclass
class MCPMessage:
    """Represents an MCP protocol message."""

    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    method: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        msg = {"jsonrpc": self.jsonrpc}

        if self.id is not None:
            msg["id"] = self.id
        if self.method is not None:
            msg["method"] = self.method
        if self.params is not None:
            msg["params"] = self.params
        if self.result is not None:
            msg["result"] = self.result
        if self.error is not None:
            msg["error"] = self.error

        return msg

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPMessage":
        """Create message from dictionary."""
        return cls(
            jsonrpc=data.get("jsonrpc", "2.0"),
            id=data.get("id"),
            method=data.get("method"),
            params=data.get("params"),
            result=data.get("result"),
            error=data.get("error"),
        )

    def is_request(self) -> bool:
        """Check if this is a request message."""
        return self.method is not None and self.id is not None

    def is_response(self) -> bool:
        """Check if this is a response message."""
        return self.id is not None and (
            self.result is not None or self.error is not None
        )

    def is_notification(self) -> bool:
        """Check if this is a notification message."""
        return self.method is not None and self.id is None


class MCPTransport(ABC):
    """Abstract base class for MCP transport implementations."""

    def __init__(self, server_config: ServerConfig):
        self.server_config = server_config
        self.state = ConnectionState.DISCONNECTED
        self._message_handlers: List[Callable[[MCPMessage], None]] = []
        self._error_handlers: List[Callable[[Exception], None]] = []

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the MCP server."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to the MCP server."""
        pass

    @abstractmethod
    async def send_message(self, message: MCPMessage) -> None:
        """Send a message to the MCP server."""
        pass

    @abstractmethod
    async def is_healthy(self) -> bool:
        """Check if the connection is healthy."""
        pass

    def add_message_handler(self, handler: Callable[[MCPMessage], None]) -> None:
        """Add a message handler."""
        self._message_handlers.append(handler)

    def add_error_handler(self, handler: Callable[[Exception], None]) -> None:
        """Add an error handler."""
        self._error_handlers.append(handler)

    def _handle_message(self, message: MCPMessage) -> None:
        """Handle incoming message."""
        for handler in self._message_handlers:
            try:
                handler(message)
            except Exception as e:
                logger.error(f"Error in message handler: {e}")

    def _handle_error(self, error: Exception) -> None:
        """Handle error."""
        for handler in self._error_handlers:
            try:
                handler(error)
            except Exception as e:
                logger.error(f"Error in error handler: {e}")


class StdioTransport(MCPTransport):
    """Transport for stdio-based MCP servers."""

    def __init__(self, server_config: ServerConfig):
        super().__init__(server_config)
        self.process: Optional[subprocess.Popen] = None
        self._read_task: Optional[asyncio.Task] = None

    async def connect(self) -> None:
        """Start the MCP server process and establish stdio connection."""
        if self.state in [ConnectionState.CONNECTED, ConnectionState.CONNECTING]:
            return

        self.state = ConnectionState.CONNECTING
        logger.info(f"Starting stdio MCP server: {self.server_config.command}")

        try:
            # Start the process
            self.process = subprocess.Popen(
                [self.server_config.command] + (self.server_config.args or []),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={**os.environ, **(self.server_config.env or {})},
                text=True,
                bufsize=0,
            )

            # Start reading messages
            self._read_task = asyncio.create_task(self._read_messages())

            self.state = ConnectionState.CONNECTED
            logger.info(f"Connected to stdio MCP server: {self.server_config.name}")

        except Exception as e:
            self.state = ConnectionState.FAILED
            logger.error(
                f"Failed to start stdio MCP server {self.server_config.name}: {e}"
            )
            self._handle_error(e)
            raise

    async def disconnect(self) -> None:
        """Stop the MCP server process."""
        if self.state == ConnectionState.DISCONNECTED:
            return

        logger.info(f"Disconnecting from stdio MCP server: {self.server_config.name}")

        # Cancel read task
        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass

        # Terminate process
        if self.process:
            try:
                self.process.terminate()
                # Wait for graceful shutdown
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning(
                        f"Force killing stdio MCP server: {self.server_config.name}"
                    )
                    self.process.kill()
                    self.process.wait()
            except Exception as e:
                logger.error(f"Error terminating process: {e}")

        self.process = None
        self.state = ConnectionState.DISCONNECTED

    async def send_message(self, message: MCPMessage) -> None:
        """Send a message to the stdio MCP server."""
        if not self.process or not self.process.stdin:
            raise RuntimeError("Not connected to stdio MCP server")

        try:
            message_json = json.dumps(message.to_dict()) + "\n"
            self.process.stdin.write(message_json)
            self.process.stdin.flush()
            logger.debug(f"Sent message to {self.server_config.name}: {message.method}")
        except Exception as e:
            logger.error(f"Failed to send message to {self.server_config.name}: {e}")
            self._handle_error(e)
            raise

    async def is_healthy(self) -> bool:
        """Check if the stdio connection is healthy."""
        if not self.process:
            return False

        # Check if process is still running
        return self.process.poll() is None

    async def _read_messages(self) -> None:
        """Read messages from the stdio MCP server."""
        if not self.process or not self.process.stdout:
            return

        try:
            while True:
                line = await asyncio.get_event_loop().run_in_executor(
                    None, self.process.stdout.readline
                )

                if not line:  # EOF
                    break

                line = line.strip()
                if not line:
                    continue

                try:
                    message_data = json.loads(line)
                    message = MCPMessage.from_dict(message_data)
                    self._handle_message(message)
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON from {self.server_config.name}: {e}")
                except Exception as e:
                    logger.error(
                        f"Error processing message from {self.server_config.name}: {e}"
                    )

        except Exception as e:
            if not isinstance(e, asyncio.CancelledError):
                logger.error(f"Error reading from {self.server_config.name}: {e}")
                self._handle_error(e)
                self.state = ConnectionState.FAILED


class SSETransport(MCPTransport):
    """Transport for Server-Sent Events based MCP servers."""

    def __init__(self, server_config: ServerConfig):
        super().__init__(server_config)
        self.client: Optional[httpx.AsyncClient] = None
        self._read_task: Optional[asyncio.Task] = None

    async def connect(self) -> None:
        """Connect to the SSE MCP server."""
        if self.state in [ConnectionState.CONNECTED, ConnectionState.CONNECTING]:
            return

        self.state = ConnectionState.CONNECTING
        logger.info(f"Connecting to SSE MCP server: {self.server_config.url}")

        try:
            # Create HTTP client
            self.client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.server_config.settings.timeout),
                headers=self.server_config.headers or {},
            )

            # Test connection
            response = await self.client.get(self.server_config.url)
            response.raise_for_status()

            # Start reading SSE stream
            self._read_task = asyncio.create_task(self._read_sse_stream())

            self.state = ConnectionState.CONNECTED
            logger.info(f"Connected to SSE MCP server: {self.server_config.name}")

        except Exception as e:
            self.state = ConnectionState.FAILED
            logger.error(
                f"Failed to connect to SSE MCP server {self.server_config.name}: {e}"
            )
            self._handle_error(e)
            raise

    async def disconnect(self) -> None:
        """Disconnect from the SSE MCP server."""
        if self.state == ConnectionState.DISCONNECTED:
            return

        logger.info(f"Disconnecting from SSE MCP server: {self.server_config.name}")

        # Cancel read task
        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass

        # Close HTTP client
        if self.client:
            await self.client.aclose()
            self.client = None

        self.state = ConnectionState.DISCONNECTED

    async def send_message(self, message: MCPMessage) -> None:
        """Send a message to the SSE MCP server via HTTP POST."""
        if not self.client:
            raise RuntimeError("Not connected to SSE MCP server")

        try:
            response = await self.client.post(
                self.server_config.url,
                json=message.to_dict(),
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            logger.debug(f"Sent message to {self.server_config.name}: {message.method}")
        except Exception as e:
            logger.error(f"Failed to send message to {self.server_config.name}: {e}")
            self._handle_error(e)
            raise

    async def is_healthy(self) -> bool:
        """Check if the SSE connection is healthy."""
        if not self.client:
            return False

        try:
            response = await self.client.head(self.server_config.url)
            return response.status_code < 400
        except Exception:
            return False

    async def _read_sse_stream(self) -> None:
        """Read Server-Sent Events stream."""
        if not self.client:
            return

        try:
            async with self.client.stream("GET", self.server_config.url) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]  # Remove "data: " prefix
                        if data.strip():
                            try:
                                message_data = json.loads(data)
                                message = MCPMessage.from_dict(message_data)
                                self._handle_message(message)
                            except json.JSONDecodeError as e:
                                logger.error(
                                    f"Invalid JSON from SSE {self.server_config.name}: {e}"
                                )
                            except Exception as e:
                                logger.error(
                                    f"Error processing SSE message from {self.server_config.name}: {e}"
                                )

        except Exception as e:
            if not isinstance(e, asyncio.CancelledError):
                logger.error(f"Error reading SSE from {self.server_config.name}: {e}")
                self._handle_error(e)
                self.state = ConnectionState.FAILED


class HTTPTransport(MCPTransport):
    """Transport for HTTP-based MCP servers."""

    def __init__(self, server_config: ServerConfig):
        super().__init__(server_config)
        self.client: Optional[httpx.AsyncClient] = None

    async def connect(self) -> None:
        """Connect to the HTTP MCP server."""
        if self.state in [ConnectionState.CONNECTED, ConnectionState.CONNECTING]:
            return

        self.state = ConnectionState.CONNECTING
        logger.info(f"Connecting to HTTP MCP server: {self.server_config.url}")

        try:
            # Create HTTP client
            self.client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.server_config.settings.timeout),
                headers=self.server_config.headers or {},
            )

            # Test connection
            response = await self.client.get(self.server_config.url)
            response.raise_for_status()

            self.state = ConnectionState.CONNECTED
            logger.info(f"Connected to HTTP MCP server: {self.server_config.name}")

        except Exception as e:
            self.state = ConnectionState.FAILED
            logger.error(
                f"Failed to connect to HTTP MCP server {self.server_config.name}: {e}"
            )
            self._handle_error(e)
            raise

    async def disconnect(self) -> None:
        """Disconnect from the HTTP MCP server."""
        if self.state == ConnectionState.DISCONNECTED:
            return

        logger.info(f"Disconnecting from HTTP MCP server: {self.server_config.name}")

        if self.client:
            await self.client.aclose()
            self.client = None

        self.state = ConnectionState.DISCONNECTED

    async def send_message(self, message: MCPMessage) -> None:
        """Send a message to the HTTP MCP server."""
        if not self.client:
            raise RuntimeError("Not connected to HTTP MCP server")

        try:
            response = await self.client.post(
                self.server_config.url,
                json=message.to_dict(),
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()

            # Handle response if it's a request
            if message.is_request():
                response_data = response.json()
                response_message = MCPMessage.from_dict(response_data)
                self._handle_message(response_message)

            logger.debug(f"Sent message to {self.server_config.name}: {message.method}")
        except Exception as e:
            logger.error(f"Failed to send message to {self.server_config.name}: {e}")
            self._handle_error(e)
            raise

    async def is_healthy(self) -> bool:
        """Check if the HTTP connection is healthy."""
        if not self.client:
            return False

        try:
            response = await self.client.head(self.server_config.url)
            return response.status_code < 400
        except Exception:
            return False


class MCPClient:
    """
    Client for connecting to external MCP servers.

    Handles connection management, message routing, and health checking
    for various MCP transport protocols.
    """

    def __init__(self, server_config: ServerConfig):
        """
        Initialize MCP client.

        Args:
            server_config: Configuration for the MCP server to connect to
        """
        self.server_config = server_config
        self.transport: Optional[MCPTransport] = None
        self._message_id_counter = 0
        self._pending_requests: Dict[Union[str, int], asyncio.Future] = {}
        self._last_health_check = 0.0
        self._connection_attempts = 0

        # Tool discovery cache
        self._discovered_tools: List[MCPTool] = []
        self._server_info: Optional[MCPServerInfo] = None
        self._last_discovery = 0.0

        # Create appropriate transport
        self._create_transport()

    def _create_transport(self) -> None:
        """Create the appropriate transport for the server type."""
        if self.server_config.type == "stdio":
            self.transport = StdioTransport(self.server_config)
        elif self.server_config.type == "sse":
            self.transport = SSETransport(self.server_config)
        elif self.server_config.type in ["streamable-http", "http"]:
            self.transport = HTTPTransport(self.server_config)
        else:
            raise ValueError(f"Unsupported transport type: {self.server_config.type}")

        # Add message and error handlers
        self.transport.add_message_handler(self._handle_message)
        self.transport.add_error_handler(self._handle_error)

    async def connect(self) -> None:
        """
        Connect to the MCP server.

        Raises:
            RuntimeError: If connection fails
        """
        if not self.transport:
            raise RuntimeError("No transport available")

        try:
            await self.transport.connect()
            self._connection_attempts = 0
            logger.info(
                f"Successfully connected to MCP server: {self.server_config.name}"
            )
        except Exception as e:
            self._connection_attempts += 1
            logger.error(
                f"Failed to connect to MCP server {self.server_config.name}: {e}"
            )
            raise

    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        if self.transport:
            await self.transport.disconnect()

        # Cancel any pending requests
        for future in self._pending_requests.values():
            if not future.done():
                future.cancel()
        self._pending_requests.clear()

    async def send_request(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> Any:
        """
        Send a request to the MCP server and wait for response.

        Args:
            method: The method name to call
            params: Parameters for the method
            timeout: Request timeout in seconds

        Returns:
            The result from the server

        Raises:
            RuntimeError: If not connected or request fails
            asyncio.TimeoutError: If request times out
        """
        if not self.transport or self.transport.state != ConnectionState.CONNECTED:
            raise RuntimeError("Not connected to MCP server")

        # Generate unique message ID
        message_id = self._get_next_message_id()

        # Create request message
        message = MCPMessage(id=message_id, method=method, params=params or {})

        # Create future for response
        response_future = asyncio.Future()
        self._pending_requests[message_id] = response_future

        try:
            # Send message
            await self.transport.send_message(message)

            # Wait for response
            timeout = timeout or self.server_config.settings.timeout
            response = await asyncio.wait_for(response_future, timeout=timeout)

            return response

        except asyncio.TimeoutError:
            logger.error(f"Request timeout for {method} on {self.server_config.name}")
            raise
        except Exception as e:
            logger.error(
                f"Request failed for {method} on {self.server_config.name}: {e}"
            )
            raise
        finally:
            # Clean up pending request
            self._pending_requests.pop(message_id, None)

    async def initialize_server(self) -> MCPServerInfo:
        """
        Initialize the MCP server connection and get server info.

        Returns:
            Server information

        Raises:
            RuntimeError: If initialization fails
        """
        if not self.is_connected:
            raise RuntimeError("Must be connected before initializing server")

        try:
            # Send initialize request
            result = await self.send_request(
                "initialize",
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "mcp-proxy-client", "version": "1.0.0"},
                },
            )

            # Parse server info
            self._server_info = MCPServerInfo.from_mcp_response(
                result, self.server_config.name
            )

            # Send initialized notification
            await self.send_notification("notifications/initialized")

            logger.info(
                f"Initialized MCP server {self.server_config.name}: {self._server_info.name} v{self._server_info.version}"
            )
            return self._server_info

        except Exception as e:
            logger.error(
                f"Failed to initialize MCP server {self.server_config.name}: {e}"
            )
            raise

    async def discover_tools(self, force_refresh: bool = False) -> List[MCPTool]:
        """
        Discover tools available on the MCP server.

        Args:
            force_refresh: If True, bypass cache and fetch fresh tool list

        Returns:
            List of discovered tools

        Raises:
            RuntimeError: If not connected or discovery fails
        """
        if not self.is_connected:
            raise RuntimeError("Must be connected before discovering tools")

        # Check cache
        now = time.time()
        cache_valid = (
            not force_refresh
            and self._discovered_tools
            and (now - self._last_discovery) < 300  # 5 minute cache
        )

        if cache_valid:
            logger.debug(f"Using cached tools for {self.server_config.name}")
            return self._discovered_tools

        try:
            logger.info(f"Discovering tools from MCP server: {self.server_config.name}")

            # Send tools/list request
            result = await self.send_request("tools/list")

            # Parse tools from response
            tools_data = result.get("tools", [])
            if not isinstance(tools_data, list):
                raise ValueError("Expected 'tools' to be a list in response")

            # Convert to MCPTool objects
            discovered_tools = []
            for tool_data in tools_data:
                try:
                    tool = MCPTool.from_mcp_response(tool_data, self.server_config.name)
                    discovered_tools.append(tool)
                    logger.debug(f"Discovered tool: {tool.name}")
                except Exception as e:
                    logger.warning(
                        f"Failed to parse tool from {self.server_config.name}: {e}"
                    )
                    continue

            # Update cache
            self._discovered_tools = discovered_tools
            self._last_discovery = now

            logger.info(
                f"Discovered {len(discovered_tools)} tools from {self.server_config.name}"
            )
            return discovered_tools

        except Exception as e:
            logger.error(
                f"Failed to discover tools from {self.server_config.name}: {e}"
            )
            raise

    async def get_tool_schema(self, tool_name: str) -> Dict[str, Any]:
        """
        Get detailed schema for a specific tool.

        Args:
            tool_name: Name of the tool to get schema for

        Returns:
            Tool schema information

        Raises:
            RuntimeError: If not connected or tool not found
        """
        if not self.is_connected:
            raise RuntimeError("Must be connected before getting tool schema")

        try:
            # First check if we have the tool in our cache
            for tool in self._discovered_tools:
                if tool.name == tool_name:
                    return tool.input_schema

            # If not in cache, try to get it directly
            result = await self.send_request("tools/get", {"name": tool_name})
            return result.get("inputSchema", {})

        except Exception as e:
            logger.error(
                f"Failed to get schema for tool {tool_name} from {self.server_config.name}: {e}"
            )
            raise

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call a tool on the MCP server.

        Args:
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool

        Returns:
            Tool execution result

        Raises:
            RuntimeError: If not connected or tool call fails
        """
        if not self.is_connected:
            raise RuntimeError("Must be connected before calling tools")

        try:
            logger.debug(f"Calling tool {tool_name} on {self.server_config.name}")

            result = await self.send_request(
                "tools/call", {"name": tool_name, "arguments": arguments}
            )

            # Extract content from result
            content = result.get("content", [])
            if isinstance(content, list) and len(content) > 0:
                # Return the first content item's text if available
                first_content = content[0]
                if isinstance(first_content, dict):
                    return first_content.get("text", result)

            return result

        except Exception as e:
            logger.error(
                f"Failed to call tool {tool_name} on {self.server_config.name}: {e}"
            )
            raise

    def get_discovered_tools(self) -> List[MCPTool]:
        """
        Get the list of currently discovered tools (from cache).

        Returns:
            List of discovered tools
        """
        return self._discovered_tools.copy()

    def get_server_info(self) -> Optional[MCPServerInfo]:
        """
        Get server information.

        Returns:
            Server info if available, None otherwise
        """
        return self._server_info

    def get_tool_by_name(self, tool_name: str) -> Optional[MCPTool]:
        """
        Get a specific tool by name from discovered tools.

        Args:
            tool_name: Name of the tool to find

        Returns:
            MCPTool if found, None otherwise
        """
        for tool in self._discovered_tools:
            if tool.name == tool_name:
                return tool
        return None

    def clear_tool_cache(self) -> None:
        """Clear the tool discovery cache."""
        self._discovered_tools.clear()
        self._last_discovery = 0.0
        logger.debug(f"Cleared tool cache for {self.server_config.name}")

    async def send_notification(
        self, method: str, params: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Send a notification to the MCP server (no response expected).

        Args:
            method: The method name to call
            params: Parameters for the method

        Raises:
            RuntimeError: If not connected
        """
        if not self.transport or self.transport.state != ConnectionState.CONNECTED:
            raise RuntimeError("Not connected to MCP server")

        message = MCPMessage(method=method, params=params or {})

        await self.transport.send_message(message)

    async def is_healthy(self) -> bool:
        """
        Check if the connection is healthy.

        Returns:
            True if connection is healthy, False otherwise
        """
        if not self.transport:
            return False

        # Use cached result if recent
        now = time.time()
        if (
            now - self._last_health_check
        ) < self.server_config.settings.health_check_interval:
            return self.transport.state == ConnectionState.CONNECTED

        # Perform health check
        try:
            is_healthy = await self.transport.is_healthy()
            self._last_health_check = now
            return is_healthy
        except Exception as e:
            logger.error(f"Health check failed for {self.server_config.name}: {e}")
            return False

    async def reconnect(self) -> bool:
        """
        Attempt to reconnect to the MCP server.

        Returns:
            True if reconnection successful, False otherwise
        """
        if self.transport and self.transport.state == ConnectionState.CONNECTED:
            return True

        max_attempts = self.server_config.settings.retry_attempts
        delay = self.server_config.settings.retry_delay

        for attempt in range(max_attempts):
            try:
                logger.info(
                    f"Reconnection attempt {attempt + 1}/{max_attempts} for {self.server_config.name}"
                )

                # Disconnect first
                await self.disconnect()

                # Wait before retry
                if attempt > 0:
                    await asyncio.sleep(delay * (2**attempt))  # Exponential backoff

                # Attempt connection
                await self.connect()
                return True

            except Exception as e:
                logger.warning(
                    f"Reconnection attempt {attempt + 1} failed for {self.server_config.name}: {e}"
                )

        logger.error(f"All reconnection attempts failed for {self.server_config.name}")
        return False

    def _get_next_message_id(self) -> int:
        """Get the next message ID."""
        self._message_id_counter += 1
        return self._message_id_counter

    def _handle_message(self, message: MCPMessage) -> None:
        """Handle incoming message from the transport."""
        if message.is_response() and message.id in self._pending_requests:
            # Handle response to pending request
            future = self._pending_requests[message.id]
            if not future.done():
                if message.error:
                    error = Exception(f"MCP Error: {message.error}")
                    future.set_exception(error)
                else:
                    future.set_result(message.result)
        elif message.is_notification():
            # Handle notification (could be used for events)
            logger.debug(
                f"Received notification from {self.server_config.name}: {message.method}"
            )
        else:
            logger.warning(
                f"Unhandled message from {self.server_config.name}: {message.to_dict()}"
            )

    def _handle_error(self, error: Exception) -> None:
        """Handle transport error."""
        logger.error(f"Transport error for {self.server_config.name}: {error}")

        # Cancel any pending requests
        for future in self._pending_requests.values():
            if not future.done():
                future.set_exception(error)
        self._pending_requests.clear()

    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return (
            self.transport is not None
            and self.transport.state == ConnectionState.CONNECTED
        )

    @property
    def connection_state(self) -> ConnectionState:
        """Get current connection state."""
        return self.transport.state if self.transport else ConnectionState.DISCONNECTED

    def __str__(self) -> str:
        """String representation."""
        return f"MCPClient({self.server_config.name}, {self.connection_state.value})"

    def __repr__(self) -> str:
        """Detailed string representation."""
        return (
            f"MCPClient(name={self.server_config.name}, "
            f"type={self.server_config.type}, "
            f"state={self.connection_state.value})"
        )


# Import os for environment variables
import os
